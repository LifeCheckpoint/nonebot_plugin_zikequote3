"""
随机语录命令处理器（dishka DI 版本）。

替代旧的 random_quote_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。
"""

from __future__ import annotations

import asyncio
import logging

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot.adapters import Message
from nonebot.params import CommandArg

from ..command_definition_new import matcher_random_quote
from ...di import get_container
from ...services.new import QuoteReadService, QuoteWriteService, UserService
from ...database.image_store import ImageStore
from ...utils.error_report import event_exception_failmsg_a, event_exception
from ...msgtexts.quote_read import send_quote

logger = logging.getLogger(__name__)


@matcher_random_quote.handle()
async def handle_random_quote(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
) -> None:
    """随机语录。"""
    key = arg.extract_plain_text().strip()
    group_id = str(event.group_id)
    send_msg = None

    container = get_container()
    async with container() as request_scope:
        quote_read_svc = await request_scope.get(QuoteReadService)
        quote_write_svc = await request_scope.get(QuoteWriteService)
        user_svc = await request_scope.get(UserService)
        image_store = await request_scope.get(ImageStore)

        async with event_exception_failmsg_a(matcher_random_quote, "获取随机语录"):
            q_result = await quote_read_svc.get_random_quote(
                group_id,
                keyword=key if key else None,
            )

            if q_result is None:
                await matcher_random_quote.finish("没有找到符合条件的语录哦~")

            # 异步更新用户信息缓存
            async def _sync_user_info() -> None:
                try:
                    member_info = await bot.get_group_member_info(
                        group_id=int(group_id), user_id=int(q_result.author_id),
                    )
                    nickname = member_info.get("nickname", "")
                    card = member_info.get("card", "")
                    if nickname:
                        await user_svc.sync_nickname(q_result.author_id, nickname)
                    if card:
                        await user_svc.sync_group_card(q_result.author_id, group_id, card)
                except Exception:
                    logger.debug("同步用户信息失败", exc_info=True)

            asyncio.create_task(_sync_user_info())

            # 获取语录作者当前昵称
            author_card = await user_svc.get_display_name(q_result.author_id, group_id)

            with event_exception(operation="ignore"):
                if q_result.content is not None:
                    text_msg = MsgSeg.text(send_quote(author_card, q_result.content))
                else:
                    text_msg = None

                if q_result.image_content_uuid is None and text_msg is not None:
                    send_msg = await matcher_random_quote.send(text_msg)
                elif q_result.image_content_uuid is not None and text_msg is not None:
                    try:
                        img_path = image_store.get_path(q_result.image_content_uuid)
                        image_data = img_path.read_bytes()
                        full_msg = text_msg + MsgSeg.image(image_data)
                    except FileNotFoundError:
                        full_msg = text_msg + MsgSeg.text("\n（语录图片文件已丢失 O.O）")
                    send_msg = await matcher_random_quote.send(full_msg)
                elif q_result.image_content_uuid is not None and text_msg is None:
                    try:
                        img_path = image_store.get_path(q_result.image_content_uuid)
                        image_data = img_path.read_bytes()
                        send_msg = await matcher_random_quote.send(MsgSeg.image(image_data))
                    except FileNotFoundError:
                        send_msg = await matcher_random_quote.send("（语录图片文件已丢失 O.O）")
                else:
                    raise ValueError("语录内容和图片均为空")

        # 更新语录出现次数
        with event_exception(operation="ignore"):
            await quote_read_svc.increment_show_time(q_result.quote_id)

        # 添加消息映射
        if send_msg is not None:
            with event_exception(operation="ignore"):
                await quote_write_svc.create_msg_quote_mapping(
                    str(send_msg["message_id"]), q_result.quote_id,
                )
