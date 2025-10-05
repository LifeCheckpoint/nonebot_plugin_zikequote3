"""
HTML模板渲染中转层
提供类型安全的Jinja2模板渲染方法，处理CSS/JS资源内联
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

template_path = Path(__file__).parent / "src"
env = Environment(
    loader=FileSystemLoader(template_path),
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
        渲染后的HTML字符串
    """
    template = env.get_template(template_name)
    return template.render(**kwargs)

def read_resource_file(file_path: str) -> str:
    """
    读取资源文件内容（CSS/JS）
    
    Args:
        file_path: 资源文件路径
        
    Returns:
        文件内容字符串
    """
    resource_path = Path(__file__).parent / "src" / "assets" / file_path
    try:
        return resource_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        raise FileNotFoundError(f"资源文件未找到: {resource_path}")
    except Exception as e:
        raise Exception(f"读取资源文件失败: {e}")
    

from .schema import card
from .schema import code_frame
from .schema import listing
from .schema import rank
from .schema import md

__all__ = [
    'card',
    'code_frame', 
    'listing',
    'rank',
    'md',
]