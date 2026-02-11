"""
语录搜索命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
使用 :class:`QueryResolver` 统一解析 @提及 和 ``-qq`` 选项的用户筛选参数。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot_plugin_alconna import Match, Query
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_alconna.uniseg.segment import At
from pydantic import BaseModel

from ..command_definition import matcher_search_quote
from ..parse_helper.query_resolver import extract_at_qq
from ...di import Inject, inject
from ...services import ConfigService, StatisticsService, QuoteReadService, UserService
from ...services.html_render_service import HtmlRenderServiceBase
from ...database.image_store import ImageStore
from ._error_handlers import command_error_handler
from ...templates.registry import LISTING
from ...templates.schema.listing import TemplateQuoteListData, render_list
from ._display_helpers import transform_quotes_to_template_boxes

logger = logging.getLogger(__name__)


class _ArgsValidater(BaseModel):
    """
    搜索命令参数校验模型。

    :param qq: 用于筛选的 QQ 号，默认为 ``None``
    :type qq: Optional[int]
    :param search_with_image: 是否包含含图片的语录，默认为 ``True``
    :type search_with_image: bool
    :param max_result: 最大返回结果数量，默认为 ``None``（不限制）
    :type max_result: Optional[int]
    :param use_regex: 是否使用正则表达式搜索，默认为 ``False``
    :type use_regex: bool
    :param pattern: 搜索关键词或正则模式，默认为空字符串
    :type pattern: str
    """

    qq: Optional[int] = None
    search_with_image: bool = True
    max_result: Optional[int] = None
    use_regex: bool = False
    pattern: str = ""


@matcher_search_quote.handle()
@inject
async def handle_search_quote(
    event: GroupMessageEvent,
    at_user: Match[At],
    qq: Match[int],
    max_result: Match[int],
    keyword: Match[UniMessage],
    no_image: Query[bool] = Query("no_image.value", False),
    use_regex: Query[bool] = Query("use_regex.value", False),
    stats_svc: StatisticsService = Inject(StatisticsService),
    quote_read_svc: QuoteReadService = Inject(QuoteReadService),
    user_svc: UserService = Inject(UserService),
    image_store: ImageStore = Inject(ImageStore),
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
    config_svc: ConfigService = Inject(ConfigService),
) -> None:
    """
    处理语录搜索命令。

    支持关键词搜索、正则搜索、按 @提及 或 QQ 号筛选作者、排除图片等多种搜索模式，
    使用 :func:`extract_at_qq` 从 @提及 中提取 QQ 号，与 ``-qq`` 选项统一处理，
    渲染为列表图片发送。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param at_user: Alconna 匹配的 At 段参数，用于筛选语录作者
    :type at_user: Match[At]
    :param qq: Alconna 匹配的 QQ 号筛选参数（``-qq`` 选项）
    :type qq: Match[int]
    :param max_result: Alconna 匹配的最大返回结果数量参数
    :type max_result: Match[int]
    :param keyword: Alconna 匹配的搜索关键词参数
    :type keyword: Match[UniMessage]
    :param no_image: 是否排除含图片的语录
    :type no_image: Query[bool]
    :param use_regex: 是否使用正则表达式搜索
    :type use_regex: Query[bool]
    :param stats_svc: 统计服务（DI 注入）
    :type stats_svc: StatisticsService
    :param quote_read_svc: 语录读取服务（DI 注入）
    :type quote_read_svc: QuoteReadService
    :param user_svc: 用户服务（DI 注入）
    :type user_svc: UserService
    :param image_store: 图片存储（DI 注入）
    :type image_store: ImageStore
    :param html_render_svc: HTML 渲染服务（DI 注入）
    :type html_render_svc: HtmlRenderServiceBase
    :param config_svc: 配置服务（DI 注入）
    :type config_svc: ConfigService
    """
    group_id = str(event.group_id)

    async with command_error_handler(matcher_search_quote, "解析参数"):
        if max_result.available:
            if max_result.result is not None and max_result.result < 1:
                await matcher_search_quote.finish(
                    "最大返回结果数量至少为 1 哦~"
                )

        # 统一 @提及 和 -qq 选项：@提及 优先于 -qq
        at_qq = extract_at_qq(at_user)
        resolved_qq: int | None = None
        if at_qq is not None:
            resolved_qq = int(at_qq)
        elif qq.available and qq.result is not None:
            resolved_qq = qq.result

        params = _ArgsValidater(
            qq=resolved_qq,
            search_with_image=(
                (not no_image.result) if no_image.available else True
            ),
            max_result=(
                max_result.result if max_result.available else None
            ),
            use_regex=(
                use_regex.result if use_regex.available else False
            ),
            pattern=(
                keyword.result.extract_plain_text()
                if keyword.available else ""
            ),
        )
        logger.debug("解析结果参数: %s", params)

    async with command_error_handler(matcher_search_quote, "获取语录列表"):
        # 使用 StatisticsService 搜索语录
        quotes, total_found = await stats_svc.search_quotes(
            keyword=params.pattern,
            group_id=group_id,
            author_id=(
                str(params.qq) if params.qq else None
            ),
            include_image_only=params.search_with_image,
            max_results=params.max_result,
            use_regex=params.use_regex,
        )

        # 获取群组配置中的语录内容最大显示长度
        cfg = await config_svc.get_parsed_config(group_id)
        max_content_length = cfg.showcase.quote_content_max_length

        # 转换为模板数据
        quote_boxes = await transform_quotes_to_template_boxes(
            quotes, group_id,
            quote_read_svc=quote_read_svc,
            user_svc=user_svc,
            image_store=image_store,
            show_author=True,
            max_content_length=max_content_length,
        )

        # 拼接说明文字
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title_text = f"有关{params.pattern}的语录搜索结果"
        desc_text = " | ".join([
            f"{time_str}",
            f"{'正则' if params.use_regex else '普通'}搜索模式",
            (
                f"筛选 QQ: {params.qq}"
                if params.qq else "不筛选 QQ"
            ),
            f"{'' if params.search_with_image else '不'} 包含图片",
            f"共 {total_found} 条 (显示 {len(quote_boxes)} 条)",
        ])

        # 尝试获取一言
        hitokoto_text = None
        try:
            from ...utils.hitokoto import get_hitokoto
            content, author = get_hitokoto()
            if content and author:
                hitokoto_text = f"「{content}」 ——{author}"
            elif content:
                hitokoto_text = f"「{content}」"
        except Exception:
            logger.debug("获取一言失败", exc_info=True)

        # 渲染 HTML 并截图
        html = render_list(TemplateQuoteListData(
            title=title_text,
            desc=desc_text,
            addition=hitokoto_text,
            quotes=quote_boxes,
        ))
        img = await html_render_svc.render(html, width=LISTING.width, height=LISTING.height)
        await matcher_search_quote.finish(MsgSeg.image(img))
