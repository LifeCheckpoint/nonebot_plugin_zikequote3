"""
命令层共享的异常处理辅助函数。

根据异常类型提供差异化的错误响应：
- ValidationException → 用户输入错误提示
- ResourceNotFoundError → 资源不存在提示
- PermissionDeniedError → 权限不足提示
- OperationError → 操作失败提示
- 其他异常 → 通用错误提示（保留 Sentry 上报）
"""

from __future__ import annotations

import logging
from asyncio import CancelledError
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

import sentry_sdk
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher

from ...exceptions import (
    OperationError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationException,
)

logger = logging.getLogger(__name__)


async def handle_command_error(matcher: type[Matcher], error: Exception) -> None:
    """根据异常类型发送差异化错误消息并结束事件。

    Args:
        matcher: NoneBot 匹配器对象。
        error: 捕获到的异常。
    """
    if isinstance(error, ValidationException):
        await matcher.finish(f"输入有误：{error}")
    elif isinstance(error, ResourceNotFoundError):
        await matcher.finish(f"未找到：{error}")
    elif isinstance(error, PermissionDeniedError):
        await matcher.finish(f"权限不足：{error}")
    elif isinstance(error, OperationError):
        await matcher.finish(f"操作失败：{error}")
    else:
        # 非业务异常，上报 Sentry 并使用通用失败消息
        sentry_sdk.capture_exception(error)
        await matcher.finish(f"发生错误：{error}")


@asynccontextmanager
async def command_error_handler(
    matcher: type[Matcher],
    action: str = "",
) -> AsyncIterator[None]:
    """异步上下文管理器：捕获异常并根据类型发送差异化错误消息。

    替代旧的 ``event_exception_failmsg_a``，提供精确的异常分类响应。

    Args:
        matcher: NoneBot 匹配器对象。
        action: 当前操作描述（用于日志记录）。
    """
    try:
        yield
    except (FinishedException, CancelledError):
        raise
    except Exception as e:
        log_prefix = f"命令异常 / {action}" if action else "命令异常"
        logger.error("%s: %s", log_prefix, e, exc_info=True)
        await handle_command_error(matcher, e)


@contextmanager
def suppress_error(action: str = "") -> Iterator[None]:
    """同步上下文管理器：捕获并静默忽略异常（仅记录日志和上报 Sentry）。

    替代旧的 ``event_exception(operation="ignore")``，
    用于非关键操作（如更新展示次数、创建消息映射等）。

    Args:
        action: 当前操作描述（用于日志记录）。
    """
    try:
        yield
    except (FinishedException, CancelledError):
        raise
    except Exception as e:
        log_prefix = f"非关键操作异常 / {action}" if action else "非关键操作异常"
        logger.warning("%s: %s", log_prefix, e, exc_info=True)
        sentry_sdk.capture_exception(e)


@asynccontextmanager
async def silent_error_handler(
    action: str = "",
    finish_on_error: bool = True,
) -> AsyncIterator[None]:
    """异步上下文管理器：静默处理后台任务异常。

    替代旧的 ``event_exception_a(operation="finish")``，
    用于后台监听器等不需要向用户反馈错误详情的场景。

    Args:
        action: 当前操作描述（用于日志记录）。
        finish_on_error: 异常时是否抛出 FinishedException 结束事件。
    """
    try:
        yield
    except (FinishedException, CancelledError):
        raise
    except Exception as e:
        log_prefix = f"后台任务异常 / {action}" if action else "后台任务异常"
        logger.error("%s: %s", log_prefix, e, exc_info=True)
        sentry_sdk.capture_exception(e)
        if finish_on_error:
            raise FinishedException()
