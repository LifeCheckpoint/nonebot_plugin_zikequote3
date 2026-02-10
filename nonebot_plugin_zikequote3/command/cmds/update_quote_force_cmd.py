"""
强制更新语录命令处理器（dishka DI 版本）。

替代旧的 update_quote_force_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。

注意：旧版本依赖 LLM 筛选服务（s_llm_selection）和自定义锁机制，
新版本使用 QuoteCollectionService 封装的 collect_and_save 流程。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.typing import T_State

from ..command_definition import matcher_update_quote_force
from ...di import get_container
from ...services import QuoteCollectionService, ReviewService
from ...services.review_service import AUTHOR_AI
from ._error_handlers import command_error_handler

logger = logging.getLogger(__name__)


@matcher_update_quote_force.handle()
async def handle_update_quote_force(
    event: GroupMessageEvent,
    state: T_State,
) -> None:
    """强制更新语录，与自动收集命令流程类似。"""
    group_id = str(event.group_id)

    container = get_container()
    async with container() as request_scope:
        collection_svc = await request_scope.get(QuoteCollectionService)
        review_svc = await request_scope.get(ReviewService)

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
