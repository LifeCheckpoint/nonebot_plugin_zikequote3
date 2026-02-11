"""
Markdown 模板。

提供 Markdown 内容的 HTML 渲染方法。
"""

import markdown
from pydantic import BaseModel

from ..registry import MD, render_with_spec


class TemplateMarkdownData(BaseModel):
    """Markdown 渲染数据。"""

    content: str
    title: str = "Markdown 文档"


def render_markdown(data: "TemplateMarkdownData | str") -> str:
    """
    渲染 Markdown HTML。兼容旧接口：接受字符串或 Pydantic 模型。

    :param data: Markdown 内容字符串，或 TemplateMarkdownData 模型
    :type data: TemplateMarkdownData | str
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """
    if isinstance(data, str):
        data = TemplateMarkdownData(content=data)

    html_content = markdown.markdown(
        data.content,
        extensions=["tables", "fenced_code", "toc", "nl2br"],
    )

    return render_with_spec(MD, content=html_content, title=data.title)


__all__ = [
    'TemplateMarkdownData',
    'render_markdown',
]