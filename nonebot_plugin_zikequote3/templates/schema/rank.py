"""
语录排行榜模板渲染方法
"""
from typing import List
from pydantic import BaseModel
from .. import render_template, read_resource_file


class RankingItem(BaseModel):
    """排行榜项数据类"""
    author: str
    count: int
    percentage: float


class Stats(BaseModel):
    """统计数据类"""
    total_quotes: int
    pending_quotes: int
    contributors: int
    average_quotes: float
    total_shows: int


def render_rank(
    group_name: str,
    time: str,
    stats: Stats,
    ranking: List[RankingItem],
    primary_color: str = "#667eea",
    secondary_color: str = "#764ba2"
) -> str:
    """
    渲染语录排行榜HTML
    
    Args:
        group_name: 群组名称
        time: 时间
        stats: 统计信息
        ranking: 排行榜详情列表
        primary_color: 主色调
        secondary_color: 副色调
        
    Returns:
        渲染后的 HTML 字符串
    """
    inline_css = read_resource_file("css/rank.css")
    
    # 准备统计数据
    stats_data = {
        'total_quotes': stats.total_quotes,
        'pending_quotes': stats.pending_quotes,
        'contributors': stats.contributors,
        'average_quotes': stats.average_quotes,
        'total_shows': stats.total_shows,
    }
    
    # 准备排行榜数据
    ranking_data = []
    for item in ranking:
        ranking_data.append({
            'author': item.author,
            'count': item.count,
            'percentage': item.percentage
        })
    
    return render_template(
        "htmls/rank.html.jinja2",
        inline_css=inline_css,
        group_name=group_name,
        time=time,
        stats=stats_data,
        ranking=ranking_data,
        primary_color=primary_color,
        secondary_color=secondary_color
    )


__all__ = [
    'RankingItem',
    'Stats',
    'render_rank',
]