"""
## 网页截图插件

建议将 css 与 html 文件命名为相同文件名，放在同一目录下，在 html 做好引用

可以将文件的渲染流程交由本插件处理完成，包括临时文件的清除
"""

from .screenshot import async_generate_screenshot
from .html_parser import generate_html_by_file, generate_html_by_str, full_render_html, full_render_markdown, template