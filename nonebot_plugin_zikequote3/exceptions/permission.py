from .base import ServiceException

class PermissionDeniedError(ServiceException, PermissionError):
    """权限不足异常"""
    pass
