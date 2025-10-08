from asyncio import CancelledError
from contextlib import contextmanager, asynccontextmanager
from nonebot import logger
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher
from typing import Literal
import sentry_sdk


@contextmanager
def service_exception(error_message: str = "", raise_again: bool = True):
    """
    用于捕获服务层同步上下文中的异常的上下文管理器

    记录日志、上报 Sentry，重新抛出

    Args:
        error_message (str): 错误信息前缀
        raise_again (bool): 是否重新抛出异常
    """
    try:
        yield
    except Exception as e:
        if isinstance(e, CancelledError):
            raise

        if error_message == "":
            logger.error(f"服务操作异常: {e}", stack_info=True)
        else:
            logger.error(f"服务操作异常 / {error_message}: {e}", stack_info=True)
            
        sentry_sdk.capture_exception(e)
        
        if raise_again:
            raise


@contextmanager
def event_exception(error_message: str = "", operation: Literal["raise", "ignore", "finish"] = "ignore"):
    """
    用于捕获事件处理同步上下文中的异常的上下文管理器

    记录日志、上报 Sentry，根据参数决定是否重新抛出

    Args:
        error_message (str): 错误信息前缀
        operation (str): 异常发生时的操作，"raise" 重新抛出异常，"ignore" 忽略异常，"finish" 抛出 FinishedException 结束事件
    """
    try:
        yield
    except Exception as e:
        if isinstance(e, CancelledError) or isinstance(e, FinishedException):
            raise

        if error_message == "":
            logger.error(f"事件操作异常: {e}", stack_info=True)
        else:
            logger.error(f"事件操作异常 / {error_message}: {e}", stack_info=True)
            
        sentry_sdk.capture_exception(e)
        
        if operation == "raise":
            raise
        elif operation == "finish":
            raise FinishedException()
        elif operation == "ignore":
            return
        else:
            raise ValueError(f"未知的 operation 参数: {operation}")


@asynccontextmanager
async def service_exception_a(error_message: str = "", raise_again: bool = True):
    """
    用于捕获服务层异步上下文中的异常的上下文管理器

    记录日志、上报 Sentry，根据参数决定是否重新抛出

    Args:
        error_message (str): 错误信息前缀
        raise_again (bool): 是否重新抛出异常
    """
    try:
        yield
    except Exception as e:
        if isinstance(e, CancelledError):
            raise

        if error_message == "":
            logger.error(f"服务操作异常: {e}", stack_info=True)
        else:
            logger.error(f"服务操作异常 / {error_message}: {e}", stack_info=True)
            
        sentry_sdk.capture_exception(e)
        
        if raise_again:
            raise


@asynccontextmanager
async def event_exception_a(error_message: str = "", operation: Literal["raise", "ignore", "finish"] = "ignore"):
    """
    用于捕获事件处理异步上下文中的异常的上下文管理器

    记录日志、上报 Sentry，根据参数决定是否重新抛出

    Args:
        error_message (str): 错误信息前缀
        operation (str): 异常发生时的操作，"raise" 重新抛出异常，"ignore" 忽略异常，"finish" 抛出 FinishedException 结束事件
    """
    try:
        yield
    except Exception as e:
        if isinstance(e, CancelledError) or isinstance(e, FinishedException):
            raise

        if error_message == "":
            logger.error(f"事件操作异常: {e}", stack_info=True)
        else:
            logger.error(f"事件操作异常 / {error_message}: {e}", stack_info=True)
            
        sentry_sdk.capture_exception(e)
        
        if operation == "raise":
            raise
        elif operation == "finish":
            raise FinishedException()
        elif operation == "ignore":
            return
        else:
            raise ValueError(f"未知的 operation 参数: {operation}")


@asynccontextmanager
async def event_exception_failmsg_a(matcher: type[Matcher], action: str, entity_name: str | None = None):
    """
    用于捕获异常并通过 matcher 反馈通用失败消息的上下文管理器

    Args:
        matcher (Matcher): NoneBot 匹配器对象
        message (str): 反馈消息内容
    """
    from ..msgtexts import general as mt_g
    try:
        yield
    except Exception as e:
        if not isinstance(e, FinishedException):
            await matcher.finish(mt_g.failure(action, entity_name, str(e)))
        else:
            # 正常结束事件
            raise
