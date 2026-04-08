"""
基础设施相关的 dishka Provider。

提供 ImageStore、TokenManager、HtmlRenderServiceBase 等基础设施组件。

组件评估记录（子任务20）：
- ImageStore              ✅ 已注册（APP scope）
- TokenManager            ✅ 已注册（APP scope）—— 有状态的内存 token 存储，
                             必须为单例以保证跨请求 token 验证一致性。
- HtmlRenderServiceBase   ✅ 已注册（APP scope）—— 无状态截图服务，
                             单例即可；通过抽象基类注册方便未来切换实现。
- ConfigManager           ❌ 不注册 —— 该类从未实现，其职责已被 ConfigService
                             （REQUEST scope，ServiceProvider 注册）完全替代。
- PermissionNodes         ❌ 不注册 —— PermissionServiceNodes 在模块加载时
                             用于 patch_matcher()，早于 DI 容器创建，时序上
                             无法通过 DI 注入。保持 command_definition.py 中
                             的模块级实例化方式。
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from dishka import Provider, Scope, provide

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.services.html_render_service import (
    HtmlRenderServiceBase,
    PlaywrightHtmlRenderService,
)
from nonebot_plugin_zikequote3.services.quote_collection_service import (
    CollectionLockManager,
)
from nonebot_plugin_zikequote3.utils.token_generate import TokenManager


class InfraProvider(Provider):
    """
    基础设施依赖提供者。

    :param image_store_path: 图片存储根目录路径
    :type image_store_path: Union[str, Path]
    :param render_device_factor: HTML 截图设备缩放因子，默认 2.0
    :type render_device_factor: float
    """

    def __init__(
        self,
        image_store_path: Union[str, Path],
        render_device_factor: float = 2.0,
    ) -> None:
        super().__init__()
        self._image_store_path = Path(image_store_path)
        self._render_device_factor = render_device_factor

    @provide(scope=Scope.APP)
    def provide_image_store(self) -> ImageStore:
        """
        创建 APP 级别的 ImageStore 单例。

        :returns: 图片存储实例
        :rtype: ImageStore
        """
        return ImageStore(self._image_store_path)

    @provide(scope=Scope.APP)
    def provide_token_manager(self) -> TokenManager:
        """
        创建 APP 级别的 TokenManager 单例。

        TokenManager 是有状态的内存 token 存储（生成 → 验证 → 过期），
        必须在整个应用生命周期内共享同一实例。

        :returns: Token 管理器实例
        :rtype: TokenManager
        """
        return TokenManager()

    @provide(scope=Scope.APP)
    def provide_collection_lock_manager(self) -> CollectionLockManager:
        """创建 APP 级别共享收集锁管理器。"""
        return CollectionLockManager()

    @provide(scope=Scope.APP)
    def provide_html_render_service(self) -> HtmlRenderServiceBase:
        """
        创建 APP 级别的 HtmlRenderServiceBase 单例。

        当前使用 PlaywrightHtmlRenderService 实现，
        未来切换截图库只需替换此处的具体实现类。

        :returns: HTML 渲染服务实例
        :rtype: HtmlRenderServiceBase
        """
        return PlaywrightHtmlRenderService(
            default_device_scale_factor=self._render_device_factor,
        )
