"""
设置相关模板渲染方法
"""
from .. import render_template


def quote_setting_showing_failed() -> str:
    """
    语录设置生成失败
    
    Returns:
        渲染后的消息
    """
    return render_template("settings/quote_setting_showing_failed.jinja2")


def quote_setting_update_failed() -> str:
    """
    语录设置更新失败
    
    Returns:
        渲染后的消息
    """
    return render_template("settings/quote_setting_update_failed.jinja2")


def quote_setting_reload_failed() -> str:
    """
    语录设置重载失败
    
    Returns:
        渲染后的消息
    """
    return render_template("settings/quote_setting_reload_failed.jinja2")


__all__ = [
    'quote_setting_showing_failed',
    'quote_setting_update_failed',
    'quote_setting_reload_failed',
]