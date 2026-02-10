"""
权限类异常定义。

提供权限校验失败时抛出的异常类。
"""

from .base import ServiceException


class PermissionDeniedError(ServiceException, PermissionError):
    """
    权限不足异常。

    当用户没有执行某操作的权限时抛出。
    """
