"""
语录统计相关模板渲染方法
"""
from .. import render_template


def quote_list_not_found(key: str) -> str:
    """
    语录列表未找到用户
    
    Args:
        key: 搜索关键词
        
    Returns:
        渲染后的消息
    """
    return render_template("quote_stastics/quote_list_not_found.jinja2", key=key)


def quote_list_ambiguous(key: str, num: int) -> str:
    """
    语录列表模糊匹配
    
    Args:
        key: 搜索关键词
        num: 匹配数量
        
    Returns:
        渲染后的消息
    """
    return render_template("quote_stastics/quote_list_ambiguous.jinja2", key=key, num=num)


__all__ = [
    'quote_list_not_found',
    'quote_list_ambiguous',
]