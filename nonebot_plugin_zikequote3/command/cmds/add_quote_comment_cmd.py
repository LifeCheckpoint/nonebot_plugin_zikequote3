"""
评论语录命令处理器（dishka DI 版本）。

替代旧的 add_quote_comment_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
)
from nonebot.adapters import Message
from nonebot.params import CommandArg

from ..command_definition import (
    matcher_add_quote_comment,
    matcher_add_quote_comment_no_prefix,
)
from ...di import get_container
from ...services import QuoteWriteService, ReviewService, GroupService
from ._error_handlers import command_error_handler, suppress_error

logger = logging.getLogger(__name__)


@matcher_add_quote_comment.handle()
async def handle_add_quote_comment(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
) -> None:
    """评论语录（带命令前缀）。"""
    reply = event.reply
    content = arg.extract_plain_text().strip()
    if reply is None or content == "":
        await matcher_add_quote_comment.finish("请回复一条语录并输入评论内容哦~")

    group_id = str(event.group_id)

    container = get_container()
    async with container() as request_scope:
        quote_write_svc = await request_scope.get(QuoteWriteService)
        review_svc = await request_scope.get(ReviewService)
        group_svc = await request_scope.get(GroupService)

        async with command_error_handler(matcher_add_quote_comment, "添加评论"):
            # 获取语录 ID
            quote_id = await quote_write_svc.get_quote_id_by_msg_id(str(reply.message_id))
            if quote_id is None:
                raise ValueError("未找到对应语录，无法评论呢~")

            # 添加评论
            await review_svc.add_review(
                quote_id=quote_id,
                author_id=str(event.sender.user_id),
                content=content,
            )

            await matcher_add_quote_comment.send("评论添加成功~(≧▽≦)")

        # 检查用户-群映射存在性
        with suppress_error("检查用户-群映射"):
            await group_svc.ensure_member(group_id, str(event.sender.user_id))


# 无前缀评论（静默模式）
if matcher_add_quote_comment_no_prefix is not None:

    @matcher_add_quote_comment_no_prefix.handle()
    async def handle_add_quote_comment_no_prefix(
        event: GroupMessageEvent,
        bot: Bot,
    ) -> None:
        """静默评论语录（无前缀）。"""
        reply = event.reply
        content = event.get_plaintext().strip()
        if reply is None or content == "":
            return  # 不处理

        container = get_container()
        async with container() as request_scope:
            quote_write_svc = await request_scope.get(QuoteWriteService)
            review_svc = await request_scope.get(ReviewService)

            async with command_error_handler(
                matcher_add_quote_comment_no_prefix, "添加评论"
            ):
                # 获取语录 ID
                quote_id = await quote_write_svc.get_quote_id_by_msg_id(
                    str(reply.message_id)
                )
                if quote_id is None:
                    # 正常消息，不要处理
                    return

                # 添加评论
                await review_svc.add_review(
                    quote_id=quote_id,
                    author_id=str(event.sender.user_id),
                    content=content,
                )
