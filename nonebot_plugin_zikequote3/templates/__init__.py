"""
HTML 模板渲染中转层。

提供类型安全的 Jinja2 模板渲染方法，处理 CSS/JS 资源内联。
"""
from functools import lru_cache
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

template_path = Path(__file__).parent / "src"
env = Environment(
    loader=FileSystemLoader(template_path),
    autoescape=select_autoescape(['html', 'xml']),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True
)

def render_template(template_name: str, **kwargs) -> str:
    """
    通用模板渲染函数。

    :param template_name: 模板文件名
    :type template_name: str
    :param kwargs: 模板参数
    :returns: 渲染后的 HTML 字符串
    :rtype: str
    """
    template = env.get_template(template_name)
    return template.render(**kwargs)

@lru_cache(maxsize=32)
def read_resource_file(file_path: str) -> str:
    """
    读取资源文件内容（CSS/JS）。

    :param file_path: 资源文件路径
    :type file_path: str
    :returns: 文件内容字符串
    :rtype: str
    :raises FileNotFoundError: 当资源文件不存在时抛出
    """
    resource_path = Path(__file__).parent / "src" / "assets" / file_path
    if not resource_path.exists():
        raise FileNotFoundError(f"资源文件未找到: {resource_path}")
    return resource_path.read_text(encoding='utf-8')
    

from .schema import card
from .schema import code_frame
from .schema import help
from .schema import listing
from .schema import rank
from .schema import md
from .schema import migration
from .schema import user_info
from .registry import TemplateSpec, render_with_spec, ALL_SPECS

__all__ = [
    "card",
    "code_frame",
    "help",
    "listing",
    "rank",
    "md",
    "migration",
    "user_info",
    "TemplateSpec",
    "render_with_spec",
    "ALL_SPECS",
]