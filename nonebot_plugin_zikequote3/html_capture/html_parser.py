"""
html 网页文件
"""
from .screenshot import async_generate_screenshot

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from pathlib import Path
from typing import Dict, Union
import markdown
from pymdownx.arithmatex import ArithmatexExtension
from random import randint

extensions = [
    ArithmatexExtension(
        generic=True,
        preview=False,
        tex_inline_wrap=('$', '$'),  # 行内公式使用$...$
        tex_block_wrap=('$$', '$$')     # 块级公式使用$$...$$
    ),
    'pymdownx.arithmatex', # 数学公式支持
    'pymdownx.superfences', # 高级代码块
    'pymdownx.details', # 折叠内容
    'pymdownx.emoji', # 表情符号
    'pymdownx.highlight', # 代码高亮
    'pymdownx.tabbed', # 标签页
    'pymdownx.tilde', # 删除线/下标等
]

async def full_render_markdown(markdown_text: str, device_scale_factor: float = 2) -> bytes:
    """
    完整流程渲染 Markdown 文本并截图
    """
    markdown_html = markdown.markdown(markdown_text, extensions=extensions, output_format="html")
    template_file_path = Path(__file__).parent / "md_templates" / "md.html"
    output_file_path = Path(__file__).parent / "md_templates"
    image_bytes = await full_render_html(template_file_path, output_file_path, data={"content": markdown_html}, width=820, height=300, device_scale_factor=device_scale_factor)
    return image_bytes

async def full_render_html(
    html_template_file_path: Union[str, Path],
    dir_html_output: Path,
    data: Dict,
    width: int = 1000,
    height: int = 800,
    device_scale_factor: float = 2
) -> bytes:
    """
    完整流程渲染 HTML 文件并截图，自动处理临时文件

    Args:
        html_template_file_path: HTML 模板文件的路径
        dir_html_output: 渲染结果的输出路径，注意应该将 html 渲染的依赖文件放在该目录下
        data: 传递给模板的上下文数据字典
    """

    # 获取临时文件名
    temp_file_name = f"{randint(1000000000, 9999999999)}"
    html_output_path = dir_html_output / f"{temp_file_name}.html"
    image_output_path = dir_html_output / f"{temp_file_name}.png"

    # html 渲染
    if not generate_html_by_file(html_output_path, html_template_file_path, data):
        # 删除临时文件
        html_output_path.unlink(missing_ok=True)
        raise RuntimeError(f"生成 HTML 文件失败: {html_output_path}")
    
    # 截图
    returncode, _, err = await async_generate_screenshot(html_output_path, image_output_path, width=width, height=height, device_scale_factor=device_scale_factor)
    if returncode != 0:
        # 删除临时文件
        html_output_path.unlink(missing_ok=True)
        image_output_path.unlink(missing_ok=True)
        raise RuntimeError(f"生成截图失败: {image_output_path}, {err}")
    
    # 读取图片字节并清理临时文件
    bytes_image = image_output_path.read_bytes()
    html_output_path.unlink(missing_ok=True)
    image_output_path.unlink(missing_ok=True)

    return bytes_image


def generate_html_by_str(
    html_output_path: Union[str, Path],
    html_template_string: str,
    data: Dict
) -> bool:
    """
    使用 Jinja2 渲染 HTML 模板字符串并保存到指定路径。

    Args:
        html_output_path: 渲染结果的输出文件路径。
        html_template_string: HTML 模板内容的字符串。
        data: 传递给模板的上下文数据字典。
    """
    # 将路径转换为 Path 对象
    output_path = Path(html_output_path)

    try:
        # 直接从字符串创建模板对象
        template = Template(html_template_string, autoescape=True)
        rendered_html = template.render(**data)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return True

    except Exception as e:
        print(f"渲染过程中发生错误: {e}")
        return False

def generate_html_by_file(
    html_output_path: Union[str, Path],
    html_template_file_path: Union[str, Path],
    data: Dict
) -> bool:
    """
    使用 Jinja2 渲染 HTML 模板并保存到指定路径。

    Args:
        html_output_path: 渲染结果的输出文件路径
        html_template_file_path: HTML 模板文件的路径
        data: 传递给模板的上下文数据字典
    """
    output_path = Path(html_output_path)
    template_path = Path(html_template_file_path)

    # 检查模板文件是否存在
    if not template_path.is_file():
        print(f"模板文件未找到: {template_path}")
        return False

    # 获取模板文件所在的目录作为加载路径
    template_dir = template_path.parent
    template_filename = template_path.name

    try:
        # 创建一个新的 Jinja2 环境
        # loader 设置为从模板文件所在的目录加载
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
        template = env.get_template(template_filename)
        rendered_html = template.render(**data)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return True

    except TemplateNotFound:
        # 理论上上面已经检查过，但为了健壮性可以捕获
        print(f"错误：在 {template_dir} 中未找到模板文件 {template_filename}")
        return False
    
    except Exception as e:
        print(f"渲染过程中发生错误: {e}")
        return False
    
def template(template_str: str, data: Dict) -> str:
    """
    渲染模板字符串
    Args:
        template: 模板字符串
        data: 上下文数据字典
    Returns:
        渲染后的 HTML 字符串
    """
    try:
        # 直接从字符串创建模板对象
        template = Template(template_str, autoescape=True)
        rendered_result = template.render(**data)

        return rendered_result

    except Exception as e:
        print(f"渲染过程中发生错误: {e}")
        return ""