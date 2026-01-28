"""
语录列表模板渲染方法
"""
from typing import List, Optional
from pydantic import BaseModel

from .. import render_template, read_resource_file


class TemplateQuoteBoxData(BaseModel):
    """语录盒子数据类"""
    
    """语录ID"""
    quote_id: Optional[str] = None

    """语录内容"""
    quote_text: Optional[str] = None

    """语录图片，base64编码"""
    quote_image: Optional[str] = None

    """语录作者"""
    quote_author: Optional[str] = None

    """语录评论"""
    quote_comment: Optional[str] = None


class TemplateQuoteListData(BaseModel):
    """语录列表渲染数据类"""
    
    """列表标题"""
    title: str

    """语录信息描述"""
    desc: Optional[str] = None

    """附加信息"""
    addition: Optional[str] = None

    """语录列表"""
    quotes: List[TemplateQuoteBoxData] = []


def render_list(data: TemplateQuoteListData) -> str:
    """
    渲染语录列表HTML

    Args:
        data: 语录列表渲染数据

    Returns:
        渲染后的HTML字符串
    """
    inline_css = read_resource_file("css/listing.css")

    return render_template(
        "htmls/listing.html.jinja2",
        inline_css=inline_css,
        **data.model_dump()
    )


__all__ = [
    "TemplateQuoteBoxData",
    "TemplateQuoteListData",
    "render_list",
]
