"""
HtmlRenderService 单元测试。

测试内容：
- PlaywrightHtmlRenderService 使用默认 device_scale_factor
- PlaywrightHtmlRenderService 使用自定义 device_scale_factor
- PlaywrightHtmlRenderService 调用时正确传递参数给底层 _html_img_render
- DI 容器能正确提供 HtmlRenderServiceBase（APP scope 单例）
- HtmlRenderServiceBase 在同一 APP 作用域内是同一实例
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from nonebot_plugin_zikequote3.services.html_render_service import (
    HtmlRenderServiceBase,
    PlaywrightHtmlRenderService,
)
from nonebot_plugin_zikequote3.di.container import create_container


# ---------------------------------------------------------------------------
# 为 html_capture.screen_shot 预注册 stub 模块，
# 避免延迟导入时触发 nonebot_plugin_localstore 初始化链。
# ---------------------------------------------------------------------------
_plugin_pkg = "nonebot_plugin_zikequote3"
_html_capture_pkg = f"{_plugin_pkg}.html_capture"
_screen_shot_mod = f"{_html_capture_pkg}.screen_shot"

# 确保 html_capture 包存在于 sys.modules
if _html_capture_pkg not in sys.modules:
    _stub_hc = types.ModuleType(_html_capture_pkg)
    _stub_hc.__path__ = [
        str(Path(__file__).resolve().parent.parent.parent
            / "nonebot_plugin_zikequote3" / "html_capture")
    ]
    sys.modules[_html_capture_pkg] = _stub_hc

# 创建 screen_shot stub 模块，包含可被替换的 _html_img_render
_stub_ss = types.ModuleType(_screen_shot_mod)
_stub_ss._html_img_render = AsyncMock(return_value=b"stub")  # type: ignore[attr-defined]
sys.modules[_screen_shot_mod] = _stub_ss


class TestPlaywrightHtmlRenderService:
    """PlaywrightHtmlRenderService 单元测试。"""

    async def test_render_uses_default_device_scale_factor(self) -> None:
        """render() 在未指定 device_scale_factor 时使用构造时的默认值。"""
        svc = PlaywrightHtmlRenderService(default_device_scale_factor=3.0)
        fake_bytes = b"fake-png-data"
        mock_render = AsyncMock(return_value=fake_bytes)
        _stub_ss._html_img_render = mock_render  # type: ignore[attr-defined]

        result = await svc.render("<html></html>", width=800, height=600)

        assert result == fake_bytes
        mock_render.assert_awaited_once_with(
            "<html></html>",
            width=800,
            height=600,
            clean_up=True,
            device_scale_factor=3.0,
            timeout=30000,
            wait=200,
        )

    async def test_render_uses_custom_device_scale_factor(self) -> None:
        """render() 在指定 device_scale_factor 时覆盖默认值。"""
        svc = PlaywrightHtmlRenderService(default_device_scale_factor=2.0)
        fake_bytes = b"fake-png-data"
        mock_render = AsyncMock(return_value=fake_bytes)
        _stub_ss._html_img_render = mock_render  # type: ignore[attr-defined]

        result = await svc.render(
            "<html></html>",
            width=1920,
            height=1080,
            device_scale_factor=1.5,
            wait=3000,
        )

        assert result == fake_bytes
        mock_render.assert_awaited_once_with(
            "<html></html>",
            width=1920,
            height=1080,
            clean_up=True,
            device_scale_factor=1.5,
            timeout=30000,
            wait=3000,
        )

    async def test_render_default_parameters(self) -> None:
        """render() 使用默认参数时正确传递。"""
        svc = PlaywrightHtmlRenderService()
        fake_bytes = b"default-png"
        mock_render = AsyncMock(return_value=fake_bytes)
        _stub_ss._html_img_render = mock_render  # type: ignore[attr-defined]

        result = await svc.render("<p>hello</p>")

        assert result == fake_bytes
        mock_render.assert_awaited_once_with(
            "<p>hello</p>",
            width=1000,
            height=800,
            clean_up=True,
            device_scale_factor=2.0,
            timeout=30000,
            wait=200,
        )

    async def test_render_propagates_exception(self) -> None:
        """render() 在底层抛出异常时正确传播。"""
        svc = PlaywrightHtmlRenderService()
        mock_render = AsyncMock(side_effect=RuntimeError("playwright crashed"))
        _stub_ss._html_img_render = mock_render  # type: ignore[attr-defined]

        with pytest.raises(RuntimeError, match="playwright crashed"):
            await svc.render("<html></html>")


class TestHtmlRenderServiceDI:
    """HtmlRenderServiceBase DI 容器集成测试。"""

    async def test_container_provides_html_render_service(self) -> None:
        """DI 容器能正确提供 HtmlRenderServiceBase 实例。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
            render_device_factor=2.0,
        )
        async with container() as app_scope:
            svc = await app_scope.get(HtmlRenderServiceBase)
            assert isinstance(svc, PlaywrightHtmlRenderService)
        await container.close()

    async def test_html_render_service_is_singleton(self) -> None:
        """同一 APP 作用域内获取的 HtmlRenderServiceBase 是同一实例。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
            render_device_factor=2.0,
        )
        async with container() as app_scope:
            svc1 = await app_scope.get(HtmlRenderServiceBase)
            svc2 = await app_scope.get(HtmlRenderServiceBase)
            assert svc1 is svc2
        await container.close()

    async def test_html_render_service_respects_config(self) -> None:
        """DI 容器传递的 render_device_factor 被正确应用。"""
        container = create_container(
            db_path=":memory:",
            image_store_path=Path("__test_images_not_used__"),
            render_device_factor=3.5,
        )
        async with container() as app_scope:
            svc = await app_scope.get(HtmlRenderServiceBase)
            assert isinstance(svc, PlaywrightHtmlRenderService)
            assert svc._default_device_scale_factor == 3.5
        await container.close()
