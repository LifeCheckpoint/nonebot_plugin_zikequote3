"""
普通操作相关模板渲染方法
"""
from .. import render_template


def quote_on_update() -> str:
    """
    语录更新中
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_on_update.jinja2")


def quote_update_success() -> str:
    """
    语录更新成功
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_update_success.jinja2")


def quote_update_failed() -> str:
    """
    语录更新失败
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_update_failed.jinja2")


__all__ = [
    'quote_on_update',
    'quote_update_success',
    'quote_update_failed',
]