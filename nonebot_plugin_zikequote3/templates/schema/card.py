"""
语录卡片模板
"""
from typing import List, Optional
from pydantic import BaseModel
from .. import render_template, read_resource_file


class TemplateCommentData(BaseModel):
    """评论渲染数据类"""

    """评论内容"""
    content: str

    """作者姓名"""
    author_name: Optional[str] = None

    """评论 ID"""
    comment_id: Optional[str] = None

class TemplateQuoteCardData(BaseModel):
    """语录卡片渲染数据类"""
    
    """语录 ID"""
    quote_id: str

    """语录内容"""
    quote: Optional[str] = None

    """语录图片 URI"""
    image_uri: Optional[str] = None

    """作者姓名"""
    author_name: str

    """评论列表"""
    comments: Optional[List[TemplateCommentData]] = None
    
    """主色调"""
    primary_color: str = "#667eea"

    """副色调"""
    secondary_color: str = "#764ba2"


def render_card(data: TemplateQuoteCardData) -> str:
    """
    渲染语录卡片HTML
    
    Args:
        data: 语录卡片渲染数据
        
    Returns:
        渲染后的 HTML 字符串
    """
    inline_css = read_resource_file("css/card.css")
    
    return render_template(
        "htmls/card.html.jinja2",
        inline_css=inline_css,
        **data.model_dump()
    )


__all__ = [
    "TemplateCommentData",
    "TemplateQuoteCardData",
    "render_card",
]