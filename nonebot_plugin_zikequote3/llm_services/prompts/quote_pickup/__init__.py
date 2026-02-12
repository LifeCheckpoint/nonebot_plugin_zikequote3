"""
语录筛选提示词模板。

提供语录筛选场景下的 LLM 提示词渲染方法。
"""
from .. import render_template
from typing import List, Tuple


def quote_pickup(
    message_history: List[Tuple[str, str, str]],
    *,
    at_least_selections: int = 0,
    at_most_selections: int = 3,
) -> str:
    """
    语录筛选提示词模板渲染。

    :param message_history: 消息记录列表，格式为 ``(msg_id, user_name, content)``
    :type message_history: List[Tuple[str, str, str]]
    :param at_least_selections: 最少筛选条数，默认 ``0``
    :type at_least_selections: int
    :param at_most_selections: 最多筛选条数，默认 ``3``
    :type at_most_selections: int
    :returns: 渲染后的字符串
    :rtype: str
    """
    msg_dictlist = [
        {
            "msg_id": msg_id,
            "user_name": user_name,
            "content": content,
        }
        for msg_id, user_name, content in message_history
    ]
    return render_template(
        "quote_pickup/quote_pickup.jinja2",
        selection_least_num=at_least_selections,
        selection_most_num=at_most_selections,
        message_history=msg_dictlist,
    )
