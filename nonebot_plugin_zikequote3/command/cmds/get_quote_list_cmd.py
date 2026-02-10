"""
语录列表命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
"""

from __future__ import annotations

import logging
from datetime import datetime

from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot_plugin_alconna import Match
from nonebot_plugin_alconna.uniseg.segment import At

from ..command_definition import matcher_get_quote_list
from ..parse_helper.datatype_parse import parse_page_range
from ...di import Inject, inject
from ...services import QuoteReadService, StatisticsService, UserService
from ...services.html_render_service import HtmlRenderServiceBase
from ...database.image_store import ImageStore
from ._error_handlers import command_error_handler
from ...templates.schema.listing import TemplateQuoteListData, render_list
from ._display_helpers import transform_quotes_to_template_boxes

logger = logging.getLogger(__name__)


@matcher_get_quote_list.handle()
@inject
async def handle_get_quote_list(
    event: GroupMessageEvent,
    range: Match[str],
    at_user: Match[At],
    qq: Match[str],
    nickname: Match[str],
    stats_svc: StatisticsService = Inject(StatisticsService),
    user_svc: UserService = Inject(UserService),
    quote_read_svc: QuoteReadService = Inject(QuoteReadService),
    image_store: ImageStore = Inject(ImageStore),
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
) -> None:
    """语录列表。"""
    group_id = str(event.group_id)

    async with command_error_handler(matcher_get_quote_list, "解析参数"):
        user_qq: str | None = None

        # 优先解析 At 段
        if at_user.available:
            if at_user.result and at_user.result.origin:
                user_qq = at_user.result.origin.data.get("qq")

        # 其次解析 QQ 号
        if not user_qq and qq.available:
            if qq.result and qq.result.isdigit():
                user_qq = qq.result

        # 其次解析手动输入昵称
        if not user_qq and nickname.available:
            if nickname.result:
                probable_users = await user_svc.search_users_by_name(
                    nickname.result, group_id, exact=False,
                )
                if len(probable_users) > 1:
                    await matcher_get_quote_list.finish(
                        "找到多个用户，请考虑使用 @ 或 QQ 号进行查询哦~"
                    )
                elif len(probable_users) < 1:
                    await matcher_get_quote_list.finish(
                        "没有找到符合条件的用户哦~"
                    )
                else:
                    user_qq = probable_users[0]

        # 最后使用发送者
        if not user_qq:
            user_qq = str(event.user_id)

        logger.debug("解析结果用户: %s", user_qq)

        # 解析范围参数
        page_from, page_to = parse_page_range(
            range.result if range.available else "",
        )

    async with command_error_handler(matcher_get_quote_list, "获取语录列表"):
        # 检查用户是否存在
        if not user_qq or not await user_svc.user_exists(user_qq):
            raise ValueError("没有找到有效的用户哦.·´¯`(>▂<)´¯`·. ")

        # 获取个人语录列表（分页）
        quotes, total_count, real_from, real_to = (
            await stats_svc.get_personal_quotes(
                qq_id=user_qq,
                group_id=group_id,
                from_index=page_from,
                to_index=page_to,
            )
        )

        # 获取用户显示名称
        current_card = await user_svc.get_display_name(user_qq, group_id)

        # 转换为模板数据
        quote_boxes = await transform_quotes_to_template_boxes(
            quotes, group_id,
            quote_read_svc=quote_read_svc,
            user_svc=user_svc,
            image_store=image_store,
        )

        # 拼接说明文字
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title_text = f"{current_card}的语录列表"
        desc_text = (
            f"{time_str} / {total_count} 条语录 "
            f"(第 {real_from + 1} - {real_to + 1} 条)"
        )

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
        await matcher_get_quote_list.finish(MsgSeg.image(img))
