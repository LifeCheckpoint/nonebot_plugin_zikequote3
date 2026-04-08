"""
dishka AsyncContainer 组装。

由插件入口在启动时调用 create_container() 创建容器，
不在模块级别创建任何全局容器。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from dishka import AsyncContainer, make_async_container

from ..config import ConfigSchema, EmbeddingConfig, LLMConfig
from .providers.database_provider import DatabaseProvider
from .providers.infra_provider import InfraProvider
from .providers.repository_provider import RepositoryProvider
from .providers.service_provider import ServiceProvider
from .providers.vector_provider import VectorProvider


def create_container(
    db_path: Union[str, Path],
    image_store_path: Union[str, Path],
    render_device_factor: float = 2.0,
    *,
    default_config: Optional[ConfigSchema] = None,
    embedding_config: Optional[EmbeddingConfig] = None,
    llm_config: Optional[LLMConfig] = None,
    vector_db_path: Optional[Union[str, Path]] = None,
) -> AsyncContainer:
    """
    组装并返回 dishka AsyncContainer。

    :param db_path: 数据库文件路径，或 ``":memory:"`` 表示内存数据库
    :type db_path: Union[str, Path]
    :param image_store_path: 图片存储根目录路径
    :type image_store_path: Union[str, Path]
    :param render_device_factor: HTML 截图设备缩放因子，默认 2.0
    :type render_device_factor: float
    :param default_config: 启动期加载的全局配置真源
    :type default_config: Optional[ConfigSchema]
    :param embedding_config: Embedding 配置，为 None 或未启用时不注册向量搜索
    :type embedding_config: Optional[EmbeddingConfig]
    :param llm_config: LLM 配置，向量搜索需要
    :type llm_config: Optional[LLMConfig]
    :param vector_db_path: 向量数据库存储路径
    :type vector_db_path: Optional[Union[str, Path]]
    :returns: 配置好所有 Provider 的 AsyncContainer 实例
    :rtype: AsyncContainer
    """
    providers = [
        DatabaseProvider(db_path),
        InfraProvider(image_store_path, render_device_factor=render_device_factor),
        RepositoryProvider(),
        ServiceProvider(default_config=default_config),
        # 始终注册 VectorProvider；disabled 时各 provide 方法返回 None
        VectorProvider(embedding_config, llm_config, vector_db_path),
    ]

    return make_async_container(*providers)
