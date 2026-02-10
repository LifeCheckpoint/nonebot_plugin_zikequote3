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
    render_device_factor: float = 2.0,
) -> AsyncContainer:
    """
    组装并返回 dishka AsyncContainer。

    :param db_path: 数据库文件路径，或 ``":memory:"`` 表示内存数据库
    :type db_path: Union[str, Path]
    :param image_store_path: 图片存储根目录路径
    :type image_store_path: Union[str, Path]
    :param render_device_factor: HTML 截图设备缩放因子，默认 2.0
    :type render_device_factor: float
    :returns: 配置好所有 Provider 的 AsyncContainer 实例
    :rtype: AsyncContainer
    """
    return make_async_container(
        DatabaseProvider(db_path),
        InfraProvider(image_store_path, render_device_factor=render_device_factor),
        RepositoryProvider(),
        ServiceProvider(),
    )
