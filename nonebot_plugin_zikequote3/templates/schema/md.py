"""
Markdown 模板。

提供 Markdown 内容的 HTML 渲染方法。
"""

import markdown

from ..registry import MD, render_with_spec

def render_markdown(content: str) -> str:
    """
    渲染 Markdown HTML。

    :param content: 要渲染的 Markdown 内容
    :type content: str
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """
    html_content = markdown.markdown(
        content,
        extensions=["tables", "fenced_code", "toc", "nl2br"],
    )

    return render_with_spec(MD, content=html_content)


__all__ = [
    'render_markdown',
]