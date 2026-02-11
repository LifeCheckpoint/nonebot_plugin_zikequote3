"""
用户信息模板。

提供用户信息的数据模型与 HTML 渲染方法。
"""
from typing import List, Optional
from pydantic import BaseModel
from ..registry import USER_INFO, render_with_spec


class TemplateUserInfoData(BaseModel):
    """
    用户信息数据类。

    :param ranking_value: 用户当前群语录排名
    :type ranking_value: Optional[int]
    :param quote_count: 用户累计语录数
    :type quote_count: int
    :param qq_id: 用户 QQ 号
    :type qq_id: str
    :param primary_nick: 用户当前昵称
    :type primary_nick: str
    :param primary_group_card: 用户当前群名片
    :type primary_group_card: Optional[str]
    :param avatar: 头像 URI
    :type avatar: str
    :param history_nicks: 曾用昵称列表
    :type history_nicks: List[str]
    :param history_group_cards: 曾用群名片列表
    :type history_group_cards: List[str]
    """

    ranking_value: Optional[int] = None
    quote_count: int
    qq_id: str
    primary_nick: str
    primary_group_card: Optional[str] = None
    avatar: str
    history_nicks: List[str] = []
    history_group_cards: List[str] = []


def render_user_info(data: TemplateUserInfoData) -> str:
    """
    渲染用户信息 HTML。

    :param data: 用户信息渲染数据
    :type data: TemplateUserInfoData
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """
    guide_command = "/语录列表"
    return render_with_spec(USER_INFO, guide_command=guide_command, **data.model_dump())


__all__ = [
    "TemplateUserInfoData",
    "render_user_info"
]