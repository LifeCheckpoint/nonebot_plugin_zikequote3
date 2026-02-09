"""
自动收集监听器命令处理器（dishka DI 版本）。

替代旧的 collecting_listener_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。

注意：
- 旧版本通过全局 cfg[group_id].collecting 访问收集配置（msg_max_length、
  update_personal_info_probability 等），新版本暂时保留对旧配置模块的引用。
- LLM 筛选流程由 QuoteCollectionService.collect_and_save 封装。
"""

from __future__ import annotations

import logging
import random
from typing import Any

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from ..command_definition import matcher_collecting_listener
from ...di import get_container
from ...services import (
    QuoteCollectionService,
    GroupService,
    UserService,
)
from ...utils.error_report import event_exception_a, event_exception

logger = logging.getLogger(__name__)


def _load_collecting_config(group_id: int) -> dict[str, Any]:
    """
    从旧配置模块加载收集相关配置。

    TODO: 后续应通过 ConfigService 获取，不再依赖旧的全局 cfg。
    """
    defaults: dict[str, Any] = {
        "msg_max_length": 500,
        "update_personal_info_probability": 0.05,
        "pickup_interval": 80,
    }
    try:
        from ...imports import cfg
        group_cfg = cfg[group_id].collecting
        return {
            "msg_max_length": group_cfg.msg_max_length,
            "update_personal_info_probability": group_cfg.update_personal_info_probability,
            "pickup_interval": group_cfg.pickup_interval,
        }
    except Exception:
        return defaults


@matcher_collecting_listener.handle()
async def handle_collecting_listener(
    event: GroupMessageEvent,
    bot: Bot,
) -> None:
    """
    监听群组消息，处理自动语录收集。

    此事件不会向用户界面提供任何反馈。
    """
    group_id = str(event.group_id)
    user_id = str(event.user_id)
    msg = event.get_plaintext().strip()

    # 加载收集配置
    col_cfg = _load_collecting_config(event.group_id)
    max_length: int = col_cfg["msg_max_length"]
    update_prob: float = col_cfg["update_personal_info_probability"]
    pickup_interval: int = col_cfg["pickup_interval"]

    # 验证收录条件
    if not msg or msg == "" or len(msg) > max_length:
        return

    container = get_container()
    async with container() as request_scope:
        collection_svc = await request_scope.get(QuoteCollectionService)
        group_svc = await request_scope.get(GroupService)
        user_svc = await request_scope.get(UserService)

        # 入队与阈值检查
        is_threshold = False
        async with event_exception_a("收录与阈值检查", operation="finish"):
            await collection_svc.enqueue_message(
                group_id=group_id,
                msg_id=str(event.message_id),
                user_id=user_id,
                content=msg,
            )
            is_threshold = await collection_svc.should_trigger_collection(
                group_id, pickup_interval,
            )

        # 概率更新用户信息
        if random.random() < update_prob:
            async with event_exception_a("更新个人信息", operation="finish"):
                try:
                    member_info = await bot.get_group_member_info(
                        group_id=int(group_id), user_id=int(user_id),
                    )
                    nickname = member_info.get("nickname", "")
                    card = member_info.get("card", "")
                    if nickname:
                        await user_svc.sync_nickname(user_id, nickname)
                    if card:
                        await user_svc.sync_group_card(user_id, group_id, card)
                except Exception:
                    logger.debug("更新个人信息失败", exc_info=True)

        # 检查用户-群映射存在性
        with event_exception(operation="ignore"):
            await group_svc.ensure_member(group_id, user_id)

        # 未达到阈值，结束流程
        if not is_threshold:
            return

        # 异步锁，防止多次触发
        if collection_svc.is_collecting(group_id):
            logger.info(
                "群 %s 的 LLM 收录任务已在进行中，跳过本次触发", group_id,
            )
            return

        # 执行收集流程
        async with event_exception_a("LLM 筛选", operation="finish"):
            quote_ids = await collection_svc.collect_and_save(group_id)
            logger.info("筛选到 %d 条语录", len(quote_ids))

        # TODO: 旧版本会为每条语录添加 AI 评论
        # （s_add_review(AUTHOR_AI, quote_id, comment)），
        # 但 collect_and_save 目前只返回 quote_ids，
        # 不返回 SelectedQuote（含 comment）。
        # 需要后续扩展 collect_and_save 的返回值以支持 AI 评论。

        # 清空队列
        with event_exception("清空队列", operation="finish"):
            await collection_svc.clear_queue(group_id)
