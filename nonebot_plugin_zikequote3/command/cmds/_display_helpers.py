"""
命令层共享的展示辅助函数（dishka DI 版本）。

将语录数据转换为模板渲染所需的数据结构，
供 get_quote_list_cmd_new / search_quote_cmd_new 等 handler 复用。
"""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime
from nonebot import logger
from typing import Sequence

from ...database.models.quotes import Quote
from ...database.image_store import ImageStore
from ...services import QuoteReadService, UserService
from ...services.review_service import AUTHOR_AI
from ...templates.schema.listing import TemplateQuoteBoxData

def _to_data_uri(data: bytes, mime: str = "image/png") -> str:
    """
    将二进制数据转换为 Data URI 格式。

    :param data: 原始二进制数据
    :type data: bytes
    :param mime: MIME 类型，默认为 ``"image/png"``
    :type mime: str
    :returns: Base64 编码的 Data URI 字符串
    :rtype: str
    """
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _format_quote_time(time_value: datetime) -> str:
    """格式化语录创建时间，优先转为本地时区显示。"""
    if time_value.tzinfo is not None:
        try:
            time_value = time_value.astimezone()
        except ValueError:
            pass
    return time_value.strftime("%Y-%m-%d %H:%M")


async def transform_quotes_to_template_boxes(
    quotes: Sequence[Quote],
    group_id: str,
    *,
    quote_read_svc: QuoteReadService,
    user_svc: UserService,
    image_store: ImageStore,
    show_id: bool = True,
    show_image: bool = True,
    show_author: bool = False,
    show_time: bool = False,
    show_comment: bool = True,
    max_content_length: int = 0,
) -> list[TemplateQuoteBoxData]:
    """
    将语录数据列表转换为模板渲染所需的 TemplateQuoteBoxData 列表。

    :param quotes: 语录数据列表
    :type quotes: Sequence[Quote]
    :param group_id: 群组 ID
    :type group_id: str
    :param quote_read_svc: 语录读取服务
    :type quote_read_svc: QuoteReadService
    :param user_svc: 用户服务
    :type user_svc: UserService
    :param image_store: 图片存储
    :type image_store: ImageStore
    :param show_id: 是否显示语录 ID，默认为 ``True``
    :type show_id: bool
    :param show_image: 是否显示图片，默认为 ``True``
    :type show_image: bool
    :param show_author: 是否显示作者，默认为 ``False``
    :type show_author: bool
    :param show_time: 是否显示语录创建时间，默认为 ``False``
    :type show_time: bool
    :param show_comment: 是否显示评论，默认为 ``True``
    :type show_comment: bool
    :param max_content_length: 单条语录内容的最大显示字符数，超过则截断并显示 ``"..."``，``0`` 表示不限制
    :type max_content_length: int
    :returns: 模板数据列表
    :rtype: list[TemplateQuoteBoxData]
    """
    boxes: list[TemplateQuoteBoxData] = []

    for qd in quotes:
        # 作者
        author_name = None
        if show_author:
            author_name = await user_svc.get_display_name(qd.author_id, group_id)

        # 首条非 AI 评论
        review_text = None
        if show_comment:
            pair = await quote_read_svc.get_quote_with_reviews(qd.quote_id)
            if pair is not None:
                _, reviews = pair
                review = next(
                    (r for r in reviews if r.author_id != AUTHOR_AI), None,
                )
                if review is not None:
                    review_author = await user_svc.get_display_name(
                        review.author_id, group_id,
                    )
                    review_text = f"{review.content}  ——{review_author}"

        # 图片
        image_uri = None
        if qd.image_content_uuid is not None and show_image:
            try:
                img_path = image_store.get_path(qd.image_content_uuid)
                data = await asyncio.to_thread(img_path.read_bytes)
                image_uri = _to_data_uri(data)
            except Exception:
                logger.warning(
                    "语录列表获取语录 {} 图片失败", qd.quote_id, exc_info=True,
                )

        # 截断超长语录内容
        text = qd.content
        if max_content_length > 0 and text and len(text) > max_content_length:
            text = text[:max_content_length] + "..."

        quote_time = _format_quote_time(qd.time_stamp) if show_time else None

        boxes.append(TemplateQuoteBoxData(
            quote_id=qd.quote_id if show_id else None,
            quote_text=text,
            quote_image=image_uri,
            quote_author=author_name,
            quote_time=quote_time,
            quote_comment=review_text,
        ))

    return boxes
