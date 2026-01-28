"""
语录卡片模板
"""
from typing import List, Optional
from pydantic import BaseModel
from .. import render_template, read_resource_file


class TemplateUserInfoData(BaseModel):
    """用户信息数据类"""

    """用户当前群语录排名"""
    ranking_value: Optional[int] = None

    """用户累计语录数"""
    quote_count: int

    """用户 QQ 号"""
    qq_id: str

    """用户当前昵称"""
    primary_nick: str

    """用户当前群名片"""
    primary_group_card: Optional[str] = None

    """头像 URI"""
    avatar: str

    """曾用昵称列表"""
    history_nicks: List[str] = []

    """曾用群名片列表"""
    history_group_cards: List[str] = []


def render_user_info(data: TemplateUserInfoData) -> str:
    """
    渲染用户信息 HTML
    
    Args:
        data: 用户信息渲染数据
        
    Returns:
        渲染后的 HTML 字符串
    """
    inline_css = read_resource_file("css/user_info.css")
    guide_text = "输入 <span class=\"guide-key\">/语录列表</span> 查看更多语录"

    return render_template(
        "htmls/user_info.html.jinja2",
        inline_css=inline_css,
        guide_text=guide_text,
        **data.model_dump(),
    )


__all__ = [
    "TemplateUserInfoData",
    "render_user_info"
]