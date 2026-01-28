"""
迁移差异项渲染模板
"""

from typing import List, Optional
from pydantic import BaseModel
from .. import render_template, read_resource_file


class TemplateDiffItemData(BaseModel):
    """差异项数据类"""

    """差异项名称"""
    label: str

    """旧值"""
    oldval: str

    """新值"""
    newval: str

class TemplateMigrationData(BaseModel):
    """迁移渲染数据类"""

    """可选，标题上方的状态提示小标题"""
    status_title: Optional[str] = None

    """提示主标题"""
    title: str

    """描述信息"""
    description: str

    """差异项目，包含名称、旧值、新值"""
    diff_items: List[TemplateDiffItemData]

    """左按钮（第二按钮）提示信息"""
    left_button: Optional[str] = None

    """右按钮（主按钮）提示信息"""
    right_button: Optional[str] = None


def render_migration_diff(data: TemplateMigrationData) -> str:
    """
    渲染差异项，用于迁移比对等

    Args:
        data: 迁移渲染数据

    Returns:
        渲染后的 HTML 字符串
    """

    migration_css = read_resource_file("css/migration.css")

    return render_template(
        "htmls/migration.html.jinja2",
        inline_css=migration_css,
        **data.model_dump()
    )

__all__ = [
    "TemplateDiffItemData",
    "TemplateMigrationData",
    "render_migration_diff",
]