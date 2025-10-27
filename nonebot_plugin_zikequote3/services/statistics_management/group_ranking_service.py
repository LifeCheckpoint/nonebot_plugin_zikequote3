from ...imports import *

async def s_get_ranking_html(group_id: str, time: str, max_showcase_number: int) -> str:
    """
    获取语录排行 HTML
    """
    from ...services.user_management.user_service import s_get_user_current_display_name
    from ...services.user_management.avatar_service import s_get_user_avatar
    from ...templates import rank
    from ...templates.schema.rank import Stats, BasicRankingItem, LineChartData
    from ...utils.base64_encoder import to_data_uri
    from ..quote_management.collection.queue_service import s_get_queue_length
    from dateutil.relativedelta import relativedelta
    import datetime

    def generate_date_range_mm_dd(start_date: datetime.date, end_date: datetime.date) -> List[str]:
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date.strftime("%m-%d"))
            current_date += datetime.timedelta(days=1)
        return date_list

    with service_exception("获取语录统计数据"):
        stat_group = db.dao.get_quote_dao().get_quote_statistics_by_group(group_id)
        total_count = stat_group["total_quotes"]
        pending_count = s_get_queue_length(group_id)
        countributors = stat_group["unique_authors"]
        total_shows = stat_group["total_shows"]

    if total_count == 0:
        raise ValueError("当前群组语录数为 0")

    stats_data = Stats(
        total_quotes=total_count,
        pending_quotes=pending_count,
        contributors=countributors,
        average_quotes=0 if countributors == 0 else total_count / countributors,
        total_shows=total_shows
    )

    with service_exception("获取群组名称"):
        group = db.dao.get_group_dao().get_group_by_id(group_id)
        if group is None:
            raise ValueError(f"无法在数据库中找到群组 {group_id}")
        group_name = group.name

    with service_exception("获取个人排行"):
        ranking_data: List[BasicRankingItem] = []
        authors = db.dao.get_group_member_dao().get_members_by_group(group_id)
        
        for author in authors:
            with service_exception("处理单个用户排行数据", raise_again=False):
                name = s_get_user_current_display_name(author.qq_id, group_id)
                
                # 获取计数
                num = db.dao.get_quote_dao().count_quotes_by_group_and_author(group_id, author.qq_id)
                if num == 0:
                    continue

                # 获取头像
                usr = db.dao.get_user_dao().get_user_by_qq_id(author.qq_id)
                avatar_bytes = usr.avatar if usr else None
                # 如果没有头像，强制更新也
                if not avatar_bytes:
                    avatar_bytes = await s_get_user_avatar(author.qq_id)
                    if avatar_bytes:
                        db.dao.get_user_dao().update_user(author.qq_id, avatar_bytes)
                avatar_bs64 = to_data_uri(avatar_bytes) if avatar_bytes else None

                # 加入列表
                ranking_data.append(BasicRankingItem(
                    qq=author.qq_id,
                    author=name,
                    count=num,
                    avatar=avatar_bs64,
                ))

    if len(ranking_data) == 0:
        raise ValueError("排行数据为空")
    
    ranking_data.sort(key=lambda x: x.count, reverse=True)
    ranking_data = ranking_data[:max_showcase_number]

    # TODO: 改为配置项
    top_n = min(5, len(ranking_data))

    with service_exception("获取排行走势数据"):
        # 对于前 top_n 名，获取其全部语录，然后过滤日期到近一个月
        # TODO: 可调时间范围

        # example data:
        # {
        #     "topN": 2,
        #     "dates": ["10-1", "10-2", "10-3", "10-4"],
        #     "seriesData": [
        #         [995, 988, 1002, 1015],
        #         [945, 938, 952, 965],
        #     ]
        # }

        today_start = datetime.datetime.now()
        one_month_ago_start = (today_start - relativedelta(months=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        frontiers_series_data = []
        for i in range(top_n):
            item = ranking_data[i]
            all_quotes = db.dao.get_quote_dao().get_quotes_by_group_and_author(group_id, item.qq)

            # 从 timestamp_start 开始，每次累计一天，获取该用户截止该日的语录数
            daily_counts = []
            current_date = one_month_ago_start
            while current_date <= today_start:
                this_day_end = current_date + datetime.timedelta(days=1)
                count_until_date = sum(1 for q in all_quotes if q.time_stamp < this_day_end)
                daily_counts.append(count_until_date)
                current_date = this_day_end
            
            frontiers_series_data.append(daily_counts)
        
        line_chart_data = LineChartData(
            topN=top_n,
            dates=generate_date_range_mm_dd(
                one_month_ago_start.date(),
                today_start.date()
            ),
            seriesData=frontiers_series_data,
        )

    with service_exception("获取语录排行数据"):
        return rank.render_rank(
            group_name=group_name,
            date_time=time,
            basic_ranking=ranking_data,
            line_chart=line_chart_data,
            stats=stats_data,
        )
