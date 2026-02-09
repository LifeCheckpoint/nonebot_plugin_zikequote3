"""
dishka AsyncContainer 组装。

由插件入口在启动时调用 create_container() 创建容器，
不在模块级别创建任何全局容器。
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from dishka import AsyncContainer, make_async_container

from .providers.database_provider import DatabaseProvider
from .providers.infra_provider import InfraProvider
from .providers.repository_provider import RepositoryProvider
from .providers.service_provider import ServiceProvider


def create_container(
    db_path: Union[str, Path],
    image_store_path: Union[str, Path],
) -> AsyncContainer:
    """
    组装并返回 dishka AsyncContainer。

    参数:
        db_path: 数据库文件路径，或 ":memory:" 表示内存数据库。
        image_store_path: 图片存储根目录路径。

    返回:
        配置好所有 Provider 的 AsyncContainer 实例。
    """
    return make_async_container(
        DatabaseProvider(db_path),
        InfraProvider(image_store_path),
        RepositoryProvider(),
        ServiceProvider(),
    )
