"""
语录列表模板渲染方法
"""
from typing import List, Optional

from pydantic import BaseModel

from .. import render_template, read_resource_file


class QuoteBox(BaseModel):
    """语录盒子数据类"""
    quote_id: Optional[str] = None
    quote_text: Optional[str] = None
    quote_image: Optional[str] = None # base64
    quote_author: Optional[str] = None
    quote_comment: Optional[str] = None


def render_list(
    title: str,
    desc: Optional[str],
    addition: Optional[str],
    quotes: List[QuoteBox]
) -> str:
    """
    渲染语录列表HTML

    Args:
        title: 列表标题
        desc: 语录信息描述
        addition: 附加信息
        quotes: 语录列表

    Returns:
        渲染后的HTML字符串
    """
    inline_css = read_resource_file("css/listing.css")

    quotes_data = [
        {
            "quote_id": box.quote_id,
            "quote_text": box.quote_text,
            "quote_image": box.quote_image,
            "quote_author": box.quote_author,
            "quote_comment": box.quote_comment,
        }
        for box in quotes
    ]

    return render_template(
        "htmls/listing.html.jinja2",
        inline_css=inline_css,
        title=title,
        desc=desc,
        addition=addition,
        quotes=quotes_data
    )


__all__ = [
    "QuoteBox",
    "render_list",
]
