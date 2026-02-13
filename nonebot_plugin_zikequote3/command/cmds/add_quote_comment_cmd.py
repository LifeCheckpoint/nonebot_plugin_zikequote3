"""
评论语录命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
"""

from __future__ import annotations

from nonebot import logger

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
from ...di import Inject, inject
from ...services import QuoteWriteService, ReviewService, GroupService
from ._error_handlers import command_error_handler, suppress_error

@matcher_add_quote_comment.handle()
@inject
async def handle_add_quote_comment(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
    quote_write_svc: QuoteWriteService = Inject(QuoteWriteService),
    review_svc: ReviewService = Inject(ReviewService),
    group_svc: GroupService = Inject(GroupService),
) -> None:
    """
    处理评论语录命令（带命令前缀）。

    回复一条语录消息并附带评论内容，将评论写入数据库。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param bot: Bot 实例
    :type bot: Bot
    :param arg: 命令参数消息体
    :type arg: Message
    :param quote_write_svc: 语录写入服务（DI 注入）
    :type quote_write_svc: QuoteWriteService
    :param review_svc: 评论服务（DI 注入）
    :type review_svc: ReviewService
    :param group_svc: 群组服务（DI 注入）
    :type group_svc: GroupService
    """
    reply = event.reply
    content = arg.extract_plain_text().strip()
    if reply is None or content == "":
        await matcher_add_quote_comment.finish("请回复一条语录并输入评论内容哦~")

    group_id = str(event.group_id)

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
    @inject
    async def handle_add_quote_comment_no_prefix(
        event: GroupMessageEvent,
        bot: Bot,
        quote_write_svc: QuoteWriteService = Inject(QuoteWriteService),
        review_svc: ReviewService = Inject(ReviewService),
    ) -> None:
        """
        处理静默评论语录（无命令前缀模式）。

        当用户直接回复语录消息时，自动识别并添加评论。

        :param event: 群消息事件
        :type event: GroupMessageEvent
        :param bot: Bot 实例
        :type bot: Bot
        :param quote_write_svc: 语录写入服务（DI 注入）
        :type quote_write_svc: QuoteWriteService
        :param review_svc: 评论服务（DI 注入）
        :type review_svc: ReviewService
        """
        reply = event.reply
        content = event.get_plaintext().strip()
        if reply is None or content == "":
            return  # 不处理

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
