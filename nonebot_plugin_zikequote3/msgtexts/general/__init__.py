"""
通用操作相关模板渲染方法
"""
from .. import render_template
from typing import Optional


def success(action: str, entity_name: Optional[str] = None, detial: Optional[str] = None) -> str:
    """
    通用成功消息
    
    Returns:
        渲染后的消息
    """
    return render_template(
        "general/success.jinja2",
        action=action, entity_name=entity_name, detial=detial
    )

def failure(action: str, entity_name: Optional[str] = None, detial: Optional[str] = None) -> str:
    """
    通用失败消息
    
    Returns:
        渲染后的消息
    """
    return render_template(
        "general/failure.jinja2",
        action=action, entity_name=entity_name, detial=detial
    )

__all__ = [
    'success',
    'failure',
]