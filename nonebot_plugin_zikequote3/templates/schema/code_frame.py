"""
高亮代码显示模板
"""
from .. import render_template, read_resource_file
from pydantic import BaseModel


class TemplateCodeFrameData(BaseModel):
    """代码高亮显示渲染数据类"""

    """标题"""
    title: str

    """副标题"""
    subtitle: str

    """代码语言"""
    language: str

    """代码内容"""
    code: str


def render_code_frame(data: TemplateCodeFrameData) -> str:
    """
    渲染代码高亮显示
    
    Args:
        data: 代码显示渲染数据
        
    Returns:
        渲染后的 HTML 字符串
    """
    inline_css = read_resource_file("css/codeframe.css")
    
    try:
        inline_github_dark_min_css = read_resource_file("css/vendor/github-dark.min.css")
    except FileNotFoundError:
        inline_github_dark_min_css = ""
    
    try:
        inline_highlight_min_js = read_resource_file("js/vendor/highlight.min.js")
    except FileNotFoundError:
        inline_highlight_min_js = ""
    
    return render_template(
        "htmls/code_frame.html.jinja2",
        inline_css=inline_css,
        inline_github_dark_min_css=inline_github_dark_min_css,
        inline_highlight_min_js=inline_highlight_min_js,
        **data.model_dump()
    )


__all__ = [
    "TemplateCodeFrameData",
    "render_code_frame",
]