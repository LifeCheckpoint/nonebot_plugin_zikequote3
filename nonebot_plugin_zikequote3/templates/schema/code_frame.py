"""
高亮代码显示模板
"""
from .. import render_template, read_resource_file


def render_code_frame(
    title: str,
    subtitle: str,
    language: str,
    code: str,
    primary_color: str = "#667eea",
    secondary_color: str = "#764ba2"
) -> str:
    """
    渲染代码高亮显示
    
    Args:
        title: 标题
        subtitle: 副标题
        language: 代码语言（例如 'python', 'javascript', 'toml'）
        code: 代码内容
        primary_color: 主色调
        secondary_color: 副色调
        
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
        title=title,
        subtitle=subtitle,
        language=f"language-{language}",
        code=code,
        primary_color=primary_color,
        secondary_color=secondary_color
    )


__all__ = [
    'render_code_frame',
]