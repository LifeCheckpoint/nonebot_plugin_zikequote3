"""
html 网页文件
"""
from .screenshot import async_generate_screenshot

from pathlib import Path
from pymdownx.arithmatex import ArithmatexExtension
import markdown
import uuid


async def html_img_render(
    html_content: str, cache_dir: Path,
    width: int = 1000, height: int = 800, device_scale_factor: float = 2
) -> bytes:
    """
    渲染 HTML 文件并截图，自动处理临时文件

    Args:
        :param html_content: HTML 内容字符串
        :param cache_dir: 用于存放临时文件的目录
        :param width: 截图宽度
        :param height: 截图高度
        :param device_scale_factor: 设备像素比

    Returns:
        :return: 截图结果字节
    """

    # 获取临时文件名
    temp_file_name = uuid.uuid4().hex
    temp_html = cache_dir / f"{temp_file_name}.html"
    temp_image = cache_dir / f"{temp_file_name}.png"

    # html 渲染
    try:
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_html.write_text(html_content, encoding="utf-8")
    except Exception as e:
        temp_html.unlink(missing_ok=True)
        print(f"生成 HTML 文件失败: {temp_html}")
        raise e
    
    # 截图
    returncode, _, err = await async_generate_screenshot(
        temp_html, temp_image, width=width, height=height, device_scale_factor=device_scale_factor
    )

    # 截图返回码检查
    if returncode != 0:
        temp_html.unlink(missing_ok=True)
        temp_image.unlink(missing_ok=True)
        raise RuntimeError(f"生成截图失败: {temp_image}, {err}")
    
    # 读取图片字节并清理临时文件
    bytes_image = temp_image.read_bytes()
    temp_html.unlink(missing_ok=True)
    temp_image.unlink(missing_ok=True)

    return bytes_image


async def parse_md2html(markdown_text: str) -> str:
    """
    将 Markdown 文本转换为 HTML
    """
    extensions = [
        ArithmatexExtension(
            generic=True,
            preview=False,
            tex_inline_wrap=('$', '$'),  # 行内公式使用$...$
            tex_block_wrap=('$$', '$$')     # 块级公式使用$$...$$
        ),
        'pymdownx.extra',      # 系列扩展
        'pymdownx.arithmatex', # 数学公式支持
        'pymdownx.details', # 折叠内容
        'pymdownx.emoji', # 表情符号
        'pymdownx.highlight', # 代码高亮
        'pymdownx.tabbed', # 标签页
        'pymdownx.tilde', # 删除线/下标等
    ]
    return markdown.markdown(markdown_text, extensions=extensions, output_format="html")