"""向量搜索相关的 dishka Provider。

注册 :class:`EmbeddingClient`、:class:`VectorStore` 和
:class:`VectorSearchService` 到 dishka 依赖注入容器中。
当 embedding 未启用时，各 provide 方法返回 ``None``。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from dishka import Provider, Scope, provide

from nonebot_plugin_zikequote3.config import EmbeddingConfig, LLMConfig
from nonebot_plugin_zikequote3.database.repositories.quote_repository import QuoteRepository
from nonebot_plugin_zikequote3.vector_search.embedding_client import EmbeddingClient
from nonebot_plugin_zikequote3.vector_search.vector_store import VectorStore
from nonebot_plugin_zikequote3.vector_search.search_service import VectorSearchService


class VectorProvider(Provider):
    """向量搜索 DI Provider。

    始终注册到容器中。当 embedding 未启用时，各 provide 方法返回 ``None``。

    :param embedding_config: Embedding 服务配置，默认为 ``None``。
    :type embedding_config: Optional[EmbeddingConfig]
    :param llm_config: LLM 服务配置，默认为 ``None``。
    :type llm_config: Optional[LLMConfig]
    :param vector_db_path: 向量数据库路径，默认为 ``None``。
    :type vector_db_path: Optional[Union[str, Path]]
    """

    def __init__(
        self,
        embedding_config: Optional[EmbeddingConfig] = None,
        llm_config: Optional[LLMConfig] = None,
        vector_db_path: Optional[Union[str, Path]] = None,
    ):
        super().__init__()
        self._enabled = bool(
            embedding_config
            and embedding_config.enabled
            and llm_config
            and vector_db_path
        )
        self._embedding_config = embedding_config
        self._llm_config = llm_config
        self._vector_db_path = str(vector_db_path) if vector_db_path else ""

    @provide(scope=Scope.APP)
    async def provide_embedding_client(self) -> EmbeddingClient:  # type: ignore[return-value]
        """提供 EmbeddingClient 实例。

        :returns: Embedding 客户端实例，未启用时返回 ``None``。
        :rtype: EmbeddingClient
        """
        if not self._enabled:
            return None  # type: ignore[return-value]
        return EmbeddingClient(self._embedding_config, self._llm_config)  # type: ignore[arg-type]

    @provide(scope=Scope.APP)
    async def provide_vector_store(self) -> VectorStore:  # type: ignore[return-value]
        """提供 VectorStore 实例，自动完成连接和表初始化。

        :returns: 向量存储实例，未启用时返回 ``None``。
        :rtype: VectorStore
        """
        if not self._enabled:
            return None  # type: ignore[return-value]
        store = VectorStore()
        await store.connect(self._vector_db_path)
        await store.ensure_table(self._embedding_config.dimensions)  # type: ignore[union-attr]
        return store

    @provide(scope=Scope.REQUEST)
    def provide_vector_search_service(
        self,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        quote_repo: QuoteRepository,
    ) -> VectorSearchService:  # type: ignore[return-value]
        """提供 VectorSearchService 实例。

        :param embedding_client: Embedding 客户端实例。
        :type embedding_client: EmbeddingClient
        :param vector_store: 向量存储实例。
        :type vector_store: VectorStore
        :param quote_repo: 语录仓储实例。
        :type quote_repo: QuoteRepository
        :returns: 向量搜索服务实例，未启用时返回 ``None``。
        :rtype: VectorSearchService
        """
        if not self._enabled or embedding_client is None or vector_store is None:
            return None  # type: ignore[return-value]
        return VectorSearchService(embedding_client, vector_store, quote_repo)
