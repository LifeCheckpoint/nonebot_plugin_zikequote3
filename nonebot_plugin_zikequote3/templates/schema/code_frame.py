"""
高亮代码显示模板。

提供代码高亮显示的数据模型与 HTML 渲染方法。
"""
from .. import render_template, read_resource_file
from pydantic import BaseModel


class TemplateCodeFrameData(BaseModel):
    """
    代码高亮显示渲染数据类。

    :param title: 标题
    :type title: str
    :param subtitle: 副标题
    :type subtitle: str
    :param language: 代码语言
    :type language: str
    :param code: 代码内容
    :type code: str
    """

    title: str
    subtitle: str
    language: str
    code: str


def render_code_frame(data: TemplateCodeFrameData) -> str:
    """
    渲染代码高亮显示。

    :param data: 代码显示渲染数据
    :type data: TemplateCodeFrameData
    :returns: 渲染后的 HTML 字符串
    :rtype: str
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