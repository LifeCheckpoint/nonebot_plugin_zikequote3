"""
HTML 截图渲染服务。

提供抽象基类 ``HtmlRenderServiceBase`` 和基于 Playwright
(nonebot_plugin_htmlrender) 的具体实现 ``PlaywrightHtmlRenderService``。

通过 DI 容器注入，方便未来切换截图库（如从 Playwright 切换到其他方案）
时只需替换 Service 实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class HtmlRenderServiceBase(ABC):
    """HTML 截图服务抽象基类，方便未来切换实现。"""

    @abstractmethod
    async def render(
        self,
        html: str,
        width: int = 1000,
        height: int = 800,
        *,
        device_scale_factor: float | None = None,
        wait: int = 200,
    ) -> bytes:
        """将 HTML 字符串渲染为图片 bytes。

        Args:
            html: 完整的 HTML 内容字符串。
            width: 视口宽度（像素）。
            height: 视口高度（像素）。
            device_scale_factor: 设备缩放因子，为 ``None`` 时使用服务默认值。
            wait: 页面加载后额外等待时间（毫秒）。

        Returns:
            PNG 格式的截图字节数据。
        """
        ...


class PlaywrightHtmlRenderService(HtmlRenderServiceBase):
    """基于 Playwright (nonebot_plugin_htmlrender) 的 HTML 截图实现。"""

    def __init__(self, default_device_scale_factor: float = 2.0) -> None:
        self._default_device_scale_factor = default_device_scale_factor

    async def render(
        self,
        html: str,
        width: int = 1000,
        height: int = 800,
        *,
        device_scale_factor: float | None = None,
        wait: int = 200,
    ) -> bytes:
        """调用底层 ``_html_img_render`` 完成截图。"""
        from ..html_capture.screen_shot import _html_img_render

        factor = (
            device_scale_factor
            if device_scale_factor is not None
            else self._default_device_scale_factor
        )
        return await _html_img_render(
            html,
            width=width,
            height=height,
            clean_up=True,
            device_scale_factor=factor,
            timeout=30000,
            wait=wait,
        )
