from ...imports import *

def s_get_ranking_html(group_id: str, time: str, max_showcase_number: int) -> str:
    """
    获取语录排行 HTML
    """
    from ..quote_management.collection.queue_service import s_get_queue_length
    from ...templates import rank
    from ...templates.schema.rank import Stats, BasicRankingItem

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
                # 获取昵称，顺序获取防止失败
                name = db.dao.get_group_nickname_dao().get_current_group_nickname(author.qq_id, group_id)
                if name is None:
                    n = db.dao.get_user_nickname_dao().get_current_nickname(author.qq_id)
                    name = n.name if n else None
                if name is None:
                    name = author.qq_id
                
                # 获取计数
                num = db.dao.get_quote_dao().count_quotes_by_group_and_author(group_id, author.qq_id)
                if num == 0:
                    continue

                # 加入列表
                ranking_data.append(BasicRankingItem(
                    author=name,
                    count=num,
                    percentage=num / total_count,
                ))

    if len(ranking_data) == 0:
        raise ValueError("排行数据为空")
    
    ranking_data.sort(key=lambda x: x.count, reverse=True)
    ranking_data = ranking_data[:max_showcase_number]

    with service_exception("获取语录排行数据"):
        return rank.render_rank(
            group_name=group_name,
            date_time=time,
            stats=stats_data,
            basic_ranking=ranking_data,
        )
