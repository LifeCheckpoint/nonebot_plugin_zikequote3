"""
语录读取相关模板渲染方法
"""
from typing import Optional
from .. import render_template


def api_request_error(error: Optional[str] = None) -> str:
    """
    API请求错误
    
    Args:
        error: 错误信息
        
    Returns:
        渲染后的消息
    """
    return render_template("quote_read/api_request_error.jinja2", error=error)


def send_quote(author: str, quote: str) -> str:
    """
    发送语录
    
    Args:
        author: 作者
        quote: 语录内容
        
    Returns:
        渲染后的消息
    """
    return render_template("quote_read/send_quote.jinja2", author=author, quote=quote)


def quote_not_found(key: Optional[str] = None) -> str:
    """
    语录未找到
    
    Args:
        key: 搜索关键词
        
    Returns:
        渲染后的消息
    """
    return render_template("quote_read/quote_not_found.jinja2", key=key)


def quote_search_empty() -> str:
    """
    语录搜索关键词为空
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_read/quote_search_empty.jinja2")


__all__ = [
    'api_request_error',
    'send_quote',
    'quote_not_found',
    'quote_search_empty',
]