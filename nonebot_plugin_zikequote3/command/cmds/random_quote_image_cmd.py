"""
随机语录图命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
使用 :class:`QueryResolver` 统一解析用户查询参数（@提及、昵称、关键词、语录ID）。
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot_plugin_alconna import Match
from nonebot_plugin_alconna.uniseg.segment import At

if TYPE_CHECKING:
    from ...database.models.quotes import Quote
    from ..parse_helper.query_resolver import ResolvedQuery

from ..command_definition import matcher_random_quote_image
from ..parse_helper.query_resolver import (
    QueryIntent,
    QueryResolver,
    STRATEGY_RANDOM_QUOTE,
    extract_at_qq,
    extract_text,
)
from ...di import Inject, inject
from ...services import QuoteReadService, QuoteWriteService, UserService
from ...database.image_store import ImageStore
from ._error_handlers import command_error_handler, suppress_error

logger = logging.getLogger(__name__)


@matcher_random_quote_image.handle()
@inject
async def handle_random_quote_image(
    event: GroupMessageEvent,
    bot: Bot,
    at_user: Match[At],
    text: Match[str],
    quote_read_svc: QuoteReadService = Inject(QuoteReadService),
    quote_write_svc: QuoteWriteService = Inject(QuoteWriteService),
    user_svc: UserService = Inject(UserService),
    image_store: ImageStore = Inject(ImageStore),
) -> None:
    """
    处理随机语录图命令。

    使用 :data:`STRATEGY_RANDOM_QUOTE` 策略通过 :class:`QueryResolver`
    统一解析 At、昵称、关键词、语录ID 等参数，随机获取一条含图片的语录，
    仅发送图片内容。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param bot: Bot 实例
    :type bot: Bot
    :param at_user: Alconna 匹配的 At 段参数
    :type at_user: Match[At]
    :param text: Alconna 匹配的文本参数（昵称、关键词或语录ID）
    :type text: Match[str]
    :param quote_read_svc: 语录读取服务（DI 注入）
    :type quote_read_svc: QuoteReadService
    :param quote_write_svc: 语录写入服务（DI 注入）
    :type quote_write_svc: QuoteWriteService
    :param user_svc: 用户服务（DI 注入）
    :type user_svc: UserService
    :param image_store: 图片存储（DI 注入）
    :type image_store: ImageStore
    """
    group_id = str(event.group_id)
    q_result = None

    async with command_error_handler(matcher_random_quote_image, "解析参数"):
        # 使用 QueryResolver 统一解析查询参数
        resolver = QueryResolver(user_svc)
        resolved = await resolver.resolve(
            strategy=STRATEGY_RANDOM_QUOTE,
            group_id=group_id,
            sender_id=str(event.user_id),
            at_target=extract_at_qq(at_user),
            raw_text=extract_text(text),
        )
        logger.debug(
            "随机语录图解析结果: intent=%s, resolved=%s",
            resolved.intent, resolved,
        )

    async with command_error_handler(matcher_random_quote_image, "获取语录图片"):
        # 根据解析结果构建候选池并随机选取（仅含图片的语录）
        q_result = await _pick_random_image_quote(
            resolved, group_id, quote_read_svc,
        )

        if q_result is None or q_result.image_content_uuid is None:
            await matcher_random_quote_image.finish(
                "没有找到符合条件的语录哦~",
            )

        # 发送语录图片
        img_path = image_store.get_path(q_result.image_content_uuid)
        image_data = img_path.read_bytes()
        await matcher_random_quote_image.send(MsgSeg.image(image_data))

    # 更新语录出现次数
    if q_result is not None:
        with suppress_error("更新语录出现次数"):
            await quote_read_svc.increment_show_time(q_result.quote_id)

        # 添加消息映射
        with suppress_error("添加消息映射"):
            await quote_write_svc.create_msg_quote_mapping(
                str(event.message_id), q_result.quote_id,
            )


async def _pick_random_image_quote(
    resolved: ResolvedQuery,
    group_id: str,
    quote_read_svc: QuoteReadService,
) -> Quote | None:
    """
    根据 :class:`ResolvedQuery` 解析结果构建候选语录池，过滤含图片的语录并随机选取。

    与 :func:`_pick_random_quote` 逻辑类似，但额外过滤
    ``image_content_uuid is not None`` 的语录。

    :param resolved: 统一查询解析结果
    :type resolved: ResolvedQuery
    :param group_id: 当前群组 ID
    :type group_id: str
    :param quote_read_svc: 语录读取服务
    :type quote_read_svc: QuoteReadService
    :returns: 随机选取的含图片语录，候选池为空时返回 ``None``
    :rtype: Quote | None
    """
    intent = resolved.intent

    # 按语录ID查询
    if intent == QueryIntent.QUOTE_BY_ID and resolved.quote_id:
        quote = await quote_read_svc.get_quote(resolved.quote_id)
        if (
            quote is not None
            and quote.group_id == group_id
            and quote.image_content_uuid is not None
        ):
            return quote
        return None

    # 按用户筛选（@提及 / QQ号 / 昵称匹配）
    if intent in (
        QueryIntent.USER_BY_AT,
        QueryIntent.USER_BY_QQ,
        QueryIntent.USER_BY_NAME,
    ):
        pool = []
        for uid in resolved.user_candidates:
            quotes = await quote_read_svc.get_quotes_by_group_and_author(
                group_id, uid,
            )
            pool.extend(q for q in quotes if q.image_content_uuid is not None)
        return random.choice(pool) if pool else None

    # 关键词搜索（含 merge_candidates 合并模式）
    if intent == QueryIntent.KEYWORD:
        pool = []
        seen_ids: set[str] = set()

        # merge_candidates 模式：添加匹配用户的语录
        for uid in resolved.user_candidates:
            quotes = await quote_read_svc.get_quotes_by_group_and_author(
                group_id, uid,
            )
            for q in quotes:
                if (
                    q.image_content_uuid is not None
                    and q.quote_id not in seen_ids
                ):
                    pool.append(q)
                    seen_ids.add(q.quote_id)

        # 添加关键词匹配的语录
        if resolved.has_keyword and resolved.keyword is not None:
            keyword_quotes = await quote_read_svc.search_quotes(
                resolved.keyword, group_id,
            )
            for q in keyword_quotes:
                if (
                    q.image_content_uuid is not None
                    and q.quote_id not in seen_ids
                ):
                    pool.append(q)
                    seen_ids.add(q.quote_id)
        elif not resolved.user_candidates:
            # 空关键词且无用户候选 = 全部含图片语录
            all_quotes = await quote_read_svc.get_quotes_by_group(group_id)
            pool.extend(
                q for q in all_quotes if q.image_content_uuid is not None
            )

        return random.choice(pool) if pool else None

    # SELF 或其他：无筛选，从全部含图片语录中随机选取
    all_quotes = list(
        await quote_read_svc.get_quotes_by_group(group_id),
    )
    image_pool = [q for q in all_quotes if q.image_content_uuid is not None]
    return random.choice(image_pool) if image_pool else None
