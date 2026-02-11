"""
隐私政策命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
此命令不依赖数据库服务，仅读取静态 Markdown 文件并渲染为图片。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import MessageSegment as MsgSeg
from nonebot.exception import FinishedException

from ..command_definition import matcher_get_privacy
from ...di import Inject, inject
from ...services.html_render_service import HtmlRenderServiceBase
from ...paths import PluginPath
from ...templates import md as md_template

logger = logging.getLogger(__name__)


@matcher_get_privacy.handle()
@inject
async def handle_get_privacy(
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
) -> None:
    """
    处理获取隐私政策命令。

    读取静态 Markdown 隐私政策文件并渲染为图片发送，渲染失败时降级为纯文本。

    :param html_render_svc: HTML 渲染服务（DI 注入）
    :type html_render_svc: HtmlRenderServiceBase
    """
    privacy_markdown = PluginPath.module_resources_root / "privacy.md"

    if not privacy_markdown.exists():
        await matcher_get_privacy.finish(
            "隐私政策文件不存在，请联系管理员处理（＞人＜；）"
        )

    try:
        md_content = privacy_markdown.read_text(encoding="utf-8")
        html = md_template.render_markdown(md_content)
        img = await html_render_svc.render(html, width=800)
        await matcher_get_privacy.finish(MsgSeg.image(img))
    except FinishedException:
        raise
    except Exception:
        logger.warning("渲染隐私政策图片失败，回退为纯文本", exc_info=True)
        await matcher_get_privacy.finish(
            privacy_markdown.read_text(encoding="utf-8")
        )
