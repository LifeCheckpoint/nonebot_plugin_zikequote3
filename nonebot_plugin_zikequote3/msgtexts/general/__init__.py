"""
通用操作相关模板渲染方法。

提供通用成功/失败消息的模板渲染。
"""
from .. import render_template
from typing import Optional


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

__all__ = [
    'success',
    'failure',
]