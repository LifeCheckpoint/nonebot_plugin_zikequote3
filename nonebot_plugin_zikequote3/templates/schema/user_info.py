"""
语录卡片模板
"""
from typing import List, Optional
from pydantic import BaseModel
from .. import render_template, read_resource_file


class UserInfoData(BaseModel):
    """用户信息数据类"""
    ranking_value: Optional[int] = None
    quote_count: int
    primary_nick: str
    primary_group_card: Optional[str] = None
    avatar: str
    history_nicks: List[str] = []
    history_group_cards: List[str] = []
    guide_text: str = ""


def render_user_info(
    ranking_value: Optional[int],
    quote_count: int,
    primary_nick: str,
    primary_group_card: Optional[str],
    avatar: str,
    history_nicks: Optional[List[str]] = None,
    history_group_cards: Optional[List[str]] = None,
) -> str:
    """
    渲染用户信息 HTML
    
    Args:
        ranking_value: 可选，用户当前群语录排名
        quote_count: 用户累计语录数
        primary_nick: 用户当前昵称
        primary_group_card: 用户当前群名片
        avatar: 头像 (可以为 Base64 或 URL)
        history_nicks: 曾用昵称列表
        history_group_cards: 曾用群名片列表
        guide_text: 引导文本
        
    Returns:
        渲染后的 HTML 字符串
    """
    inline_css = read_resource_file("css/user_info.css")
    guide_text = "输入 <span class=\"guide-key\">/语录列表</span> 查看更多语录"

    user_info_data = UserInfoData(
        ranking_value=ranking_value,
        quote_count=quote_count,
        primary_nick=primary_nick,
        primary_group_card=primary_group_card,
        avatar=avatar,
        history_nicks=history_nicks or [],
        history_group_cards=history_group_cards or [],
    )
    
    return render_template(
        "htmls/user_info.html.jinja2",
        inline_css=inline_css,
        ranking_value=user_info_data.ranking_value,
        quote_count=user_info_data.quote_count,
        primary_nick=user_info_data.primary_nick,
        primary_group_card=user_info_data.primary_group_card,
        avatar=user_info_data.avatar,
        history_nicks=user_info_data.history_nicks,
        history_group_cards=user_info_data.history_group_cards,
        guide_text=guide_text
    )


__all__ = [
    "UserInfoData",
    "render_user_info"
]