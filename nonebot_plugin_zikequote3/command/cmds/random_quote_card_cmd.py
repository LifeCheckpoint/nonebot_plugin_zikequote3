"""
随机语录卡命令处理器（dishka DI 版本）。

替代旧的 random_quote_card_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。
"""

from __future__ import annotations

import asyncio
import base64
import logging

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot.adapters import Message
from nonebot.params import CommandArg

from ..command_definition import matcher_random_quote_card
from ...di import get_container
from ...services import QuoteReadService, QuoteWriteService, UserService
from ...services.html_render_service import HtmlRenderServiceBase
from ...database.image_store import ImageStore
from ._error_handlers import command_error_handler, suppress_error
from ...templates.schema.card import TemplateCommentData, TemplateQuoteCardData
from ...templates import card as card_template

logger = logging.getLogger(__name__)

# 与旧版 review_service 中的 AI 作者标识保持一致
_AUTHOR_AI = "AI"


def _to_data_uri(data: bytes, mime: str = "image/png") -> str:
    """将二进制数据转换为 Data URI 格式。"""
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


@matcher_random_quote_card.handle()
async def handle_random_quote_card(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
) -> None:
    """随机语录卡，渲染为卡片图片发送。"""
    key = arg.extract_plain_text().strip()
    group_id = str(event.group_id)
    send_msg = None

    container = get_container()
    async with container() as request_scope:
        quote_read_svc = await request_scope.get(QuoteReadService)
        quote_write_svc = await request_scope.get(QuoteWriteService)
        user_svc = await request_scope.get(UserService)
        image_store = await request_scope.get(ImageStore)
        html_render_svc = await request_scope.get(HtmlRenderServiceBase)

        q_result = None

        async with command_error_handler(matcher_random_quote_card, "获取语录卡"):
            q_result = await quote_read_svc.get_random_quote(
                group_id,
                keyword=key if key else None,
            )

            if q_result is None:
                await matcher_random_quote_card.finish("没有找到符合条件的语录哦~")

            # 异步更新用户信息缓存
            async def _sync_user_info() -> None:
                try:
                    member_info = await bot.get_group_member_info(
                        group_id=int(group_id),
                        user_id=int(q_result.author_id),
                    )
                    nickname = member_info.get("nickname", "")
                    card_name = member_info.get("card", "")
                    if nickname:
                        await user_svc.sync_nickname(q_result.author_id, nickname)
                    if card_name:
                        await user_svc.sync_group_card(
                            q_result.author_id, group_id, card_name,
                        )
                except Exception:
                    logger.debug("同步用户信息失败", exc_info=True)

            asyncio.create_task(_sync_user_info())

            # 构建卡片 HTML
            author_name = await user_svc.get_display_name(
                q_result.author_id, group_id,
            )

            # 获取评论
            pair = await quote_read_svc.get_quote_with_reviews(q_result.quote_id)
            comments: list[TemplateCommentData] = []
            if pair is not None:
                _, reviews = pair
                for r in reviews:
                    comment_author = await user_svc.get_display_name(
                        r.author_id, group_id,
                    )
                    if comment_author == _AUTHOR_AI:
                        comment_author = "AI"
                    comments.append(TemplateCommentData(
                        comment_id=r.review_id,
                        author_name=comment_author,
                        content=r.content,
                    ))

            # 获取图片 data URI（如有）
            image_uri = None
            if q_result.image_content_uuid is not None:
                try:
                    img_path = image_store.get_path(q_result.image_content_uuid)
                    image_uri = _to_data_uri(img_path.read_bytes())
                except FileNotFoundError:
                    logger.warning("语录图片文件已丢失: %s", q_result.image_content_uuid)

            # 渲染卡片
            quote_card_html = card_template.render_card(
                TemplateQuoteCardData(
                    quote_id=q_result.quote_id,
                    quote=q_result.content,
                    image_uri=image_uri,
                    author_name=author_name,
                    comments=comments,
                )
            )
            quote_card_img = await html_render_svc.render(quote_card_html, width=800, height=120)
            send_msg = await matcher_random_quote_card.send(MsgSeg.image(quote_card_img))

        # 更新语录出现次数
        if q_result is not None:
            with suppress_error("更新语录出现次数"):
                await quote_read_svc.increment_show_time(q_result.quote_id)

        # 添加消息映射
        if send_msg is not None and q_result is not None:
            with suppress_error("添加消息映射"):
                await quote_write_svc.create_msg_quote_mapping(
                    str(send_msg["message_id"]), q_result.quote_id,
                )
