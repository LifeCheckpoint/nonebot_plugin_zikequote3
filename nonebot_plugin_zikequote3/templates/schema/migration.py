"""
迁移差异项渲染模板。

提供迁移差异项的数据模型与 HTML 渲染方法。
"""

from typing import List, Optional
from pydantic import BaseModel
from ..registry import MIGRATION, render_with_spec


class TemplateDiffItemData(BaseModel):
    """
    差异项数据类。

    :param label: 差异项名称
    :type label: str
    :param oldval: 旧值
    :type oldval: str
    :param newval: 新值
    :type newval: str
    """

    label: str
    oldval: str
    newval: str

class TemplateMigrationData(BaseModel):
    """
    迁移渲染数据类。

    :param status_title: 可选，标题上方的状态提示小标题
    :type status_title: Optional[str]
    :param title: 提示主标题
    :type title: str
    :param description: 描述信息
    :type description: str
    :param diff_items: 差异项目，包含名称、旧值、新值
    :type diff_items: List[TemplateDiffItemData]
    :param left_button: 左按钮（第二按钮）提示信息
    :type left_button: Optional[str]
    :param right_button: 右按钮（主按钮）提示信息
    :type right_button: Optional[str]
    """

    status_title: Optional[str] = None
    title: str
    description: str
    diff_items: List[TemplateDiffItemData]
    left_button: Optional[str] = None
    right_button: Optional[str] = None


def render_migration_diff(data: TemplateMigrationData) -> str:
    """
    渲染差异项，用于迁移比对等。

    :param data: 迁移渲染数据
    :type data: TemplateMigrationData
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """

    return render_with_spec(MIGRATION, **data.model_dump())

__all__ = [
    "TemplateDiffItemData",
    "TemplateMigrationData",
    "render_migration_diff",
]