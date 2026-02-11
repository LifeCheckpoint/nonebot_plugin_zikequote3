"""
语录排行榜模板渲染方法。

提供语录排行榜的数据模型与 HTML 渲染方法。
"""
from typing import List, Optional
from pydantic import BaseModel
from .. import render_template, get_resource_path
import random, base64


class TemplateBasicRankingItemData(BaseModel):
    """
    排行榜项数据类。

    :param qq: QQ 号
    :type qq: str
    :param author: 作者名称
    :type author: str
    :param count: 语录数量
    :type count: int
    :param avatar: 头像 URI
    :type avatar: Optional[str]
    """

    qq: str
    author: str
    count: int
    avatar: Optional[str]

class TemplateLineChartData(BaseModel):
    """
    折线图数据类，参见 rank 模板。

    :param topN: 排名前 N 名
    :type topN: int
    :param dates: 日期列表
    :type dates: List[str]
    :param seriesData: 数据系列列表
    :type seriesData: List[List[int]]
    """

    topN: int
    dates: List[str]
    seriesData: List[List[int]]

class TemplateRankingStatsData(BaseModel):
    """
    统计数据类。

    :param total_quotes: 总语录数
    :type total_quotes: int
    :param pending_quotes: 待收集语录数
    :type pending_quotes: int
    :param contributors: 贡献者数量
    :type contributors: int
    :param average_quotes: 人均语录数
    :type average_quotes: float
    :param total_shows: 总展示次数
    :type total_shows: int
    """

    total_quotes: int
    pending_quotes: int
    contributors: int
    average_quotes: float
    total_shows: int

class TemplateRankingData(BaseModel):
    """
    语录排行榜渲染数据类。

    :param group_name: 群组名称
    :type group_name: str
    :param date_time: 时间字符串
    :type date_time: str
    :param basic_ranking: 基础排行数据
    :type basic_ranking: List[TemplateBasicRankingItemData]
    :param line_chart: 折线图数据
    :type line_chart: TemplateLineChartData
    :param stats: 统计信息
    :type stats: TemplateRankingStatsData
    """

    group_name: str
    date_time: str
    basic_ranking: List[TemplateBasicRankingItemData]
    line_chart: TemplateLineChartData
    stats: TemplateRankingStatsData


def render_rank(data: TemplateRankingData) -> str:
    """
    渲染语录排行榜 HTML。

    :param data: 语录排行榜渲染数据
    :type data: TemplateRankingData
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """

    def generate_random_color_svg_uri():
        hex_color = f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"
        svg_content = f'<svg width="1" height="1" viewBox="0 0 1 1" xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1" fill="{hex_color}"/></svg>'
        encoded_svg = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{encoded_svg}"
    
    echarts_js = get_resource_path("js/vendor/echarts.min.js")
    rank_css = get_resource_path("css/rank.css")
    rank_js = get_resource_path("js/rank.js")
    color_thief_js = get_resource_path("js/vendor/color-thief.min.js")

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
        echarts_js=str(echarts_js),
        rank_css=str(rank_css),
        rank_js=str(rank_js),
        color_thief_js=str(color_thief_js),

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
