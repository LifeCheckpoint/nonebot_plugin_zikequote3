"""
迁移差异项渲染模板
"""

from typing import List, Optional
from pydantic import BaseModel
from .. import render_template
from ...imports import PluginPath


class DiffItem(BaseModel):
    label: str
    oldval: str
    newval: str


def render_migration_diff(
    status_title: Optional[str],
    title: str,
    description: str,
    diff_items: List[DiffItem],
    left_button: Optional[str],
    right_button: Optional[str],
) -> str:
    """
    渲染差异项，用于迁移比对等

    Args:
        status_title: 可选，标题上方的状态提示小标题
        title: 提示主标题
        description: 描述信息
        diff_items: 差异项目，包含名称、旧值、新值
        left_button: 可选，左按钮（第二按钮）提示信息
        right_button: 可选，右按钮（主按钮）提示信息

    Returns:
        渲染后的 HTML 字符串
    """

    migration_css = PluginPath.module_templates_root / "src" / "assets" / "css" / "migration.css"

    # 准备差异数据
    diff_data = [{
        "label": item.label,
        "oldval": item.oldval,
        "newval": item.newval
    } for item in diff_items]

    return render_template(
        "htmls/migration.html.jinja2",
        inline_css=migration_css.read_text(encoding="utf-8"),
        
        status_title=status_title,
        title=title,
        description=description,
        diff_items=diff_data,
        left_button=left_button,
        right_button=right_button
    )

__all__ = [
    "DiffItem",
    "render_migration_diff",
]