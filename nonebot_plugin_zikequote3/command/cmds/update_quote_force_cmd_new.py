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

from ..command_definition_new import matcher_update_quote_force
from ...di import get_container
from ...services.new import QuoteCollectionService, ReviewService
from ...services.new.quote_collection_service import CollectionLockError
from ...services.new.review_service import AUTHOR_AI
from ...utils.error_report import event_exception_failmsg_a, event_exception

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

        async with event_exception_failmsg_a(
            matcher_update_quote_force, "语录强制更新"
        ):
            # 执行收集流程（包含锁、队列取出、筛选、保存）
            quote_ids = await collection_svc.collect_and_save(group_id)

            # TODO: QuoteCollectionService.collect_and_save 目前只返回 quote_ids，
            # 不返回 SelectedQuote 列表（含 comment），因此无法为每条语录添加 AI 评论。
            # 旧版本会调用 s_add_review(AUTHOR_AI, quote_id, quote.comment) 为每条语录
            # 添加 AI 生成的评论。需要后续在 Service 层补充返回 SelectedQuote 的方法，
            # 或者扩展 collect_and_save 的返回值。

            # 清空队列
            await collection_svc.clear_queue(group_id)

        num_quotes = len(quote_ids)
        await matcher_update_quote_force.finish(
            f"本次语录更新完成，共新增 {num_quotes} 条语录~"
        )
