from contextlib import contextmanager, asynccontextmanager
from nonebot.matcher import Matcher
import logging
import sentry_sdk

logger = logging.getLogger(__name__)

@contextmanager
def exception_report(error_message: str = "", not_raise: bool = False, ignore_all: bool = False):
    """
    用于捕获代码块中的异常的上下文管理器

    记录日志、上报 Sentry，重新抛出

    Args:
        error_message (str): 错误信息前缀
    """
    try:
        yield
    except Exception as e:
        if ignore_all:
            return
        
        if error_message == "":
            logger.error(f"操作异常: {e}", stack_info=True)
        else:
            logger.error(f"操作异常 / {error_message}: {e}", stack_info=True)
            
        sentry_sdk.capture_exception(e)
        
        if not not_raise:
            raise
        else:
            return
    

@asynccontextmanager
async def exception_finish_failure(matcher: type[Matcher], action: str, entity_name: str | None = None):
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
        await matcher.finish(mt_g.failure(action, entity_name, str(e)))
        # finish 会抛出 Finished 异常阻断传播
