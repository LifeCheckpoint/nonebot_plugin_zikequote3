"""
操作类异常定义。

提供操作失败相关的异常类，如数据库操作异常等。
"""

from .base import ServiceException


class OperationError(ServiceException):
    """
    操作异常基类。

    当业务操作执行失败时抛出。
    """


class DatabaseOperationError(OperationError):
    """
    数据库操作异常。

    当数据库层面的操作执行失败时抛出。
    """
