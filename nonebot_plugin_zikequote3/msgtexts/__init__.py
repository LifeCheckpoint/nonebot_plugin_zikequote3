"""
消息模板渲染中转层
提供类型安全的Jinja2模板渲染方法
"""
from jinja2 import Environment, FileSystemLoader, select_autoescape

# 初始化Jinja2环境
from ..paths import PluginPath

all_template_dir = [str(p.absolute()) for p in PluginPath.module_msgtexts_root.glob('*/')]

env = Environment(
    loader=FileSystemLoader(all_template_dir),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)


def render_template(template_name: str, **kwargs) -> str:
    """
    通用模板渲染函数
    
    Args:
        template_name: 模板文件名
        **kwargs: 模板参数
        
    Returns:
        渲染后的字符串
    """
    template = env.get_template(template_name)
    return template.render(**kwargs)


from . import general
from . import quote_read


__all__ = [
    'general',
    'quote_read',
]
