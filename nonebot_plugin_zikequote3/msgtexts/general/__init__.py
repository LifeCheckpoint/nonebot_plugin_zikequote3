"""
通用操作相关模板渲染方法。

提供通用成功/失败消息与共享错误消息的模板渲染。
"""
from typing import Optional

from .. import render_template


def success(action: str, entity_name: Optional[str] = None, detial: Optional[str] = None) -> str:
    """
    通用成功消息。

    :param action: 操作名称
    :type action: str
    :param entity_name: 实体名称
    :type entity_name: Optional[str]
    :param detial: 详细信息
    :type detial: Optional[str]
    :returns: 渲染后的消息
    :rtype: str
    """
    return render_template(
        "success.jinja2",
        action=action, entity_name=entity_name, detial=detial
    )


def failure(action: str, entity_name: Optional[str] = None, detial: Optional[str] = None) -> str:
    """
    通用失败消息。

    :param action: 操作名称
    :type action: str
    :param entity_name: 实体名称
    :type entity_name: Optional[str]
    :param detial: 详细信息
    :type detial: Optional[str]
    :returns: 渲染后的消息
    :rtype: str
    """
    return render_template(
        "failure.jinja2",
        action=action, entity_name=entity_name, detial=detial
    )


def validation_error(error: str) -> str:
    """用户输入错误提示。"""
    return render_template(
        "general_command_error.jinja2",
        error_type="validation",
        error=error,
    )


def resource_not_found_error(error: str) -> str:
    """资源不存在提示。"""
    return render_template(
        "general_command_error.jinja2",
        error_type="resource_not_found",
        error=error,
    )


def permission_denied_error(error: str) -> str:
    """权限不足提示。"""
    return render_template(
        "general_command_error.jinja2",
        error_type="permission_denied",
        error=error,
    )


def operation_error(error: str) -> str:
    """操作失败提示。"""
    return render_template(
        "general_command_error.jinja2",
        error_type="operation",
        error=error,
    )


def unexpected_error(error: str) -> str:
    """未知异常提示。"""
    return render_template(
        "general_command_error.jinja2",
        error_type="unexpected",
        error=error,
    )


__all__ = [
    'success',
    'failure',
    'validation_error',
    'resource_not_found_error',
    'permission_denied_error',
    'operation_error',
    'unexpected_error',
]