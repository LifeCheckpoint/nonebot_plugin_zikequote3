"""
语录排行榜命令处理器（dishka DI 版本）。

替代旧的 get_ranking_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。
"""

from __future__ import annotations

import datetime
import logging
from typing import List

from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot.adapters import Message
from nonebot.params import CommandArg

from ..command_definition_new import matcher_get_ranking, default_cfg
from ...di import get_container
from ...services.new import (
    GroupService,
    QuoteReadService,
    StatisticsService,
    UserService,
)
from ...utils.error_report import event_exception_failmsg_a
from ...utils.base64_encoder import to_data_uri
from ...templates.schema.rank import (
    TemplateBasicRankingItemData,
    TemplateLineChartData,
    TemplateRankingData,
    TemplateRankingStatsData,
    render_rank,
)
from ...html_capture import html_img_render

logger = logging.getLogger(__name__)


def _generate_date_range_mm_dd(
    start_date: datetime.date, end_date: datetime.date,
) -> List[str]:
    """生成 MM-DD 格式的日期范围列表。"""
    date_list: List[str] = []
    current = start_date
    while current <= end_date:
        date_list.append(current.strftime("%m-%d"))
        current += datetime.timedelta(days=1)
    return date_list


@matcher_get_ranking.handle()
async def handle_get_ranking(
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
) -> None:
    """展示群内语录排行图片。"""
    group_id = str(event.group_id)

    # 解析参数，获取展示数量
    key = arg.extract_plain_text().strip()
    max_rank = default_cfg.showcase.max_rank_user_num
    if key and key.isnumeric() and int(key) > 0:
        max_showcase_number = min(int(key), max(1, max_rank))
    else:
        max_showcase_number = max_rank

    container = get_container()
    async with container() as request_scope:
        stats_svc = await request_scope.get(StatisticsService)
        user_svc = await request_scope.get(UserService)
        group_svc = await request_scope.get(GroupService)
        quote_read_svc = await request_scope.get(QuoteReadService)

        async with event_exception_failmsg_a(matcher_get_ranking, "获取语录排行"):
            # 获取统计数据
            stat = await stats_svc.get_group_statistics(group_id)
            total_count = stat["total_quotes"]
            contributors = stat["unique_authors"]
            total_shows = stat["total_shows"]

            if total_count == 0:
                raise ValueError("当前群组语录数为 0")

            # pending_count 暂时设为 0（旧版依赖 queue_service）
            pending_count = 0

            stats_data = TemplateRankingStatsData(
                total_quotes=total_count,
                pending_quotes=pending_count,
                contributors=contributors,
                average_quotes=(
                    0.0 if contributors == 0
                    else total_count / contributors
                ),
                total_shows=total_shows,
            )

            # 获取群组名称
            group_info = await group_svc.get_group(group_id)
            if group_info is None:
                raise ValueError(f"无法在数据库中找到群组 {group_id}")
            group_name = group_info.name

            # 获取个人排行
            member_counts = await stats_svc.get_group_member_quote_counts(
                group_id,
            )
            ranking_data: List[TemplateBasicRankingItemData] = []
            for item in member_counts:
                qq_id = item["qq_id"]
                count = item["quote_count"]
                name = await user_svc.get_display_name(qq_id, group_id)

                # 获取头像
                avatar_bytes = await user_svc.get_avatar(qq_id)
                avatar_uri = to_data_uri(avatar_bytes) if avatar_bytes else None

                ranking_data.append(TemplateBasicRankingItemData(
                    qq=qq_id,
                    author=name,
                    count=count,
                    avatar=avatar_uri,
                ))

            if not ranking_data:
                raise ValueError("排行数据为空")

            ranking_data.sort(key=lambda x: x.count, reverse=True)
            ranking_data = ranking_data[:max_showcase_number]

            # 折线图数据（近 15 天走势）
            top_n = min(5, len(ranking_data))
            today_start = datetime.datetime.now()
            fifteen_days_ago = (
                today_start - datetime.timedelta(days=15)
            ).replace(hour=0, minute=0, second=0, microsecond=0)

            frontiers_series: List[List[int]] = []
            for i in range(top_n):
                qq_id = ranking_data[i].qq
                all_quotes = list(
                    await quote_read_svc.get_quotes_by_group_and_author(
                        group_id, qq_id,
                    )
                )
                daily_counts: List[int] = []
                current_date = fifteen_days_ago
                while current_date <= today_start:
                    next_day = current_date + datetime.timedelta(days=1)
                    cnt = sum(
                        1 for q in all_quotes if q.time_stamp < next_day
                    )
                    daily_counts.append(cnt)
                    current_date = next_day
                frontiers_series.append(daily_counts)

            line_chart_data = TemplateLineChartData(
                topN=top_n,
                dates=_generate_date_range_mm_dd(
                    fifteen_days_ago.date(), today_start.date(),
                ),
                seriesData=frontiers_series,
            )

            # 渲染 HTML 并截图
            time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            html = render_rank(TemplateRankingData(
                group_name=group_name,
                date_time=time_str,
                basic_ranking=ranking_data,
                line_chart=line_chart_data,
                stats=stats_data,
            ))
            img = await html_img_render(
                html, width=1920, height=1080, wait=3000,
            )
            await matcher_get_ranking.finish(MsgSeg.image(img))
