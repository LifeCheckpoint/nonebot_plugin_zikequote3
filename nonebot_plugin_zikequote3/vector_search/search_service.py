"""向量搜索服务，协调 EmbeddingClient 和 VectorStore。"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from ..database.repositories.quote_repository import QuoteRepository
from ..database.models.quotes import Quote
from .embedding_client import EmbeddingClient
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class VectorSearchService:
    """向量搜索服务。"""

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
        """语义搜索，返回 [(Quote, similarity_score), ...]。"""
        if not await self.check_model_consistency():
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
        """为单条语录生成向量并存入 LanceDB。跳过无文本内容的语录。"""
        if not quote.content:
            return
        vector = await self._embedding.embed_query(quote.content)
        await self._store.upsert([{
            "quote_id": quote.quote_id,
            "group_id": quote.group_id,
            "content": quote.content,
            "vector": vector,
        }])

    async def remove_quote(self, quote_id: str) -> None:
        """删除单条语录的向量记录。"""
        await self._store.delete([quote_id])

    async def reindex_all(self, group_id: Optional[str] = None) -> int:
        """重建向量索引。group_id=None 时重建全部群。返回索引数量。"""
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
            return 0

        # 分批向量化
        batch_size = self._embedding.batch_size
        total_indexed = 0
        for i in range(0, len(text_quotes), batch_size):
            batch = text_quotes[i:i + batch_size]
            texts: List[str] = [q.content for q in batch if q.content]
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

        return total_indexed

    async def check_model_consistency(self) -> bool:
        """检查当前配置的模型/维度与已存储的是否一致。不一致返回 False。"""
        meta = await self._store.get_meta()
        if not meta:
            return True  # 无元信息，视为首次使用
        stored_model = meta.get("model_name", "")
        stored_dims = int(meta.get("dimensions", "0"))
        return (
            stored_model == self._embedding.model_name
            and stored_dims == self._embedding.dimensions
        )

    async def is_available(self) -> bool:
        """检查向量搜索服务是否可用（已连接且模型一致）。"""
        try:
            count = await self._store.count()
            consistent = await self.check_model_consistency()
            return consistent and count > 0
        except Exception:
            return False

    async def get_index_count(self) -> int:
        """获取当前索引的向量数量。"""
        return await self._store.count()
