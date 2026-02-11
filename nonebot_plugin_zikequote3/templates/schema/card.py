"""
语录卡片模板。

提供语录卡片的数据模型与 HTML 渲染方法。
"""
from typing import List, Optional
from pydantic import BaseModel
from ..registry import CARD, render_with_spec


class TemplateCommentData(BaseModel):
    """
    评论渲染数据类。

    :param content: 评论内容
    :type content: str
    :param author_name: 作者姓名
    :type author_name: Optional[str]
    :param comment_id: 评论 ID
    :type comment_id: Optional[str]
    """

    content: str
    author_name: Optional[str] = None
    comment_id: Optional[str] = None

class TemplateQuoteCardData(BaseModel):
    """
    语录卡片渲染数据类。

    :param quote_id: 语录 ID
    :type quote_id: str
    :param quote: 语录内容
    :type quote: Optional[str]
    :param image_uri: 语录图片 URI
    :type image_uri: Optional[str]
    :param author_name: 作者姓名
    :type author_name: str
    :param comments: 评论列表
    :type comments: Optional[List[TemplateCommentData]]
    :param primary_color: 主色调
    :type primary_color: str
    :param secondary_color: 副色调
    :type secondary_color: str
    """

    quote_id: str
    quote: Optional[str] = None
    image_uri: Optional[str] = None
    author_name: str
    comments: Optional[List[TemplateCommentData]] = None
    primary_color: str = "#667eea"
    secondary_color: str = "#764ba2"


def render_card(data: TemplateQuoteCardData) -> str:
    """
    渲染语录卡片 HTML。

    :param data: 语录卡片渲染数据
    :type data: TemplateQuoteCardData
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """
    return render_with_spec(CARD, **data.model_dump())


__all__ = [
    "TemplateCommentData",
    "TemplateQuoteCardData",
    "render_card",
]