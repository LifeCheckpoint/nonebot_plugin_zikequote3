"""
校验类异常定义。

提供数据校验失败时抛出的异常类。
"""

from .base import ServiceException


class ValidationException(ServiceException):
    """
    校验类异常基类。

    当输入数据校验失败时抛出。
    """


class InvalidAlgorithmError(ValidationException):
    """
    算法参数错误异常。

    当指定的算法名称或参数不合法时抛出。
    """
