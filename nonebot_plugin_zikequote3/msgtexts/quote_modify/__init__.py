"""
语录修改相关模板渲染方法
"""
from .. import render_template


def add_quote_reply_args_missing() -> str:
    """
    回复方式添加语录参数缺失
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/add_quote_reply_args_missing.jinja2")


def add_quote_failed() -> str:
    """
    添加语录失败
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/add_quote_failed.jinja2")


def add_quote_success() -> str:
    """
    添加语录成功
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/add_quote_success.jinja2")


def remove_quote_reply_args_missing() -> str:
    """
    回复方式删除语录参数缺失
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/remove_quote_reply_args_missing.jinja2")


def remove_quote_success() -> str:
    """
    删除语录成功
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/remove_quote_success.jinja2")


def remove_quote_failed() -> str:
    """
    删除语录失败
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/remove_quote_failed.jinja2")


def remove_quote_id_invalid() -> str:
    """
    删除语录ID无效
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/remove_quote_id_invalid.jinja2")


def comment_quote_reply_args_missing() -> str:
    """
    回复方式评论语录参数缺失
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/comment_quote_reply_args_missing.jinja2")


def comment_quote_success() -> str:
    """
    评论语录成功
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/comment_quote_success.jinja2")


def comment_quote_failed() -> str:
    """
    评论语录失败
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/comment_quote_failed.jinja2")


def quote_not_found() -> str:
    """
    删除语录未找到
    
    Returns:
        渲染后的消息
    """
    return render_template("quote_modify/quote_not_found.jinja2")


__all__ = [
    'add_quote_reply_args_missing',
    'add_quote_failed',
    'add_quote_success',
    'remove_quote_reply_args_missing',
    'remove_quote_success',
    'remove_quote_failed',
    'remove_quote_id_invalid',
    'comment_quote_reply_args_missing',
    'comment_quote_success',
    'comment_quote_failed',
    'quote_not_found',
]