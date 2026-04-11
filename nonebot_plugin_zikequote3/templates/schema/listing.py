"""
语录列表模板渲染方法。

提供语录列表的数据模型与 HTML 渲染方法。
"""
from typing import List, Optional
from pydantic import BaseModel

from ..registry import LISTING, render_with_spec


class TemplateQuoteBoxData(BaseModel):
    """
    语录盒子数据类。

    :param quote_id: 语录 ID
    :type quote_id: Optional[str]
    :param quote_text: 语录内容
    :type quote_text: Optional[str]
    :param quote_image: 语录图片，base64 编码
    :type quote_image: Optional[str]
    :param quote_author: 语录作者
    :type quote_author: Optional[str]
    :param quote_time: 语录时间（用于最近语录场景等需要展示时间的场合）
    :type quote_time: Optional[str]
    :param quote_comment: 语录评论
    :type quote_comment: Optional[str]
    """

    quote_id: Optional[str] = None
    quote_text: Optional[str] = None
    quote_image: Optional[str] = None
    quote_author: Optional[str] = None
    quote_time: Optional[str] = None
    quote_comment: Optional[str] = None


class TemplateQuoteListData(BaseModel):
    """
    语录列表渲染数据类。

    :param title: 列表标题
    :type title: str
    :param desc: 语录信息描述
    :type desc: Optional[str]
    :param addition: 附加信息
    :type addition: Optional[str]
    :param clamp_hint: 可选，上限截断时的轻提示（用于最近语录场景）
    :type clamp_hint: Optional[str]
    :param quotes: 语录列表
    :type quotes: List[TemplateQuoteBoxData]
    """

    title: str
    desc: Optional[str] = None
    addition: Optional[str] = None
    clamp_hint: Optional[str] = None
    quotes: List[TemplateQuoteBoxData] = []


def render_list(data: TemplateQuoteListData) -> str:
    """
    渲染语录列表 HTML。

    :param data: 语录列表渲染数据
    :type data: TemplateQuoteListData
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """
    return render_with_spec(LISTING, **data.model_dump())


__all__ = [
    "TemplateQuoteBoxData",
    "TemplateQuoteListData",
    "render_list",
]
