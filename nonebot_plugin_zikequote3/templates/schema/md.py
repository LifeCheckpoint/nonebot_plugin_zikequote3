"""
Markdown 模板。

提供 Markdown 内容的 HTML 渲染方法。
"""

import markdown

from .. import render_template, read_resource_file

def render_markdown(content: str) -> str:
    """
    渲染 Markdown HTML。

    :param content: 要渲染的 Markdown 内容
    :type content: str
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """
    inline_css = read_resource_file("css/md.css")

    html_content = markdown.markdown(
        content,
        extensions=["tables", "fenced_code", "toc", "nl2br"],
    )

    return render_template(
        "htmls/md.html.jinja2",
        inline_css=inline_css,
        content=html_content,
    )


__all__ = [
    'render_markdown',
]