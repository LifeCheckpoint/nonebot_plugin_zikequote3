"""
语录搜索命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
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
from pydantic import BaseModel

from ..command_definition import matcher_search_quote
from ...di import Inject, inject
from ...services import StatisticsService, QuoteReadService, UserService
from ...services.html_render_service import HtmlRenderServiceBase
from ...database.image_store import ImageStore
from ._error_handlers import command_error_handler
from ...templates.schema.listing import TemplateQuoteListData, render_list
from ._display_helpers import transform_quotes_to_template_boxes

logger = logging.getLogger(__name__)


class _ArgsValidater(BaseModel):
    qq: Optional[int] = None
    search_with_image: bool = True
    max_result: Optional[int] = None
    use_regex: bool = False
    pattern: str = ""


@matcher_search_quote.handle()
@inject
async def handle_search_quote(
    event: GroupMessageEvent,
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
) -> None:
    """语录搜索。"""
    group_id = str(event.group_id)

    async with command_error_handler(matcher_search_quote, "解析参数"):
        if max_result.available:
            if max_result.result is not None and max_result.result < 1:
                await matcher_search_quote.finish(
                    "最大返回结果数量至少为 1 哦~"
                )

        params = _ArgsValidater(
            qq=qq.result if qq.available else None,
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

        # 转换为模板数据
        quote_boxes = await transform_quotes_to_template_boxes(
            quotes, group_id,
            quote_read_svc=quote_read_svc,
            user_svc=user_svc,
            image_store=image_store,
            show_author=True,
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
        img = await html_render_svc.render(html, width=1520, height=200)
        await matcher_search_quote.finish(MsgSeg.image(img))
