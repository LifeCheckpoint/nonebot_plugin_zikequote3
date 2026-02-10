"""
自动收集监听器命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。

收集配置通过 ConfigService.get_parsed_config() 获取，
LLM 筛选流程由 QuoteCollectionService.collect_and_save 封装。
"""

from __future__ import annotations

import logging
import random

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from ..command_definition import matcher_collecting_listener
from ...di import Inject, inject
from ...services import (
    ConfigService,
    QuoteCollectionService,
    GroupService,
    ReviewService,
    UserService,
)
from ...services.review_service import AUTHOR_AI
from ._error_handlers import silent_error_handler, suppress_error

logger = logging.getLogger(__name__)


@matcher_collecting_listener.handle()
@inject
async def handle_collecting_listener(
    event: GroupMessageEvent,
    bot: Bot,
    config_svc: ConfigService = Inject(ConfigService),
    collection_svc: QuoteCollectionService = Inject(QuoteCollectionService),
    group_svc: GroupService = Inject(GroupService),
    review_svc: ReviewService = Inject(ReviewService),
    user_svc: UserService = Inject(UserService),
) -> None:
    """
    监听群组消息，处理自动语录收集。

    此事件不会向用户界面提供任何反馈。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param bot: Bot 实例
    :type bot: Bot
    :param config_svc: 配置服务（DI 注入）
    :type config_svc: ConfigService
    :param collection_svc: 语录收集服务（DI 注入）
    :type collection_svc: QuoteCollectionService
    :param group_svc: 群组服务（DI 注入）
    :type group_svc: GroupService
    :param review_svc: 评论服务（DI 注入）
    :type review_svc: ReviewService
    :param user_svc: 用户服务（DI 注入）
    :type user_svc: UserService
    """
    group_id = str(event.group_id)
    user_id = str(event.user_id)
    msg = event.get_plaintext().strip()

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
        collected = await collection_svc.collect_and_save(group_id)
        logger.info("筛选到 %d 条语录", len(collected))

    # 为每条语录添加 AI 评论
    for item in collected:
        if item.comment:
            async with silent_error_handler("添加 AI 评论"):
                await review_svc.add_review(
                    quote_id=item.quote_id,
                    author_id=AUTHOR_AI,
                    content=item.comment,
                )

    # 清空队列
    with suppress_error("清空队列"):
        await collection_svc.clear_queue(group_id)
