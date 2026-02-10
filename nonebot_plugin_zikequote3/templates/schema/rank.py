"""
语录排行榜模板渲染方法
"""
from typing import List, Optional
from pydantic import BaseModel
from .. import render_template
from ...paths import PluginPath
import random, base64


class TemplateBasicRankingItemData(BaseModel):
    """排行榜项数据类"""

    """QQ号"""
    qq: str

    """作者名称"""
    author: str

    """语录数量"""
    count: int
    
    """头像URI"""
    avatar: Optional[str]

class TemplateLineChartData(BaseModel):
    """折线图数据类，参见 rank 模板"""

    """排名前 N 名"""
    topN: int

    """日期列表"""
    dates: List[str]

    """数据系列列表"""
    seriesData: List[List[int]]

class TemplateRankingStatsData(BaseModel):
    """统计数据类"""

    """总语录数"""
    total_quotes: int

    """待收集语录数"""
    pending_quotes: int

    """贡献者数量"""
    contributors: int

    """人均语录数"""
    average_quotes: float

    """总展示次数"""
    total_shows: int

class TemplateRankingData(BaseModel):
    """语录排行榜渲染数据类"""

    """群组名称"""
    group_name: str

    """时间字符串"""
    date_time: str

    """基础排行数据"""
    basic_ranking: List[TemplateBasicRankingItemData]

    """折线图数据"""
    line_chart: TemplateLineChartData

    """统计信息"""
    stats: TemplateRankingStatsData


def render_rank(data: TemplateRankingData) -> str:
    """
    渲染语录排行榜HTML
    
    Args:
        data: 语录排行榜渲染数据
        
    Returns:
        渲染后的 HTML 字符串
    """

    def generate_random_color_svg_uri():
        hex_color = f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"
        svg_content = f'<svg width="1" height="1" viewBox="0 0 1 1" xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1" fill="{hex_color}"/></svg>'
        encoded_svg = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{encoded_svg}"
    
    echarts_js = PluginPath.module_templates_js_root / "vendor" / "echarts.min.js"
    rank_css = PluginPath.module_templates_css_root / "rank.css"
    rank_js = PluginPath.module_templates_js_root / "rank.js"
    color_thief_js = PluginPath.module_templates_js_root / "vendor" / "color-thief.min.js"

    max_avatar_threshold = 10

    # 准备排行榜数据
    ranking_data = []
    for i, item in enumerate(data.basic_ranking):
        ranking_data.append({
            "rank": i + 1,
            "name": item.author,
            "score": item.count,
            "avatar": item.avatar or generate_random_color_svg_uri(),
        })
    
    
    stat_data_list = [
        {"value": data.stats.total_quotes, "label": "总语录数"},
        {"value": data.stats.pending_quotes, "label": "待收集语录"},
        {"value": data.stats.contributors, "label": "贡献者数量"},
        {"value": round(data.stats.average_quotes, 1), "label": "人均语录数"},
        {"value": data.stats.total_shows, "label": "总展示次数"},
    ]

    return render_template(
        "htmls/rank.html.jinja2",
        echarts_js=str(echarts_js.absolute()),
        rank_css=str(rank_css.absolute()),
        rank_js=str(rank_js.absolute()),
        color_thief_js=str(color_thief_js.absolute()),

        group_name=data.group_name,
        date_time=data.date_time,

        max_avatar_threshold=max_avatar_threshold,
        basic_ranking_data=ranking_data,
        line_chart_data=data.line_chart.model_dump(),
        stat_data=stat_data_list,
    )


__all__ = [
    "TemplateBasicRankingItemData",
    "TemplateRankingStatsData",
    "TemplateLineChartData",
    "TemplateRankingData",
    "render_rank",
]