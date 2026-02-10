"""
LLM 提示词模板渲染中转层。

提供类型安全的 Jinja2 模板渲染方法。
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

template_path = Path(__file__).parent
env = Environment(
    loader=FileSystemLoader(template_path),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)


def render_template(template_name: str, **kwargs) -> str:
    """
    通用模板渲染函数。

    :param template_name: 模板文件名
    :type template_name: str
    :param kwargs: 模板参数
    :returns: 渲染后的字符串
    :rtype: str
    """
    template = env.get_template(template_name)
    return template.render(**kwargs)


from . import quote_pickup

__all__ = [
    'quote_pickup',
]