"""
随机语录命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
使用 :class:`QueryResolver` 统一解析用户查询参数（@提及、昵称、关键词、语录ID）。
"""

from __future__ import annotations

import asyncio
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

from ..command_definition import matcher_random_quote
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
from ...msgtexts.quote_read import send_quote

logger = logging.getLogger(__name__)


@matcher_random_quote.handle()
@inject
async def handle_random_quote(
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
    处理随机语录命令。

    使用 :data:`STRATEGY_RANDOM_QUOTE` 策略通过 :class:`QueryResolver`
    统一解析 At、昵称、关键词、语录ID 等参数，随机获取一条语录，
    以纯文本（含可选图片）形式发送。

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
    send_msg = None

    async with command_error_handler(matcher_random_quote, "解析参数"):
        # 使用 QueryResolver 统一解析查询参数
        resolver = QueryResolver(user_svc)
        resolved = await resolver.resolve(
            strategy=STRATEGY_RANDOM_QUOTE,
            group_id=group_id,
            sender_id=str(event.user_id),
            at_target=extract_at_qq(at_user),
            raw_text=extract_text(text),
        )
        logger.debug("随机语录解析结果: intent=%s, resolved=%s", resolved.intent, resolved)

    async with command_error_handler(matcher_random_quote, "获取随机语录"):
        # 根据解析结果构建候选池并随机选取
        q_result = await _pick_random_quote(resolved, group_id, quote_read_svc)

        if q_result is None:
            await matcher_random_quote.finish("没有找到符合条件的语录哦~")

        # 异步更新用户信息缓存
        async def _sync_user_info() -> None:
            try:
                member_info = await bot.get_group_member_info(
                    group_id=int(group_id), user_id=int(q_result.author_id),
                )
                nickname = member_info.get("nickname", "")
                card = member_info.get("card", "")
                if nickname:
                    await user_svc.sync_nickname(q_result.author_id, nickname)
                if card:
                    await user_svc.sync_group_card(q_result.author_id, group_id, card)
            except Exception:
                logger.debug("同步用户信息失败", exc_info=True)

        asyncio.create_task(_sync_user_info())

        # 获取语录作者当前昵称
        author_card = await user_svc.get_display_name(q_result.author_id, group_id)

        with suppress_error("发送语录消息"):
            if q_result.content is not None:
                text_msg = MsgSeg.text(send_quote(author_card, q_result.content))
            else:
                text_msg = None

            if q_result.image_content_uuid is None and text_msg is not None:
                send_msg = await matcher_random_quote.send(text_msg)
            elif q_result.image_content_uuid is not None and text_msg is not None:
                try:
                    img_path = image_store.get_path(q_result.image_content_uuid)
                    image_data = img_path.read_bytes()
                    full_msg = text_msg + MsgSeg.image(image_data)
                except FileNotFoundError:
                    full_msg = text_msg + MsgSeg.text("\n（语录图片文件已丢失 O.O）")
                send_msg = await matcher_random_quote.send(full_msg)
            elif q_result.image_content_uuid is not None and text_msg is None:
                try:
                    img_path = image_store.get_path(q_result.image_content_uuid)
                    image_data = img_path.read_bytes()
                    send_msg = await matcher_random_quote.send(MsgSeg.image(image_data))
                except FileNotFoundError:
                    send_msg = await matcher_random_quote.send("（语录图片文件已丢失 O.O）")
            else:
                raise ValueError("语录内容和图片均为空")

    # 更新语录出现次数
    with suppress_error("更新语录出现次数"):
        await quote_read_svc.increment_show_time(q_result.quote_id)

    # 添加消息映射
    if send_msg is not None:
        with suppress_error("添加消息映射"):
            await quote_write_svc.create_msg_quote_mapping(
                str(send_msg["message_id"]), q_result.quote_id,
            )


async def _pick_random_quote(
    resolved: ResolvedQuery,
    group_id: str,
    quote_read_svc: QuoteReadService,
) -> Quote | None:
    """
    根据 :class:`ResolvedQuery` 解析结果构建候选语录池并随机选取一条。

    支持按语录ID、按用户、按关键词（含 merge_candidates 合并模式）
    以及无筛选等多种查询意图。

    :param resolved: 统一查询解析结果
    :type resolved: ResolvedQuery
    :param group_id: 当前群组 ID
    :type group_id: str
    :param quote_read_svc: 语录读取服务
    :type quote_read_svc: QuoteReadService
    :returns: 随机选取的语录，候选池为空时返回 ``None``
    :rtype: Quote | None
    """
    intent = resolved.intent

    # 按语录ID查询
    if intent == QueryIntent.QUOTE_BY_ID and resolved.quote_id:
        quote = await quote_read_svc.get_quote(resolved.quote_id)
        if quote is not None and quote.group_id == group_id:
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
            pool.extend(quotes)
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
                if q.quote_id not in seen_ids:
                    pool.append(q)
                    seen_ids.add(q.quote_id)

        # 添加关键词匹配的语录
        if resolved.has_keyword and resolved.keyword is not None:
            keyword_quotes = await quote_read_svc.search_quotes(
                resolved.keyword, group_id,
            )
            for q in keyword_quotes:
                if q.quote_id not in seen_ids:
                    pool.append(q)
                    seen_ids.add(q.quote_id)
        elif not resolved.user_candidates:
            # 空关键词且无用户候选 = 全部语录
            all_quotes = await quote_read_svc.get_quotes_by_group(group_id)
            pool.extend(all_quotes)

        return random.choice(pool) if pool else None

    # SELF 或其他：无筛选，返回全部语录中随机一条
    return await quote_read_svc.get_random_quote(group_id)
