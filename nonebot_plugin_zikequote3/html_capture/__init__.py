"""
HTML 截图公共接口（向后兼容）。

.. deprecated::
    新代码应通过 DI 容器获取 ``HtmlRenderServiceBase`` 并调用
    ``render()`` 方法，而非直接调用本模块的 ``html_img_render()``。

本模块保留 ``html_img_render()`` 仅为尚未迁移到 DI 的旧代码提供
过渡支持。该函数不再依赖 ``imports.py``，而是直接调用底层
``screen_shot._html_img_render()``。
"""

from __future__ import annotations


async def html_img_render(
    html_content: str,
    width: int = 1000,
    height: int = 800,
    *,
    wait: int = 200,
    device_scale_factor: float = 2.0,
) -> bytes:
    """向后兼容的 HTML 截图便捷函数。

    新代码请使用 DI 注入的 ``HtmlRenderServiceBase.render()``。

    Args:
        html_content: 完整的 HTML 内容字符串。
        width: 视口宽度（像素）。
        height: 视口高度（像素）。
        wait: 页面加载后额外等待时间（毫秒）。
        device_scale_factor: 设备缩放因子。

    Returns:
        PNG 格式的截图字节数据。
    """
    from .screen_shot import _html_img_render

    return await _html_img_render(
        html_content,
        width=width,
        height=height,
        clean_up=True,
        device_scale_factor=device_scale_factor,
        timeout=30000,
        wait=wait,
    )
