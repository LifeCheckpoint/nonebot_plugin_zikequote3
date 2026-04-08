"""向量搜索相关的 dishka Provider。

注册 :class:`EmbeddingClient`、:class:`VectorStore` 和
:class:`VectorSearchService` 到 dishka 依赖注入容器中。
Embedding 的连接参数统一来自启动期全局配置；群级运行时仅通过
``embedding.enabled`` 决定是否实际使用这些基础设施。
当基础设施创建失败（如 API key 文件不存在）时，各 provide 方法返回 ``None``。
"""
from __future__ import annotations

from nonebot import logger
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

    始终注册到容器中，始终尝试创建基础设施。
    连接参数只读取启动期全局配置，不接受群级热更新覆盖；
    当配置不完整或创建失败时，各 provide 方法返回 ``None``。

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
        self._embedding_config = embedding_config
        self._llm_config = llm_config
        self._vector_db_path = str(vector_db_path) if vector_db_path else ""

    @provide(scope=Scope.APP)
    async def provide_embedding_client(self) -> EmbeddingClient:  # type: ignore[return-value]
        """提供 EmbeddingClient 实例。

        :returns: Embedding 客户端实例，配置不完整或创建失败时返回 ``None``。
        :rtype: EmbeddingClient
        """
        if not self._embedding_config or not self._llm_config:
            return None  # type: ignore[return-value]
        try:
            return EmbeddingClient(self._embedding_config, self._llm_config)
        except Exception as e:
            logger.warning("EmbeddingClient 创建失败: {}", e)
            return None  # type: ignore[return-value]

    @provide(scope=Scope.APP)
    async def provide_vector_store(self) -> VectorStore:  # type: ignore[return-value]
        """提供 VectorStore 实例，自动完成连接和表初始化。

        :returns: 向量存储实例，配置不完整或创建失败时返回 ``None``。
        :rtype: VectorStore
        """
        if not self._vector_db_path or not self._embedding_config:
            return None  # type: ignore[return-value]
        try:
            store = VectorStore()
            await store.connect(self._vector_db_path)
            await store.ensure_table(self._embedding_config.dimensions)
            return store
        except Exception as e:
            logger.warning("VectorStore 创建失败: {}", e)
            return None  # type: ignore[return-value]

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
        :returns: 向量搜索服务实例，依赖不可用时返回 ``None``。
        :rtype: VectorSearchService
        """
        if embedding_client is None or vector_store is None:
            return None  # type: ignore[return-value]
        return VectorSearchService(embedding_client, vector_store, quote_repo)
