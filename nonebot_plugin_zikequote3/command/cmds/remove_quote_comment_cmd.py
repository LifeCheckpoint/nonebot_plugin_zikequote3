"""
删除评论命令处理器。

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

from ..command_definition import matcher_remove_quote_comment, perm_nodes
from ...di import Inject, inject
from ...exceptions import PermissionDeniedError
from ...services import ReviewService
from ._error_handlers import command_error_handler

@matcher_remove_quote_comment.handle()
@inject
async def handle_remove_quote_comment(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
    review_svc: ReviewService = Inject(ReviewService),
) -> None:
    """
    处理删除评论命令。

    使用方式：``/删评论 评论ID``

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param bot: Bot 实例
    :type bot: Bot
    :param arg: 命令参数消息体
    :type arg: Message
    :param review_svc: 评论服务（DI 注入）
    :type review_svc: ReviewService
    """
    review_id = arg.extract_plain_text().strip()
    if not review_id:
        await matcher_remove_quote_comment.finish(
            "请提供要删除的评论 ID 哦~\n用法：/删评论 评论ID"
        )

    operator_id = str(event.user_id)

    async with command_error_handler(
        matcher_remove_quote_comment, "删除评论"
    ):
        allow_delete_others = False
        review = await review_svc.get_review_by_id(review_id)
        if review is not None:
            if review.author_id == operator_id:
                allowed = await perm_nodes.n_review_delete_self.check(
                    bot,
                    event,
                    throw_on_fail=False,
                )
                if not allowed:
                    raise PermissionDeniedError(
                        f"缺少删除自己评论权限（review_id={review_id}）"
                    )
            else:
                allowed = await perm_nodes.n_review_delete_others.check(
                    bot,
                    event,
                    throw_on_fail=False,
                )
                if not allowed:
                    raise PermissionDeniedError(
                        f"缺少删除他人评论权限（review_id={review_id}）"
                    )
                allow_delete_others = True

        await review_svc.delete_review(
            review_id,
            operator_id=operator_id,
            allow_delete_others=allow_delete_others,
        )

    await matcher_remove_quote_comment.finish("评论删除成功~(≧▽≦)")
