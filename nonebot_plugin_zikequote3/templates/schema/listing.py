"""
语录列表模板渲染方法
"""
from typing import List, Optional

from pydantic import BaseModel

from .. import render_template, read_resource_file


class QuoteBox(BaseModel):
    """语录盒子数据类"""
    quote: str
    comment: Optional[str] = None
    comment_author_name: Optional[str] = None


def render_list(
    title: str,
    description: str,
    addition: str,
    quotes: List[QuoteBox],
    items_per_page: int = 9,
    primary_color: str = "#667eea",
    secondary_color: str = "#764ba2",
    section_colors: Optional[List[str]] = None,
    page_title_template: str = "第 {page_number} 页"
) -> str:
    """
    渲染语录列表HTML

    Args:
        title: 列表标题
        description: 语录信息描述
        addition: 附加信息
        quotes: 全量语录列表
        items_per_page: 每页展示数量
        primary_color: 主色调
        secondary_color: 副色调
        section_colors: 分页标题背景色循环列表
        page_title_template: 分页标题模板（支持 {page_number} 和 {total_pages} 占位符）

    Returns:
        渲染后的HTML字符串
    """
    inline_css = read_resource_file("css/listing.css")

    if section_colors is None:
        section_colors = [
            "#667eea",  # indigo
            "#764ba2",  # purple
            "#f6ad55",  # orange
            "#68d391",  # green
            "#63b3ed",  # blue
            "#ed64a6",  # pink
        ]

    quotes_data = [
        {
            "quote": box.quote,
            "comment": box.comment,
            "comment_author_name": box.comment_author_name,
        }
        for box in quotes
    ]

    return render_template(
        "htmls/listing.html.jinja2",
        inline_css=inline_css,
        title=title,
        description=description,
        addition=addition,
        quotes=quotes_data,
        items_per_page=items_per_page,
        primary_color=primary_color,
        secondary_color=secondary_color,
        section_colors=section_colors,
        page_title_template=page_title_template,
    )


__all__ = [
    "QuoteBox",
    "render_list",
]
