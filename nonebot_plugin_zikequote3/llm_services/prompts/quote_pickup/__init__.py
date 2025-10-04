from ....imports import cfg
from .. import render_template
from typing import List, Tuple

def quote_pickup(group_id: int, message_history: List[Tuple[str, str, str]]):
    """
    语录筛选提示词模板渲染

    Args:
        group_id (int): 群号
        message_history (List[Tuple[str, str, str]]): 消息记录列表，格式为 (user_id, user_name, content)

    Returns:
        渲染后的字符串
    """
    msg_dictlist = [
        {
            "user_id": user_id,
            "user_name": user_name,
            "content": content
        }
        for user_id, user_name, content in message_history
    ]
    return render_template(
        "quote_pickup/quote_pickup.jinja2",
        selection_least_num=cfg[group_id].collecting.at_least_selections,
        selection_most_num=cfg[group_id].collecting.at_most_selections,
        message_history=msg_dictlist,
    )
