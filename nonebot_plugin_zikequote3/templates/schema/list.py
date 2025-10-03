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


class Section(BaseModel):
    """分页数据类"""
    title: str
    color: str
    boxes: List[QuoteBox]


def render_list(
    title: str,
    description: str,
    addition: str,
    sections: List[Section],
    primary_color: str = "#667eea",
    secondary_color: str = "#764ba2"
) -> str:
    """
    渲染语录列表HTML
    
    Args:
        title: 列表标题
        description: 语录信息描述
        addition: 附加信息
        sections: 分页语录列表
        primary_color: 主色调
        secondary_color: 副色调
        
    Returns:
        渲染后的HTML字符串
    """
    inline_css = read_resource_file("css/list.css")
    
    # 准备分页数据
    sections_data = []
    for section in sections:
        boxes_data = []
        for box in section.boxes:
            boxes_data.append({
                'quote': box.quote,
                'comment': box.comment,
                'comment_author_name': box.comment_author_name
            })
        sections_data.append({
            'title': section.title,
            'color': section.color,
            'boxes': boxes_data
        })
    
    return render_template(
        "htmls/list.html.jinja2",
        inline_css=inline_css,
        title=title,
        description=description,
        addition=addition,
        sections=sections_data,
        primary_color=primary_color,
        secondary_color=secondary_color
    )


__all__ = [
    'QuoteBox',
    'Section',
    'render_list',
]