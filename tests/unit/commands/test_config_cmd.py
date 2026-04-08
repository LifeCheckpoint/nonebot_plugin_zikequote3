"""
config_cmd 命令处理器单元测试。

覆盖：
- handle_get_current_config：查看当前配置（图片渲染成功 / toml 为 None / 渲染失败降级纯文本）
- handle_modify_config：修改配置（成功 / 参数过少 / 解析失败）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.exceptions import ValidationException
from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_get_current_config: MagicMock = getattr(
    _stub_cmd_def, "matcher_get_current_config"
)
matcher_modify_config: MagicMock = getattr(
    _stub_cmd_def, "matcher_modify_config"
)

# handler 函数（conftest stub 保证 @matcher.handle() 透传）
from nonebot_plugin_zikequote3.command.cmds.config_cmd import (  # noqa: E402
    handle_get_current_config,
    handle_modify_config,
)


# ===================================================================
# handle_get_current_config 测试
# ===================================================================


class TestHandleGetCurrentConfig:
    """查看当前配置命令。"""

    async def test_render_image_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """配置存在且图片渲染成功：返回图片消息。"""
        # Arrange
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.get_group_toml = AsyncMock(
            return_value="[general]\nkey = 'value'"
        )
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")
        patch_container({
            ConfigService: mock_config_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_current_config(
                event=mock_group_event,
                config_svc=mock_config_svc,
                html_render_svc=mock_render_svc,
            )

        # 验证服务调用
        mock_config_svc.get_group_toml.assert_awaited_once_with("123456")
        mock_render_svc.render.assert_awaited_once()

    async def test_no_custom_config(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """群组无自定义配置（toml 为 None）：提示使用默认配置。"""
        # Arrange
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.get_group_toml = AsyncMock(return_value=None)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        patch_container({
            ConfigService: mock_config_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_current_config(
                event=mock_group_event,
                config_svc=mock_config_svc,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含默认配置提示
        finish_calls = matcher_get_current_config.finish.call_args_list
        assert any("默认配置" in str(c) for c in finish_calls)
        # 渲染服务不应被调用
        mock_render_svc.render.assert_not_awaited()

    async def test_render_fallback_to_text(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """图片渲染失败：降级为纯文本输出。"""
        # Arrange
        toml_content = "[general]\nkey = 'value'"
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.get_group_toml = AsyncMock(return_value=toml_content)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(
            side_effect=RuntimeError("playwright crashed")
        )
        patch_container({
            ConfigService: mock_config_svc,
            HtmlRenderServiceBase: mock_render_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_get_current_config(
                event=mock_group_event,
                config_svc=mock_config_svc,
                html_render_svc=mock_render_svc,
            )

        # 验证降级为纯文本（finish 参数包含 toml 内容）
        finish_calls = matcher_get_current_config.finish.call_args_list
        # 直接检查 call_args 的实际参数值（避免 str() 转义换行符）
        last_call_args = finish_calls[-1]
        msg = last_call_args.args[0] if last_call_args.args else ""
        assert "[general]" in msg
        assert "key = 'value'" in msg


# ===================================================================
# handle_modify_config 测试
# ===================================================================


class TestHandleModifyConfig:
    """修改配置命令。"""

    async def test_modify_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """参数正确：修改配置成功。"""
        # Arrange
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.parse_config_param = MagicMock(
            return_value=("general.key", "new_value")
        )
        mock_config_svc.modify_single_value = AsyncMock(return_value=None)
        patch_container({ConfigService: mock_config_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "general.key new_value"

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_modify_config(
                event=mock_group_event,
                arg=mock_arg,
                config_svc=mock_config_svc,
            )

        # 验证服务调用
        mock_config_svc.parse_config_param.assert_called_once_with(
            ["general.key", "new_value"]
        )
        mock_config_svc.modify_single_value.assert_awaited_once_with(
            "123456", "general.key", "new_value"
        )
        # 验证成功消息
        finish_calls = matcher_modify_config.finish.call_args_list
        assert any("修改成功" in str(c) for c in finish_calls)

    async def test_modify_preserves_string_value_with_spaces(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """带空格的合法字符串值应完整传给解析层，不得被命令层截断。"""
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.parse_config_param = MagicMock(
            return_value=("general.key", "hello world")
        )
        mock_config_svc.modify_single_value = AsyncMock(return_value=None)
        patch_container({ConfigService: mock_config_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "general.key 'hello world'"

        with pytest.raises(FinishedException):
            await handle_modify_config(
                event=mock_group_event,
                arg=mock_arg,
                config_svc=mock_config_svc,
            )

        mock_config_svc.parse_config_param.assert_called_once_with(
            ["general.key", "'hello world'"]
        )
        mock_config_svc.modify_single_value.assert_awaited_once_with(
            "123456", "general.key", "hello world"
        )

    async def test_too_few_args(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """参数过少：抛出 ValueError，被 command_error_handler 捕获。"""
        # Arrange
        mock_config_svc = AsyncMock(spec=ConfigService)
        patch_container({ConfigService: mock_config_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "only_one"

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_modify_config(
                event=mock_group_event,
                arg=mock_arg,
                config_svc=mock_config_svc,
            )

        # ValueError 被 command_error_handler 捕获，finish 包含错误信息
        finish_calls = matcher_modify_config.finish.call_args_list
        assert any("参数过少" in str(c) for c in finish_calls)

    async def test_parse_param_error(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """参数解析失败：parse_config_param 抛异常。"""
        # Arrange
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.parse_config_param = MagicMock(
            side_effect=ValueError("invalid format")
        )
        patch_container({ConfigService: mock_config_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "bad.key ???"

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_modify_config(
                event=mock_group_event,
                arg=mock_arg,
                config_svc=mock_config_svc,
            )

        # 验证 finish 包含解析错误信息
        finish_calls = matcher_modify_config.finish.call_args_list
        assert any("奇怪" in str(c) for c in finish_calls)

    async def test_modify_schema_validation_error(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """非法在线配置在写入阶段失败，并走 schema 校验提示。"""
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_config_svc.parse_config_param = MagicMock(
            return_value=("collecting.pickup_interval", "oops")
        )
        mock_config_svc.modify_single_value = AsyncMock(
            side_effect=ValidationException("配置项 'collecting.pickup_interval' 不符合配置 schema")
        )
        patch_container({ConfigService: mock_config_svc})

        mock_arg = MagicMock()
        mock_arg.extract_plain_text.return_value = "collecting.pickup_interval 'oops'"

        with pytest.raises(FinishedException):
            await handle_modify_config(
                event=mock_group_event,
                arg=mock_arg,
                config_svc=mock_config_svc,
            )

        finish_calls = matcher_modify_config.finish.call_args_list
        assert any("输入有误" in str(c) for c in finish_calls)
        assert any("schema" in str(c) for c in finish_calls)
