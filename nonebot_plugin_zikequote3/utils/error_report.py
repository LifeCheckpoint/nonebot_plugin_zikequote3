from contextlib import contextmanager
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
    