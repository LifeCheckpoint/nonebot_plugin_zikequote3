"""
基础设施相关的 dishka Provider。

提供 ImageStore 等基础设施组件。
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from dishka import Provider, Scope, provide

from nonebot_plugin_zikequote3.database.image_store import ImageStore


class InfraProvider(Provider):
    """
    基础设施依赖提供者。

    构造参数:
        image_store_path: 图片存储根目录路径。
    """

    def __init__(self, image_store_path: Union[str, Path]) -> None:
        super().__init__()
        self._image_store_path = Path(image_store_path)

    @provide(scope=Scope.APP)
    def provide_image_store(self) -> ImageStore:
        """创建 APP 级别的 ImageStore 单例。"""
        return ImageStore(self._image_store_path)
