"""
强制更新语录命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。

注意：旧版本依赖 LLM 筛选服务（s_llm_selection）和自定义锁机制，
新版本使用 QuoteCollectionService 封装的 collect_and_save 流程。
"""

from __future__ import annotations

from nonebot import logger

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.typing import T_State

from ..command_definition import matcher_update_quote_force
from ...di import Inject, inject
from ...services import QuoteCollectionService, ReviewService
from ...services.review_service import AUTHOR_AI
from ._error_handlers import command_error_handler

@matcher_update_quote_force.handle()
@inject
async def handle_update_quote_force(
    event: GroupMessageEvent,
    state: T_State,
    collection_svc: QuoteCollectionService = Inject(QuoteCollectionService),
    review_svc: ReviewService = Inject(ReviewService),
) -> None:
    """
    处理强制更新语录命令。

    手动触发 LLM 筛选收集流程，与自动收集监听器流程类似。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param state: NoneBot 状态字典
    :type state: T_State
    :param collection_svc: 语录收集服务（DI 注入）
    :type collection_svc: QuoteCollectionService
    :param review_svc: 评论服务（DI 注入）
    :type review_svc: ReviewService
    """
    group_id = str(event.group_id)

    # 检查是否已有收集任务在进行中
    if collection_svc.is_collecting(group_id):
        await matcher_update_quote_force.finish(
            "当前已有更新任务在进行中，请稍后再试~"
        )

    async with command_error_handler(
        matcher_update_quote_force, "语录强制更新"
    ):
        # 执行收集流程（包含锁、队列取出、筛选、保存）
        collected = await collection_svc.collect_and_save(group_id)

        # 为每条语录添加 AI 评论
        for item in collected:
            if item.comment:
                await review_svc.add_review(
                    quote_id=item.quote_id,
                    author_id=AUTHOR_AI,
                    content=item.comment,
                )

        # 清空队列
        await collection_svc.clear_queue(group_id)

    num_quotes = len(collected)
    await matcher_update_quote_force.finish(
        f"本次语录更新完成，共新增 {num_quotes} 条语录~"
    )
