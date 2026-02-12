"""向量搜索服务，协调 EmbeddingClient 和 VectorStore。

提供语义搜索、单条索引、批量重建索引、模型一致性检查等功能，
是模糊搜索的核心业务层。
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from ..database.repositories.quote_repository import QuoteRepository
from ..database.models.quotes import Quote
from .embedding_client import EmbeddingClient
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

# M5: 模块级缓存，跨 REQUEST 作用域的 VectorSearchService 实例共享
_model_consistent_cache: bool | None = None


class VectorSearchService:
    """向量搜索服务。

    协调 :class:`EmbeddingClient` 和 :class:`VectorStore`，
    提供语义搜索、索引管理和模型一致性检查等高层接口。

    :param embedding_client: Embedding 客户端实例。
    :type embedding_client: EmbeddingClient
    :param vector_store: 向量存储实例。
    :type vector_store: VectorStore
    :param quote_repo: 语录仓储实例。
    :type quote_repo: QuoteRepository
    """

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        quote_repo: QuoteRepository,
    ):
        self._embedding = embedding_client
        self._store = vector_store
        self._repo = quote_repo

    async def semantic_search(
        self,
        query: str,
        group_id: str,
        *,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> List[Tuple[Quote, float]]:
        """语义搜索，返回匹配的语录及相似度分数。

        :param query: 搜索查询文本。
        :type query: str
        :param group_id: 群组 ID，限定搜索范围。
        :type group_id: str
        :param limit: 最大返回结果数量，默认为 10。
        :type limit: int
        :param threshold: 相似度阈值，低于此值的结果将被过滤，默认为 0.0。
        :type threshold: float
        :returns: 语录与相似度分数的元组列表。
        :rtype: List[Tuple[Quote, float]]
        :raises ValueError: 当向量索引模型不一致时抛出。
        """
        # M5: 使用缓存避免每次搜索都读取 meta 表
        if not await self._check_model_consistency_cached():
            raise ValueError(
                "向量索引模型不一致，请先执行 /重建语录索引 重建索引"
            )
        query_vector = await self._embedding.embed_query(query)
        results = await self._store.search(
            query_vector, group_id=group_id, limit=limit, threshold=threshold,
        )
        # 按 quote_id 批量获取完整 Quote 对象
        quotes_with_scores: List[Tuple[Quote, float]] = []
        for row in results:
            quote = await self._repo.get_quote_by_id(row["quote_id"])
            if quote is not None:
                quotes_with_scores.append((quote, row["similarity"]))
        return quotes_with_scores

    async def index_quote(self, quote: Quote) -> None:
        """为单条语录生成向量并存入 LanceDB。

        跳过无文本内容的语录。如果正在重建索引（M6），跳过操作避免竞态。

        :param quote: 待索引的语录对象。
        :type quote: Quote
        """
        if not quote.content:
            return
        if self._store.reindex_lock.locked():
            logger.info("正在重建索引，跳过 index_quote(quote_id=%s)", quote.quote_id)
            return
        async with self._store.reindex_lock:
            vector = await self._embedding.embed_query(quote.content)
            await self._store.upsert([{
                "quote_id": quote.quote_id,
                "group_id": quote.group_id,
                "content": quote.content,
                "vector": vector,
            }])

    async def remove_quote(self, quote_id: str) -> None:
        """删除单条语录的向量记录。

        如果正在重建索引（M6），跳过操作避免竞态。

        :param quote_id: 待删除的语录 ID。
        :type quote_id: str
        """
        if self._store.reindex_lock.locked():
            logger.info("正在重建索引，跳过 remove_quote(quote_id=%s)", quote_id)
            return
        async with self._store.reindex_lock:
            await self._store.delete([quote_id])

    async def reindex_all(self, group_id: Optional[str] = None) -> int:
        """重建向量索引。

        持有 reindex_lock 防止与 :meth:`index_quote` / :meth:`remove_quote` 竞态。

        :param group_id: 群组 ID，为 ``None`` 时重建全部群。
        :type group_id: Optional[str]
        :returns: 成功索引的语录数量。
        :rtype: int
        """
        global _model_consistent_cache
        async with self._store.reindex_lock:
            if group_id:
                await self._store.delete_by_group(group_id)
            else:
                await self._store.drop_all()
                await self._store.ensure_table(self._embedding.dimensions)
                await self._store.set_meta(self._embedding.model_name, self._embedding.dimensions)

            # 获取所有语录（按群或全部）
            if group_id:
                quotes = await self._repo.get_quotes_by_group(group_id)
            else:
                quotes = await self._repo.get_all_quotes()

            # 过滤掉无文本内容的语录
            text_quotes = [q for q in quotes if q.content]
            if not text_quotes:
                # M5: 重建完成后模型一定一致
                _model_consistent_cache = True
                return 0

            # 分批向量化
            batch_size = self._embedding.batch_size
            total_indexed = 0
            for i in range(0, len(text_quotes), batch_size):
                batch = text_quotes[i:i + batch_size]
                texts: List[str] = [q.content for q in batch]  # type: ignore[misc]
                vectors = await self._embedding.embed_texts(texts)
                records = [
                    {
                        "quote_id": q.quote_id,
                        "group_id": q.group_id,
                        "content": q.content,
                        "vector": v,
                    }
                    for q, v in zip(batch, vectors)
                ]
                await self._store.upsert(records)
                total_indexed += len(records)
                logger.info("向量索引进度: %d/%d", total_indexed, len(text_quotes))

            # M5: 重建完成后模型一定一致
            _model_consistent_cache = True
            return total_indexed

    async def check_model_consistency(self) -> bool:
        """检查当前配置的模型/维度与已存储的是否一致。

        :returns: 一致返回 ``True``，不一致返回 ``False``。
        :rtype: bool
        """
        meta = await self._store.get_meta()
        if not meta:
            return True  # 无元信息，视为首次使用
        stored_model = meta.get("model_name", "")
        try:
            stored_dims = int(meta.get("dimensions", "0"))
        except (ValueError, TypeError):
            logger.warning("meta 表中 dimensions 值损坏: %r，视为不一致", meta.get("dimensions"))
            return False
        return (
            stored_model == self._embedding.model_name
            and stored_dims == self._embedding.dimensions
        )

    async def _check_model_consistency_cached(self) -> bool:
        """带缓存的模型一致性检查，首次调用后缓存结果（M5）。"""
        global _model_consistent_cache
        if _model_consistent_cache is None:
            _model_consistent_cache = await self.check_model_consistency()
        return _model_consistent_cache

    @staticmethod
    def reset_model_consistency_cache() -> None:
        """重置模型一致性缓存（供测试或外部调用）。"""
        global _model_consistent_cache
        _model_consistent_cache = None

    async def is_available(self) -> bool:
        """检查向量搜索基础设施是否就绪。

        验证 store 已连接、embedding 可用。不检查索引是否有数据，
        调用方应通过 :meth:`get_index_count` 区分"索引为空"（M4）。

        :returns: 基础设施就绪返回 ``True``，否则返回 ``False``。
        :rtype: bool
        """
        try:
            # 验证 store 连接正常（调用 count 会触发 _get_db 检查）
            await self._store.count()
            return True
        except Exception:
            return False

    async def get_index_count(self) -> int:
        """获取当前索引的向量数量。

        :returns: 向量记录总数。
        :rtype: int
        """
        return await self._store.count()
