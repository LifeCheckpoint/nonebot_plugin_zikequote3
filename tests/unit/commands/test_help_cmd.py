"""
help_cmd 命令处理器单元测试。

覆盖：
- handle_get_help：渲染帮助文档（图片渲染成功 / 渲染失败降级文本 / 别名触发）
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_get_help: MagicMock = getattr(_stub_cmd_def, "matcher_get_help")

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.help_cmd import (  # noqa: E402
    handle_get_help,
)


class TestHandleGetHelp:
    """语录帮助命令。"""

    async def test_render_image_success(
        self,
        patch_container,
    ) -> None:
        """渲染成功：返回图片消息。"""
        # Arrange
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")
        patch_container({HtmlRenderServiceBase: mock_render_svc})

        # Act & Assert
        with (
            patch(
                "nonebot_plugin_zikequote3.command.cmds.help_cmd.build_default_help_data"
            ) as mock_build,
            patch(
                "nonebot_plugin_zikequote3.command.cmds.help_cmd.render_help"
            ) as mock_render_help,
        ):
            mock_build.return_value = MagicMock()
            mock_render_help.return_value = "<html>help</html>"

            with pytest.raises(FinishedException):
                await handle_get_help(
                    html_render_svc=mock_render_svc,
                )

        # 验证渲染服务被调用，宽度/高度与 HELP 常量一致
        from nonebot_plugin_zikequote3.templates.registry import HELP
        mock_render_svc.render.assert_awaited_once()
        call_kwargs = mock_render_svc.render.call_args
        assert call_kwargs.kwargs.get("width") == HELP.width
        assert call_kwargs.kwargs.get("height") == HELP.height

    async def test_render_failure_fallback(
        self,
        patch_container,
    ) -> None:
        """渲染失败：降级为纯文本提示。"""
        # Arrange
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(
            side_effect=RuntimeError("render failed")
        )
        patch_container({HtmlRenderServiceBase: mock_render_svc})

        # Act & Assert
        with (
            patch(
                "nonebot_plugin_zikequote3.command.cmds.help_cmd.build_default_help_data"
            ) as mock_build,
            patch(
                "nonebot_plugin_zikequote3.command.cmds.help_cmd.render_help"
            ) as mock_render_help,
        ):
            mock_build.return_value = MagicMock()
            mock_render_help.return_value = "<html>help</html>"

            with pytest.raises(FinishedException):
                await handle_get_help(
                    html_render_svc=mock_render_svc,
                )

        # 验证 finish 包含回退文本提示
        finish_calls = matcher_get_help.finish.call_args_list
        last_msg = finish_calls[-1].args[0] if finish_calls[-1].args else ""
        assert "失败" in last_msg or "重试" in last_msg

    async def test_alias_trigger(
        self,
        patch_container,
    ) -> None:
        """别名「查看语录帮助」触发：handler 逻辑与主命令一致。"""
        # Arrange — 与 test_render_image_success 相同逻辑
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")
        patch_container({HtmlRenderServiceBase: mock_render_svc})

        with (
            patch(
                "nonebot_plugin_zikequote3.command.cmds.help_cmd.build_default_help_data"
            ) as mock_build,
            patch(
                "nonebot_plugin_zikequote3.command.cmds.help_cmd.render_help"
            ) as mock_render_help,
        ):
            mock_build.return_value = MagicMock()
            mock_render_help.return_value = "<html>help</html>"

            # 别名触发时 handler 函数相同，验证可正常执行
            with pytest.raises(FinishedException):
                await handle_get_help(
                    html_render_svc=mock_render_svc,
                )

        # 验证 build_default_help_data 和 render_help 均被调用
        mock_build.assert_called_once()
        mock_render_help.assert_called_once()
        mock_render_svc.render.assert_awaited_once()


def test_disable_quote_contract_removed_from_public_surfaces() -> None:
    """“停用语录”应已从公开命令契约、帮助与 README 中移除。"""
    from nonebot_plugin_zikequote3.command.cmds._help_data import (
        build_default_help_data,
    )

    help_data = build_default_help_data()
    command_names = {
        command.name
        for category in help_data.categories
        for command in category.commands
    }
    command_aliases = {
        alias
        for category in help_data.categories
        for command in category.commands
        for alias in command.aliases
    }

    assert "/停用语录" not in command_names
    assert "停用zikequote3" not in command_aliases

    project_root = Path(__file__).resolve().parents[3]
    command_definition_text = (
        project_root
        / "nonebot_plugin_zikequote3"
        / "command"
        / "command_definition.py"
    ).read_text(encoding="utf-8")
    readme_text = (project_root / "README.md").read_text(encoding="utf-8")

    assert "停用语录" not in command_definition_text
    assert "停用zikequote3" not in command_definition_text
    assert "停用语录" not in readme_text
    assert "停用zikequote3" not in readme_text
