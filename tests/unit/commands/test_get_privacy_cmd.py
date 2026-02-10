"""
get_privacy_cmd 命令处理器单元测试。

覆盖：
- handle_get_privacy：获取隐私政策（图片渲染成功 / 文件不存在 / 渲染失败降级纯文本）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_get_privacy: MagicMock = getattr(_stub_cmd_def, "matcher_get_privacy")

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.get_privacy_cmd import (  # noqa: E402
    handle_get_privacy,
)


class TestHandleGetPrivacy:
    """获取隐私政策命令。"""

    async def test_render_image_success(
        self,
        patch_container,
    ) -> None:
        """隐私文件存在且渲染成功：返回图片消息。"""
        # Arrange
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")
        patch_container({HtmlRenderServiceBase: mock_render_svc})

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "# 隐私政策\n内容..."

        # Act & Assert
        with (
            patch(
                "nonebot_plugin_zikequote3.command.cmds.get_privacy_cmd.PluginPath"
            ) as mock_plugin_path,
            patch(
                "nonebot_plugin_zikequote3.command.cmds.get_privacy_cmd.md_template"
            ) as mock_md_template,
        ):
            mock_plugin_path.module_resources_root.__truediv__ = MagicMock(
                return_value=mock_path
            )
            mock_md_template.render_markdown.return_value = "<h1>隐私政策</h1>"

            with pytest.raises(FinishedException):
                await handle_get_privacy(
                    html_render_svc=mock_render_svc,
                )

        # 验证渲染服务被调用
        mock_render_svc.render.assert_awaited_once()

    async def test_privacy_file_not_found(
        self,
        patch_container,
    ) -> None:
        """隐私文件不存在：提示联系管理员。"""
        # Arrange
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        patch_container({HtmlRenderServiceBase: mock_render_svc})

        mock_path = MagicMock()
        mock_path.exists.return_value = False

        # Act & Assert
        with patch(
            "nonebot_plugin_zikequote3.command.cmds.get_privacy_cmd.PluginPath"
        ) as mock_plugin_path:
            mock_plugin_path.module_resources_root.__truediv__ = MagicMock(
                return_value=mock_path
            )

            with pytest.raises(FinishedException):
                await handle_get_privacy(
                    html_render_svc=mock_render_svc,
                )

        # 验证 finish 包含文件不存在提示
        finish_calls = matcher_get_privacy.finish.call_args_list
        assert any("不存在" in str(c) for c in finish_calls)
        # 渲染服务不应被调用
        mock_render_svc.render.assert_not_awaited()

    async def test_render_fallback_to_text(
        self,
        patch_container,
    ) -> None:
        """渲染失败：降级为纯文本输出。"""
        # Arrange
        md_content = "# 隐私政策\n这是隐私政策内容"
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(
            side_effect=RuntimeError("render failed")
        )
        patch_container({HtmlRenderServiceBase: mock_render_svc})

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = md_content

        # Act & Assert
        with (
            patch(
                "nonebot_plugin_zikequote3.command.cmds.get_privacy_cmd.PluginPath"
            ) as mock_plugin_path,
            patch(
                "nonebot_plugin_zikequote3.command.cmds.get_privacy_cmd.md_template"
            ) as mock_md_template,
        ):
            mock_plugin_path.module_resources_root.__truediv__ = MagicMock(
                return_value=mock_path
            )
            mock_md_template.render_markdown.return_value = "<h1>隐私政策</h1>"

            with pytest.raises(FinishedException):
                await handle_get_privacy(
                    html_render_svc=mock_render_svc,
                )

        # 验证降级为纯文本（finish 参数包含 markdown 内容）
        finish_calls = matcher_get_privacy.finish.call_args_list
        # 直接检查 call_args 的实际参数值（避免 str() 转义换行符）
        last_call_args = finish_calls[-1]
        msg = last_call_args.args[0] if last_call_args.args else ""
        assert "隐私政策" in msg
        assert "这是隐私政策内容" in msg
