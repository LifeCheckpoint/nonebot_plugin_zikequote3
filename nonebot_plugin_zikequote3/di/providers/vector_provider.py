"""向量搜索相关的 dishka Provider。"""
from __future__ import annotations

from pathlib import Path

from dishka import Provider, Scope, provide

from nonebot_plugin_zikequote3.config import EmbeddingConfig, LLMConfig
from nonebot_plugin_zikequote3.database.repositories.quote_repository import QuoteRepository
from nonebot_plugin_zikequote3.vector_search.embedding_client import EmbeddingClient
from nonebot_plugin_zikequote3.vector_search.vector_store import VectorStore
from nonebot_plugin_zikequote3.vector_search.search_service import VectorSearchService


class VectorProvider(Provider):
    """向量搜索 DI Provider。"""

    def __init__(
        self,
        embedding_config: EmbeddingConfig,
        llm_config: LLMConfig,
        vector_db_path: str | Path,
    ):
        super().__init__()
        self._embedding_config = embedding_config
        self._llm_config = llm_config
        self._vector_db_path = str(vector_db_path)

    @provide(scope=Scope.APP)
    async def provide_embedding_client(self) -> EmbeddingClient:
        return EmbeddingClient(self._embedding_config, self._llm_config)

    @provide(scope=Scope.APP)
    async def provide_vector_store(self) -> VectorStore:
        store = VectorStore()
        await store.connect(self._vector_db_path)
        await store.ensure_table(self._embedding_config.dimensions)
        return store

    @provide(scope=Scope.REQUEST)
    def provide_vector_search_service(
        self,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        quote_repo: QuoteRepository,
    ) -> VectorSearchService:
        return VectorSearchService(embedding_client, vector_store, quote_repo)
