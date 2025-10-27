"""
语录排行榜模板渲染方法
"""
from typing import List, Optional
from pydantic import BaseModel
from .. import render_template
from ...imports import module_templates_root
import random, base64


class BasicRankingItem(BaseModel):
    """排行榜项数据类"""
    qq: str
    author: str
    count: int
    avatar: Optional[str]

class LineChartData(BaseModel):
    """折线图数据类，参见 rank 模板"""
    topN: int
    dates: List[str]
    seriesData: List[List[int]]

class Stats(BaseModel):
    """统计数据类"""
    total_quotes: int
    pending_quotes: int
    contributors: int
    average_quotes: float
    total_shows: int


def render_rank(
    group_name: str,
    date_time: str,
    basic_ranking: List[BasicRankingItem],
    line_chart: LineChartData,
    stats: Stats,
) -> str:
    """
    渲染语录排行榜HTML
    
    Args:
        group_name: 群组名称
        date_time: 时间字符串
        basic_ranking: 基础排行数据
        line_chart: 折线图数据
        stats: 统计信息
        
    Returns:
        渲染后的 HTML 字符串
    """

    def generate_random_color_svg_uri():
        hex_color = f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"
        svg_content = f'<svg width="1" height="1" viewBox="0 0 1 1" xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1" fill="{hex_color}"/></svg>'
        encoded_svg = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{encoded_svg}"
    
    echarts_js = module_templates_root / "src" / "assets" / "js" / "vendor" / "echarts.min.js"
    rank_css = module_templates_root / "src" / "assets" / "css" / "rank.css"
    rank_js = module_templates_root / "src" / "assets" / "js" / "rank.js"
    color_thief_js = module_templates_root / "src" / "assets" / "js" / "vendor" / "color-thief.min.js"

    max_avatar_threshold = 10

    # 准备排行榜数据
    ranking_data = []
    for i, item in enumerate(basic_ranking):
        ranking_data.append({
            "rank": i + 1,
            "name": item.author,
            "score": item.count,
            "avatar": item.avatar or generate_random_color_svg_uri(),
        })
    
    # 准备统计数据
    stats_data = [
        {"label": "总语录", "value": stats.total_quotes},
        {"label": "待收集语录", "value": stats.pending_quotes},
        {"label": "贡献者数", "value": stats.contributors},
        {"label": "人均语录数", "value": f"{stats.average_quotes:.2f}"},
        {"label": "总展示次数", "value": stats.total_shows},
    ]

    # 准备折线图数据
    line_chart_data = {
        "topN": line_chart.topN,
        "dates": line_chart.dates,
        "seriesData": line_chart.seriesData,
    }
    
    return render_template(
        "htmls/rank.html.jinja2",
        echarts_js=str(echarts_js.absolute()),
        rank_css=str(rank_css.absolute()),
        rank_js=str(rank_js.absolute()),
        color_thief_js=str(color_thief_js.absolute()),

        group_name=group_name,
        date_time=date_time,

        max_avatar_threshold=max_avatar_threshold,
        basic_ranking_data=ranking_data,
        line_chart_data=line_chart_data,
        stat_data=stats_data,
    )


__all__ = [
    'BasicRankingItem',
    'Stats',
    'render_rank',
]