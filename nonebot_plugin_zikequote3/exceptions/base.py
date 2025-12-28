class ZikeQuoteException(Exception):
    """ZikeQuote 基础异常"""
    pass

class BusinessException(ZikeQuoteException):
    """业务逻辑异常"""
    pass
