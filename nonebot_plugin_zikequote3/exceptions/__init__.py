"""
异常定义模块。

汇总导出插件中所有自定义异常类，供上层业务代码统一引用。
"""

from .base import ZikeQuoteException, ServiceException
from .operations import OperationError, DatabaseOperationError
from .permission import PermissionDeniedError
from .resource import ResourceNotFoundError, UserNotFoundError, QuoteNotFoundError, ImageNotFoundError
from .validation import ValidationException, InvalidAlgorithmError
