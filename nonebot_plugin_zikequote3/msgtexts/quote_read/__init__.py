"""
语录读取相关模板渲染方法。

提供语录读取场景下的消息模板渲染。
"""
from typing import Optional
from .. import render_template


def api_request_error(error: Optional[str] = None) -> str:
    """
    API 请求错误。

    :param error: 错误信息
    :type error: Optional[str]
    :returns: 渲染后的消息
    :rtype: str
    """
    return render_template("api_request_error.jinja2", error=error)


def send_quote(author: str, quote: str) -> str:
    """
    发送语录。

    :param author: 作者
    :type author: str
    :param quote: 语录内容
    :type quote: str
    :returns: 渲染后的消息
    :rtype: str
    """
    return render_template("send_quote.jinja2", author=author, quote=quote)


def quote_not_found(key: Optional[str] = None) -> str:
    """
    语录未找到。

    :param key: 搜索关键词
    :type key: Optional[str]
    :returns: 渲染后的消息
    :rtype: str
    """
    return render_template("quote_not_found.jinja2", key=key)


def quote_search_empty() -> str:
    """
    语录搜索关键词为空。

    :returns: 渲染后的消息
    :rtype: str
    """
    return render_template("quote_search_empty.jinja2")


__all__ = [
    'api_request_error',
    'send_quote',
    'quote_not_found',
    'quote_search_empty',
]