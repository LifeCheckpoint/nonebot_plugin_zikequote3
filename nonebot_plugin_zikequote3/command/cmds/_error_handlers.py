"""
命令层共享的异常处理辅助函数。

根据异常类型提供差异化的错误响应：
- ValidationException → 用户输入错误提示
- ResourceNotFoundError → 资源不存在提示
- PermissionDeniedError → 权限不足提示
- OperationError → 操作失败提示
- 其他异常 → 通用错误提示
"""

from __future__ import annotations

from nonebot import logger
from asyncio import CancelledError
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

from nonebot.exception import FinishedException
from nonebot.matcher import Matcher

from ...exceptions import (
    OperationError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationException,
)
from ...msgtexts import general

async def handle_command_error(matcher: type[Matcher], error: Exception) -> None:
    """
    根据异常类型发送差异化错误消息并结束事件。

    :param matcher: NoneBot 匹配器对象
    :type matcher: type[Matcher]
    :param error: 捕获到的异常
    :type error: Exception
    """
    if isinstance(error, ValidationException):
        await matcher.finish(general.validation_error(str(error)))
    elif isinstance(error, ResourceNotFoundError):
        await matcher.finish(general.resource_not_found_error(str(error)))
    elif isinstance(error, PermissionDeniedError):
        await matcher.finish(general.permission_denied_error(str(error)))
    elif isinstance(error, OperationError):
        await matcher.finish(general.operation_error(str(error)))
    else:
        # 非业务异常仅记录日志，错误追踪由宿主项目的官方 Sentry 插件接管。
        logger.opt(exception=error).error("命令处理异常: {}", error)
        await matcher.finish(general.unexpected_error(str(error)))

@asynccontextmanager
async def command_error_handler(
    matcher: type[Matcher],
    action: str = "",
) -> AsyncIterator[None]:
    """
    异步上下文管理器：捕获异常并根据类型发送差异化错误消息。

    替代旧的 ``event_exception_failmsg_a``，提供精确的异常分类响应。

    :param matcher: NoneBot 匹配器对象
    :type matcher: type[Matcher]
    :param action: 当前操作描述（用于日志记录），默认为空字符串
    :type action: str
    """
    try:
        yield
    except (FinishedException, CancelledError):
        raise
    except Exception as e:
        log_prefix = f"命令异常 / {action}" if action else "命令异常"
        logger.error("{}: {}", log_prefix, e, exc_info=True)
        await handle_command_error(matcher, e)

@contextmanager
def suppress_error(action: str = "") -> Iterator[None]:
    """
    同步上下文管理器：捕获并静默忽略异常（仅记录日志）。

    替代旧的 ``event_exception(operation="ignore")``，
    用于非关键操作（如更新展示次数、创建消息映射等）。

    :param action: 当前操作描述（用于日志记录），默认为空字符串
    :type action: str
    """
    try:
        yield
    except (FinishedException, CancelledError):
        raise
    except Exception as e:
        log_prefix = f"非关键操作异常 / {action}" if action else "非关键操作异常"
        logger.warning("{}: {}", log_prefix, e, exc_info=True)

@asynccontextmanager
async def silent_error_handler(
    action: str = "",
    finish_on_error: bool = True,
) -> AsyncIterator[None]:
    """
    异步上下文管理器：静默处理后台任务异常。

    替代旧的 ``event_exception_a(operation="finish")``，
    用于后台监听器等不需要向用户反馈错误详情的场景。

    :param action: 当前操作描述（用于日志记录），默认为空字符串
    :type action: str
    :param finish_on_error: 异常时是否抛出 FinishedException 结束事件，默认为 ``True``
    :type finish_on_error: bool
    """
    try:
        yield
    except (FinishedException, CancelledError):
        raise
    except Exception as e:
        log_prefix = f"后台任务异常 / {action}" if action else "后台任务异常"
        logger.error("{}: {}", log_prefix, e, exc_info=True)
        if finish_on_error:
            raise FinishedException()
