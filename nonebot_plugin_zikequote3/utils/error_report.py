from contextlib import contextmanager, asynccontextmanager
from nonebot.matcher import Matcher
from nonebot.exception import FinishedException
import logging
import sentry_sdk

logger = logging.getLogger(__name__)

@contextmanager
def exception_report(error_message: str = "", not_raise: bool = False, ignore_all: bool = False, force_raise_nonebot_finished: bool = True):
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
        elif force_raise_nonebot_finished and isinstance(e, FinishedException):
            raise
        else:
            return
    

@asynccontextmanager
async def exception_finish_failure(matcher: type[Matcher], action: str, entity_name: str | None = None):
    """
    用于捕获异常并通过 matcher 反馈通用失败消息的上下文管理器

    注意，如果已经抛出了一个 Finished 异常，则可能是已经正常结束事件，因此不会重复发送失败消息

    Args:
        matcher (Matcher): NoneBot 匹配器对象
        message (str): 反馈消息内容
    """
    from ..msgtexts import general as mt_g
    try:
        yield
    except Exception as e:
        if not isinstance(e, FinishedException):
            # 非正常结束事件，会告知用户发生异常并向上游传递结束标志
            await matcher.finish(mt_g.failure(action, entity_name, str(e)))
        else:
            # 已经是正常结束事件，直接向上游传递已有的结束标志
            raise