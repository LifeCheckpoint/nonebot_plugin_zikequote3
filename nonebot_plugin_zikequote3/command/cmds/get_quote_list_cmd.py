"""
语录列表命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
使用 :class:`QueryResolver` 统一解析用户查询参数。
"""

from __future__ import annotations

from nonebot import logger
from datetime import datetime

from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot_plugin_alconna import Match
from nonebot_plugin_alconna.uniseg.segment import At

from ..command_definition import matcher_get_quote_list
from ..parse_helper.datatype_parse import parse_page_range
from ..parse_helper.query_resolver import (
    QueryResolver,
    STRATEGY_USER_LOOKUP,
    extract_at_qq,
    extract_text,
)
from ...di import Inject, inject
from ...services import ConfigService, QuoteReadService, StatisticsService, UserService
from ...services.html_render_service import HtmlRenderServiceBase
from ...database.image_store import ImageStore
from ._error_handlers import command_error_handler
from ...templates.registry import LISTING
from ...templates.schema.listing import TemplateQuoteListData, render_list
from ._display_helpers import transform_quotes_to_template_boxes

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
    config_svc: ConfigService = Inject(ConfigService),
) -> None:
    """
    处理语录列表命令。

    使用 :data:`STRATEGY_USER_LOOKUP` 策略通过 :class:`QueryResolver`
    统一解析 At、QQ 号、昵称等用户查询参数，支持分页，渲染为图片发送。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param range: Alconna 匹配的页码范围参数
    :type range: Match[str]
    :param at_user: Alconna 匹配的 At 段参数
    :type at_user: Match[At]
    :param qq: Alconna 匹配的 QQ 号参数
    :type qq: Match[str]
    :param nickname: Alconna 匹配的昵称参数
    :type nickname: Match[str]
    :param stats_svc: 统计服务（DI 注入）
    :type stats_svc: StatisticsService
    :param user_svc: 用户服务（DI 注入）
    :type user_svc: UserService
    :param quote_read_svc: 语录读取服务（DI 注入）
    :type quote_read_svc: QuoteReadService
    :param image_store: 图片存储（DI 注入）
    :type image_store: ImageStore
    :param html_render_svc: HTML 渲染服务（DI 注入）
    :type html_render_svc: HtmlRenderServiceBase
    :param config_svc: 配置服务（DI 注入）
    :type config_svc: ConfigService
    """
    group_id = str(event.group_id)

    async with command_error_handler(matcher_get_quote_list, "解析参数"):
        # 使用 QueryResolver 统一解析用户查询
        resolver = QueryResolver(user_svc)
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id=group_id,
            sender_id=str(event.user_id),
            at_target=extract_at_qq(at_user),
            raw_text=extract_text(qq, nickname),
        )

        # 处理多用户歧义和无匹配情况
        if not result.single_user:
            if len(result.user_candidates) > 1:
                await matcher_get_quote_list.finish(
                    "找到多个用户，请考虑使用 @ 或 QQ 号进行查询哦~"
                )
            else:
                await matcher_get_quote_list.finish(
                    "没有找到符合条件的用户哦~"
                )

        user_qq = result.single_user
        logger.debug("解析结果用户: {}", user_qq)

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

        # 获取群组配置中的语录内容最大显示长度
        cfg = await config_svc.get_parsed_config(group_id)
        max_content_length = cfg.showcase.quote_content_max_length

        # 转换为模板数据
        quote_boxes = await transform_quotes_to_template_boxes(
            quotes, group_id,
            quote_read_svc=quote_read_svc,
            user_svc=user_svc,
            image_store=image_store,
            max_content_length=max_content_length,
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
        img = await html_render_svc.render(html, width=LISTING.width, height=LISTING.height)
        await matcher_get_quote_list.finish(MsgSeg.image(img))
