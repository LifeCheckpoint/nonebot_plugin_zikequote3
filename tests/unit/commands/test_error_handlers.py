"""
_error_handlers 命令层异常映射单元测试。

覆盖：
- [`handle_command_error()`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py:30)：领域异常映射到稳定用户提示
- [`handle_command_error()`](nonebot_plugin_zikequote3/command/cmds/_error_handlers.py:30)：未知异常仍走内部错误分支并记录日志
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

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
from nonebot_plugin_zikequote3.msgtexts import general


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
        assert matcher.finish.call_args.args[0] == general.validation_error("参数格式不正确")

    async def test_resource_not_found_error(self) -> None:
        """[`ResourceNotFoundError`](nonebot_plugin_zikequote3/exceptions/resource.py:10) 应映射为未找到提示。"""
        matcher = _make_matcher()

        with pytest.raises(FinishedException):
            await handle_command_error(matcher, ResourceNotFoundError("没有找到对应语录"))

        assert matcher.finish.await_count == 1
        assert matcher.finish.call_args.args[0] == general.resource_not_found_error("没有找到对应语录")

    async def test_permission_denied_error(self) -> None:
        """[`PermissionDeniedError`](nonebot_plugin_zikequote3/exceptions/permission.py:10) 应映射为权限不足提示。"""
        matcher = _make_matcher()

        with pytest.raises(FinishedException):
            await handle_command_error(matcher, PermissionDeniedError("仅管理员可执行"))

        assert matcher.finish.await_count == 1
        assert matcher.finish.call_args.args[0] == general.permission_denied_error("仅管理员可执行")

    async def test_operation_error(self) -> None:
        """[`OperationError`](nonebot_plugin_zikequote3/exceptions/operations.py:10) 应映射为操作失败提示。"""
        matcher = _make_matcher()

        with pytest.raises(FinishedException):
            await handle_command_error(matcher, OperationError("当前群组语录数为 0"))

        assert matcher.finish.await_count == 1
        assert matcher.finish.call_args.args[0] == general.operation_error("当前群组语录数为 0")

    async def test_unexpected_error(self) -> None:
        """未知异常应继续走内部错误分支并返回通用错误提示。"""
        matcher = _make_matcher()
        error = RuntimeError("database crashed")

        with pytest.raises(FinishedException):
            await handle_command_error(matcher, error)

        assert matcher.finish.await_count == 1
        assert matcher.finish.call_args.args[0] == general.unexpected_error("database crashed")
