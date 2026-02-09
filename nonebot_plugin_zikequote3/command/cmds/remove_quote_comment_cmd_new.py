"""
删除评论命令处理器（dishka DI 版本）。

替代旧的 remove_quote_comment_cmd.py，消除星号导入和延迟导入，
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

from ..command_definition_new import matcher_remove_quote_comment
from ...di import get_container
from ...services import ReviewService
from ...utils.error_report import event_exception_failmsg_a

logger = logging.getLogger(__name__)


@matcher_remove_quote_comment.handle()
async def handle_remove_quote_comment(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
) -> None:
    """
    删除评论。

    使用方式：``/删评论 评论ID``
    """
    review_id = arg.extract_plain_text().strip()
    if not review_id:
        await matcher_remove_quote_comment.finish(
            "请提供要删除的评论 ID 哦~\n用法：/删评论 评论ID"
        )

    container = get_container()
    async with container() as request_scope:
        review_svc = await request_scope.get(ReviewService)

        async with event_exception_failmsg_a(
            matcher_remove_quote_comment, "删除评论"
        ):
            await review_svc.delete_review(review_id)

        await matcher_remove_quote_comment.finish("评论删除成功~(≧▽≦)")
