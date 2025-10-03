from .. import render_template

def quote_pickup(message_history: str):
    """
    语录筛选提示词模板渲染

    Args:
        message_history: 消息历史

    Returns:
        渲染后的字符串
    """
    return render_template("quote_pickup/quote_pickup.jinja2", message_history=message_history)
