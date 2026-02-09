"""
隐私政策命令处理器（dishka DI 版本）。

替代旧的 get_privacy_cmd.py，消除星号导入和延迟导入。
此命令不依赖数据库服务，仅读取静态 Markdown 文件并渲染为图片。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import MessageSegment as MsgSeg

from ..command_definition import matcher_get_privacy
from ...paths import PluginPath
from ...templates import md as md_template
from ...html_capture import html_img_render

logger = logging.getLogger(__name__)


@matcher_get_privacy.handle()
async def handle_get_privacy() -> None:
    """获取隐私政策。"""
    privacy_markdown = PluginPath.module_resources_root / "privacy.md"

    if not privacy_markdown.exists():
        await matcher_get_privacy.finish(
            "隐私政策文件不存在，请联系管理员处理（＞人＜；）"
        )

    try:
        md_content = privacy_markdown.read_text(encoding="utf-8")
        html = md_template.render_markdown(md_content)
        img = await html_img_render(html, width=800)
        await matcher_get_privacy.finish(MsgSeg.image(img))
    except Exception:
        logger.warning("渲染隐私政策图片失败，回退为纯文本", exc_info=True)
        await matcher_get_privacy.finish(
            privacy_markdown.read_text(encoding="utf-8")
        )
