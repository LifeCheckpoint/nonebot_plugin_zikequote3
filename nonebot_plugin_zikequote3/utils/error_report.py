from contextlib import contextmanager
import logging
import sentry_sdk

logger = logging.getLogger(__name__)

@contextmanager
def error_report(error_message: str):
    """
    用于捕获代码块中的异常的上下文管理器

    记录日志、上报 Sentry，重新抛出

    Args:
        error_message (str): 错误信息前缀
    """
    try:
        yield
    except Exception as e:
        logger.error(f"操作异常 / {error_message}: {e}", stack_info=True)
        sentry_sdk.capture_exception(e)
        raise
