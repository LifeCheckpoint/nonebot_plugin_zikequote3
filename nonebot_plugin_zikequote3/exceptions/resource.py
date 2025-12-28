from .base import ServiceException

class ResourceNotFoundError(ServiceException):
    """
    资源未找到异常

    当请求的资源不存在时引发此异常。
    """
    pass


class QuoteNotFoundError(ResourceNotFoundError):
    """
    语录未找到异常

    当请求的语录不存在时引发此异常。
    """
    pass


class UserNotFoundError(ResourceNotFoundError):
    """
    用户未找到异常

    当请求的用户不存在时引发此异常。
    """
    pass


class ImageNotFoundError(ResourceNotFoundError, FileNotFoundError):
    """
    图片未找到异常

    当请求的图片不存在时引发此异常。
    """
    pass
