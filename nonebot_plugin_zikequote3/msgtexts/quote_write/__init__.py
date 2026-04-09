"""
语录写入相关模板渲染方法。

提供添加/删除语录与评论场景下的消息模板渲染。
"""
from .. import render_template


def add_quote_reply_required() -> str:
    """添加语录时缺少回复消息。"""
    return render_template("quote_write_messages.jinja2", message_key="add_quote_reply_required")


def add_quote_reply_to_self() -> str:
    """添加语录时回复了机器人自己。"""
    return render_template("quote_write_messages.jinja2", message_key="add_quote_reply_to_self")


def add_quote_empty_content() -> str:
    """添加语录时内容为空。"""
    return render_template("quote_write_messages.jinja2", message_key="add_quote_empty_content")


def add_quote_success() -> str:
    """添加语录成功。"""
    return render_template("quote_write_messages.jinja2", message_key="add_quote_success")


def remove_quote_target_required() -> str:
    """删除语录时缺少目标。"""
    return render_template("quote_write_messages.jinja2", message_key="remove_quote_target_required")


def remove_quote_success() -> str:
    """删除语录成功。"""
    return render_template("quote_write_messages.jinja2", message_key="remove_quote_success")


def add_quote_comment_required() -> str:
    """添加评论时缺少回复或评论内容。"""
    return render_template("quote_write_messages.jinja2", message_key="add_quote_comment_required")


def add_quote_comment_quote_not_found() -> str:
    """添加评论时未找到对应语录。"""
    return render_template("quote_write_messages.jinja2", message_key="add_quote_comment_quote_not_found")


def add_quote_comment_success() -> str:
    """添加评论成功。"""
    return render_template("quote_write_messages.jinja2", message_key="add_quote_comment_success")


def remove_quote_comment_required() -> str:
    """删除评论时缺少评论 ID。"""
    return render_template("quote_write_messages.jinja2", message_key="remove_quote_comment_required")


def remove_quote_comment_success() -> str:
    """删除评论成功。"""
    return render_template("quote_write_messages.jinja2", message_key="remove_quote_comment_success")


__all__ = [
    'add_quote_reply_required',
    'add_quote_reply_to_self',
    'add_quote_empty_content',
    'add_quote_success',
    'remove_quote_target_required',
    'remove_quote_success',
    'add_quote_comment_required',
    'add_quote_comment_quote_not_found',
    'add_quote_comment_success',
    'remove_quote_comment_required',
    'remove_quote_comment_success',
]
