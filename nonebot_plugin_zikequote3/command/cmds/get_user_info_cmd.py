"""
用户信息卡片命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot_plugin_alconna import Match
from nonebot_plugin_alconna.uniseg.segment import At

from ..command_definition import matcher_get_user_info
from ...di import Inject, inject
from ...services import StatisticsService, UserService
from ...services.html_render_service import HtmlRenderServiceBase
from ._error_handlers import command_error_handler
from ...utils.base64_encoder import to_data_uri
from ...templates.schema.user_info import TemplateUserInfoData, render_user_info

logger = logging.getLogger(__name__)


@matcher_get_user_info.handle()
@inject
async def handle_get_user_info(
    event: GroupMessageEvent,
    at_user: Match[At],
    qq: Match[str],
    nickname: Match[str],
    user_svc: UserService = Inject(UserService),
    stats_svc: StatisticsService = Inject(StatisticsService),
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
) -> None:
    """获取用户信息卡片。"""
    group_id = str(event.group_id)

    async with command_error_handler(matcher_get_user_info, "解析参数"):
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
                    await matcher_get_user_info.finish(
                        "找到多个用户，请考虑使用 @ 或 QQ 号进行查询哦~"
                    )
                elif len(probable_users) < 1:
                    await matcher_get_user_info.finish(
                        "没有找到符合条件的用户哦~"
                    )
                else:
                    user_qq = probable_users[0]

        # 最后使用发送者
        if not user_qq:
            user_qq = str(event.user_id)

    async with command_error_handler(matcher_get_user_info, "获取用户信息"):
        # 检查用户是否存在
        if not user_qq or not await user_svc.user_exists(user_qq):
            raise ValueError("没有找到有效的用户哦.·´¯`(>▂<)´¯`·. ")

        # 获取显示名称
        display_name = await user_svc.get_display_name(user_qq, group_id)

        # 获取当前昵称（非群名片）
        current_nick = await user_svc.get_current_nickname(user_qq)
        if not current_nick:
            current_nick = display_name

        # 获取当前群名片
        current_card = await user_svc.get_current_group_card(
            user_qq, group_id,
        )

        # 获取头像
        avatar_bytes = await user_svc.get_avatar(user_qq)
        avatar_uri = to_data_uri(avatar_bytes) if avatar_bytes else ""

        # 获取语录数
        quote_count = await stats_svc.count_author_quotes_in_group(
            group_id, user_qq,
        )

        # 计算排名
        member_counts = await stats_svc.get_group_member_quote_counts(
            group_id,
        )
        ranking_value = None
        for idx, item in enumerate(member_counts):
            if item["qq_id"] == user_qq:
                ranking_value = idx + 1
                break

        # 获取历史昵称和群名片
        def _filter_name(
            name: str | None,
        ) -> bool:
            return (
                name is not None
                and name != current_nick
                and name != current_card
                and name.strip() != ""
            )

        all_nicks = await user_svc.get_all_nicknames(user_qq)
        history_nicks = [
            n.name for n in all_nicks if _filter_name(n.name)
        ]

        all_cards = await user_svc.get_all_group_nicknames(
            user_qq, group_id,
        )
        history_cards = [
            n.name for n in all_cards if _filter_name(n.name)
        ]

        # 渲染 HTML 并截图
        html = render_user_info(TemplateUserInfoData(
            ranking_value=ranking_value,
            quote_count=quote_count,
            qq_id=user_qq,
            primary_nick=current_nick,
            primary_group_card=current_card,
            avatar=avatar_uri,
            history_nicks=history_nicks,
            history_group_cards=history_cards,
        ))
        img = await html_render_svc.render(html, width=450, height=100)
        await matcher_get_user_info.finish(MsgSeg.image(img))
