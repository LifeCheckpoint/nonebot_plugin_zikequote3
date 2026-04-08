"""
_error_handlers 命令层异常映射单元测试。

覆盖：
- [`handle_command_error()`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py:30)：领域异常映射到稳定用户提示
- [`handle_command_error()`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py:30)：未知异常仍走内部错误分支并上报 Sentry
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.command.cmds._error_handlers import (
    handle_command_error,
)
from nonebot_plugin_zikequote3.exceptions import (
    OperationError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationException,
)


def _make_matcher() -> MagicMock:
    """创建模拟 matcher。"""
    matcher = MagicMock()
    matcher.finish = AsyncMock(side_effect=FinishedException)
    return matcher


class TestHandleCommandError:
    """[`handle_command_error()`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py:30) 映射规则。"""

    async def test_validation_exception(self) -> None:
        """[`ValidationException`](nonebot_plugin_zikequote3/exceptions/validation.py:10) 应映射为输入错误提示。"""
        matcher = _make_matcher()

        with pytest.raises(FinishedException):
            await handle_command_error(matcher, ValidationException("参数格式不正确"))

        assert matcher.finish.await_count == 1
        assert matcher.finish.call_args.args[0] == "输入有误：参数格式不正确"

    async def test_resource_not_found_error(self) -> None:
        """[`ResourceNotFoundError`](nonebot_plugin_zikequote3/exceptions/resource.py:10) 应映射为未找到提示。"""
        matcher = _make_matcher()

        with pytest.raises(FinishedException):
            await handle_command_error(matcher, ResourceNotFoundError("没有找到对应语录"))

        assert matcher.finish.await_count == 1
        assert matcher.finish.call_args.args[0] == "未找到：没有找到对应语录"

    async def test_permission_denied_error(self) -> None:
        """[`PermissionDeniedError`](nonebot_plugin_zikequote3/exceptions/permission.py:10) 应映射为权限不足提示。"""
        matcher = _make_matcher()

        with pytest.raises(FinishedException):
            await handle_command_error(matcher, PermissionDeniedError("仅管理员可执行"))

        assert matcher.finish.await_count == 1
        assert matcher.finish.call_args.args[0] == "权限不足：仅管理员可执行"

    async def test_operation_error(self) -> None:
        """[`OperationError`](nonebot_plugin_zikequote3/exceptions/operations.py:10) 应映射为操作失败提示。"""
        matcher = _make_matcher()

        with pytest.raises(FinishedException):
            await handle_command_error(matcher, OperationError("当前群组语录数为 0"))

        assert matcher.finish.await_count == 1
        assert matcher.finish.call_args.args[0] == "操作失败：当前群组语录数为 0"

    async def test_unexpected_error(self) -> None:
        """未知异常应继续走内部错误分支并触发 Sentry 上报。"""
        matcher = _make_matcher()
        error = RuntimeError("database crashed")

        with patch(
            "nonebot_plugin_zikequote3.command.cmds._error_handlers.sentry_sdk.capture_exception"
        ) as mock_capture:
            with pytest.raises(FinishedException):
                await handle_command_error(matcher, error)

        mock_capture.assert_called_once_with(error)
        assert matcher.finish.await_count == 1
        assert matcher.finish.call_args.args[0] == "发生错误：database crashed"
