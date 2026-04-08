"""向量搜索相关的 dishka Provider。

注册稳定的 :class:`VectorSearchCapability` 到 dishka 容器中，
统一表达“能力可用”与“能力不可用但类型稳定”两种状态。
Embedding 的连接参数统一来自启动期全局配置；群级运行时仅通过
``embedding.enabled`` 决定是否实际使用这些基础设施。
"""
from __future__ import annotations

from dataclasses import dataclass
from nonebot import logger
from pathlib import Path
from typing import Optional, Union

from dishka import Provider, Scope, provide

from nonebot_plugin_zikequote3.config import EmbeddingConfig, LLMConfig
from nonebot_plugin_zikequote3.database.repositories.quote_repository import QuoteRepository
from nonebot_plugin_zikequote3.vector_search.capability import (
    UnavailableVectorSearchService,
    VectorCapabilityStatus,
    VectorSearchCapability,
)
from nonebot_plugin_zikequote3.vector_search.embedding_client import EmbeddingClient
from nonebot_plugin_zikequote3.vector_search.search_service import VectorSearchService
from nonebot_plugin_zikequote3.vector_search.vector_store import VectorStore


@dataclass(frozen=True, slots=True)
class _VectorRuntime:
    """向量基础设施运行时快照。"""

    status: VectorCapabilityStatus
    embedding_client: EmbeddingClient | None = None
    vector_store: VectorStore | None = None


class VectorProvider(Provider):
    """向量搜索 DI Provider。"""

    def __init__(
        self,
        embedding_config: Optional[EmbeddingConfig] = None,
        llm_config: Optional[LLMConfig] = None,
        vector_db_path: Optional[Union[str, Path]] = None,
    ):
        super().__init__()
        self._embedding_config = embedding_config
        self._llm_config = llm_config
        self._vector_db_path = str(vector_db_path) if vector_db_path else ""

    @provide(scope=Scope.APP)
    async def provide_vector_runtime(self) -> _VectorRuntime:
        """构造向量基础设施，并返回稳定的运行时快照。"""
        if not self._embedding_config or not self._llm_config:
            return _VectorRuntime(
                status=VectorCapabilityStatus.unavailable_status(
                    "向量搜索基础设施未就绪，请检查启动期全局 Embedding 配置（model、base_url、api_key_path）"
                )
            )

        if not self._vector_db_path:
            return _VectorRuntime(
                status=VectorCapabilityStatus.unavailable_status(
                    "向量索引存储路径未配置，无法启用向量搜索基础设施"
                )
            )

        try:
            embedding_client = EmbeddingClient(self._embedding_config, self._llm_config)
        except Exception as exc:
            logger.warning("EmbeddingClient 创建失败: {}", exc)
            return _VectorRuntime(
                status=VectorCapabilityStatus.unavailable_status(
                    "向量搜索基础设施未就绪，请检查启动期全局 Embedding 配置（model、base_url、api_key_path）"
                )
            )

        try:
            vector_store = VectorStore()
            await vector_store.connect(self._vector_db_path)
            await vector_store.ensure_table(self._embedding_config.dimensions)
        except Exception as exc:
            logger.warning("VectorStore 创建失败: {}", exc)
            return _VectorRuntime(
                status=VectorCapabilityStatus.unavailable_status(
                    "向量搜索基础设施未就绪，请检查启动期全局 Embedding 配置（model、base_url、api_key_path）"
                )
            )

        return _VectorRuntime(
            status=VectorCapabilityStatus.available_status(),
            embedding_client=embedding_client,
            vector_store=vector_store,
        )

    @provide(scope=Scope.REQUEST)
    def provide_vector_search_capability(
        self,
        vector_runtime: _VectorRuntime,
        quote_repo: QuoteRepository,
    ) -> VectorSearchCapability:
        """提供稳定的向量搜索能力抽象。"""
        if (
            not vector_runtime.status.available
            or vector_runtime.embedding_client is None
            or vector_runtime.vector_store is None
        ):
            return UnavailableVectorSearchService(vector_runtime.status.reason)

        return VectorSearchService(
            vector_runtime.embedding_client,
            vector_runtime.vector_store,
            quote_repo,
            status=vector_runtime.status,
        )
