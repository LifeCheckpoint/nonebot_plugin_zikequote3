"""
Markdown 模板
"""
# TODO: Refactor

from .. import render_template, read_resource_file

def render_markdown(content: str) -> str:
    """
    渲染 Markdown HTML
    
    Args:
        content: 要渲染的 Markdown 内容
        
    Returns:
        渲染后的 HTML 字符串
    """
    inline_katex_min_css = read_resource_file("css/vendor/katex.min.css")
    inline_css = read_resource_file("css/md.css")
    katex_min_js = read_resource_file("js/vendor/katex.min.js")
    katex_auto_render_js = read_resource_file("js/vendor/auto-render.min.js")

    return render_template(
        "htmls/md.html.jinja2",
        inline_katex_min_css=inline_katex_min_css,
        inline_css=inline_css,
        katex_min_js=katex_min_js,
        katex_auto_render_js=katex_auto_render_js,
        content=content
    )


__all__ = [
    'render_markdown',
]