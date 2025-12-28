from .base import ServiceException

class OperationError(ServiceException):
    """操作异常"""
    pass


class DatabaseOperationError(OperationError):
    """数据库操作异常"""
    pass
