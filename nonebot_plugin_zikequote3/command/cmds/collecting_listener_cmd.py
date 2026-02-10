"""
自动收集监听器命令处理器（dishka DI 版本）。

替代旧的 collecting_listener_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。

收集配置通过 ConfigService.get_parsed_config() 获取，
LLM 筛选流程由 QuoteCollectionService.collect_and_save 封装。
"""

from __future__ import annotations

import logging
import random

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from ..command_definition import matcher_collecting_listener
from ...di import get_container
from ...services import (
    ConfigService,
    QuoteCollectionService,
    GroupService,
    UserService,
)
from ._error_handlers import silent_error_handler, suppress_error

logger = logging.getLogger(__name__)


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

    container = get_container()
    async with container() as request_scope:
        config_svc = await request_scope.get(ConfigService)
        collection_svc = await request_scope.get(QuoteCollectionService)
        group_svc = await request_scope.get(GroupService)
        user_svc = await request_scope.get(UserService)

        # 通过 ConfigService 加载收集配置
        parsed_cfg = await config_svc.get_parsed_config(group_id)
        max_length: int = parsed_cfg.collecting.msg_max_length
        update_prob: float = parsed_cfg.collecting.update_personal_info_probability
        pickup_interval: int = parsed_cfg.collecting.pickup_interval

        # 验证收录条件
        if not msg or msg == "" or len(msg) > max_length:
            return

        # 入队与阈值检查
        is_threshold = False
        async with silent_error_handler("收录与阈值检查"):
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
            async with silent_error_handler("更新个人信息"):
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
        with suppress_error("检查用户-群映射"):
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
        async with silent_error_handler("LLM 筛选"):
            quote_ids = await collection_svc.collect_and_save(group_id)
            logger.info("筛选到 %d 条语录", len(quote_ids))

        # TODO: 旧版本会为每条语录添加 AI 评论
        # （s_add_review(AUTHOR_AI, quote_id, comment)），
        # 但 collect_and_save 目前只返回 quote_ids，
        # 不返回 SelectedQuote（含 comment）。
        # 需要后续扩展 collect_and_save 的返回值以支持 AI 评论。

        # 清空队列
        with suppress_error("清空队列"):
            await collection_svc.clear_queue(group_id)
