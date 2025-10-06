"""
语录卡片模板
"""
from typing import List, Optional
from pydantic import BaseModel
from .. import render_template, read_resource_file


class Comment(BaseModel):
    """评论数据类"""
    content: str
    author_name: Optional[str] = None
    comment_id: Optional[str] = None


def render_card(
    quote_id: str,
    quote: str,
    image_uri: Optional[str],
    author_name: str,
    comments: Optional[List[Comment]] = None,
    primary_color: str = "#667eea",
    secondary_color: str = "#764ba2"
) -> str:
    """
    渲染语录卡片HTML
    
    Args:
        quote_id: 语录ID
        quote: 语录内容
        image_uri: 语录图片URI
        author_name: 作者姓名
        comments: 评论列表
        primary_color: 主色调
        secondary_color: 副色调
        
    Returns:
        渲染后的 HTML 字符串
    """
    inline_css = read_resource_file("css/card.css")
    
    # 准备评论数据
    comments_data = []
    if comments:
        for comment in comments:
            comments_data.append({
                'content': comment.content,
                'author_name': comment.author_name,
                'comment_id': comment.comment_id
            })
    
    return render_template(
        "htmls/card.html.jinja2",
        inline_css=inline_css,
        quote_id=quote_id,
        quote=quote,
        image=image_uri,
        author_name=author_name,
        comments=comments_data,
        primary_color=primary_color,
        secondary_color=secondary_color
    )


__all__ = [
    'Comment',
    'render_card',
]