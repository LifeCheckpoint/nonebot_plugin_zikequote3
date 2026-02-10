"""
资源类异常定义。

提供资源未找到相关的异常类，如语录、用户、图片未找到等。
"""

from .base import ServiceException


class ResourceNotFoundError(ServiceException):
    """
    资源未找到异常基类。

    当请求的资源不存在时抛出。
    """


class QuoteNotFoundError(ResourceNotFoundError):
    """
    语录未找到异常。

    当请求的语录不存在时抛出。
    """


class UserNotFoundError(ResourceNotFoundError):
    """
    用户未找到异常。

    当请求的用户不存在时抛出。
    """


class ImageNotFoundError(ResourceNotFoundError, FileNotFoundError):
    """
    图片未找到异常。

    当请求的图片不存在时抛出。同时继承 ``FileNotFoundError`` 以兼容文件系统异常捕获。
    """
