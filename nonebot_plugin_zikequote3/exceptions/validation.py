from .base import ServiceException

class ValidationException(ServiceException):
    """校验类异常"""


class InvalidAlgorithmError(ValidationException):
    """算法参数错误"""
