"""
基础设施相关的 dishka Provider。

提供 ImageStore、TokenManager 等基础设施组件。

组件评估记录（子任务20）：
- ImageStore        ✅ 已注册（APP scope）
- TokenManager      ✅ 已注册（APP scope）—— 有状态的内存 token 存储，
                       必须为单例以保证跨请求 token 验证一致性。
- ConfigManager     ❌ 不注册 —— 该类从未实现，其职责已被 ConfigService
                       （REQUEST scope，ServiceProvider 注册）完全替代。
- PermissionNodes   ❌ 不注册 —— PermissionServiceNodes 在模块加载时
                       用于 patch_matcher()，早于 DI 容器创建，时序上
                       无法通过 DI 注入。保持 command_definition.py 中
                       的模块级实例化方式。
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from dishka import Provider, Scope, provide

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.utils.token_generate import TokenManager


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

    @provide(scope=Scope.APP)
    def provide_token_manager(self) -> TokenManager:
        """创建 APP 级别的 TokenManager 单例。

        TokenManager 是有状态的内存 token 存储（生成 → 验证 → 过期），
        必须在整个应用生命周期内共享同一实例。
        """
        return TokenManager()
