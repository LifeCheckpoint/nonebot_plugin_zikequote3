class ZikeQuoteException(Exception):
    """ZikeQuote 基础异常"""
    pass

class ServiceException(ZikeQuoteException):
    """业务逻辑异常"""
    pass
