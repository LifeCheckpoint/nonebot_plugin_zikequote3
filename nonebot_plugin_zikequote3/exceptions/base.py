"""
异常基类定义。

提供插件异常体系的根类 :class:`ZikeQuoteException` 和业务逻辑异常基类 :class:`ServiceException`。
"""


class ZikeQuoteException(Exception):
    """
    ZikeQuote 插件的根异常类。

    所有插件自定义异常均应继承此类。
    """


class ServiceException(ZikeQuoteException):
    """
    业务逻辑异常基类。

    所有服务层抛出的业务异常均应继承此类。
    """
