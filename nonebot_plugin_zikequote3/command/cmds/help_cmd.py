"""
语录帮助命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
调用 help 模板的预填充数据构建函数，渲染为图片后发送。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import MessageSegment as MsgSeg
from nonebot.exception import FinishedException

from ..command_definition import matcher_get_help
from ...di import Inject, inject
from ...services.html_render_service import HtmlRenderServiceBase
from ...templates.registry import HELP
from ...templates.schema.help import build_default_help_data, render_help

logger = logging.getLogger(__name__)


@matcher_get_help.handle()
@inject
async def handle_get_help(
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
) -> None:
    """
    处理语录帮助命令。

    构建默认帮助数据并渲染为图片发送，渲染失败时降级为纯文本提示。

    :param html_render_svc: HTML 渲染服务（DI 注入）
    :type html_render_svc: HtmlRenderServiceBase
    """
    try:
        data = build_default_help_data()
        html = render_help(data)
        img = await html_render_svc.render(html, width=HELP.width, height=HELP.height)
        await matcher_get_help.finish(MsgSeg.image(img))
    except FinishedException:
        raise
    except Exception:
        logger.warning("渲染帮助文档图片失败，回退为纯文本提示", exc_info=True)
        await matcher_get_help.finish(
            "语录帮助渲染失败，请稍后重试或联系管理员（＞人＜；）"
        )
