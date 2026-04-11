"""
最近语录命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
复用现有 listing 模板与 HTML 截图链路展示当前群最近语录。
"""

from __future__ import annotations

from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot.params import CommandArg

from ..command_definition import matcher_recent_quotes
from ...di import Inject, inject
from ...exceptions import ValidationException
from ...msgtexts import quote_read
from ...services import ConfigService, QuoteReadService, UserService
from ...services.html_render_service import HtmlRenderServiceBase
from ...database.image_store import ImageStore
from ...templates.registry import LISTING
from ...templates.schema.listing import TemplateQuoteListData, render_list
from ._display_helpers import transform_quotes_to_template_boxes
from ._error_handlers import command_error_handler

_DEFAULT_LIMIT = 3
_MAX_LIMIT = 10


def _parse_recent_limit(
    raw_arg: str,
    raw_message: str | None = None,
) -> tuple[int, str | None]:
    """解析最近语录数量参数，返回生效数量与可选截断提示。"""
    text = raw_arg.strip()
    raw_text = raw_message.strip() if raw_message is not None else text
    if not raw_text:
        return _DEFAULT_LIMIT, None

    if text != raw_text:
        raise ValidationException("数量参数必须是 1 到 10 之间的整数")

    if not text.isdecimal():
        raise ValidationException("数量参数必须是 1 到 10 之间的整数")

    requested = int(text)
    if requested < 1:
        raise ValidationException("数量参数必须是 1 到 10 之间的整数")
    if requested > _MAX_LIMIT:
        return _MAX_LIMIT, f"已按上限展示最近 {_MAX_LIMIT} 条语录"
    return requested, None


@matcher_recent_quotes.handle()
@inject
async def handle_recent_quotes(
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
    quote_read_svc: QuoteReadService = Inject(QuoteReadService),
    user_svc: UserService = Inject(UserService),
    image_store: ImageStore = Inject(ImageStore),
    html_render_svc: HtmlRenderServiceBase = Inject(HtmlRenderServiceBase),
    config_svc: ConfigService = Inject(ConfigService),
) -> None:
    """
    处理最近语录命令。

    仅支持一个数量参数，默认展示当前群最近 3 条语录；
    当数量超过上限时自动截断，并在 listing 头部展示轻提示。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param arg: 命令参数消息体
    :type arg: Message
    :param quote_read_svc: 语录读取服务（DI 注入）
    :type quote_read_svc: QuoteReadService
    :param user_svc: 用户服务（DI 注入）
    :type user_svc: UserService
    :param image_store: 图片存储（DI 注入）
    :type image_store: ImageStore
    :param html_render_svc: HTML 渲染服务（DI 注入）
    :type html_render_svc: HtmlRenderServiceBase
    :param config_svc: 配置服务（DI 注入）
    :type config_svc: ConfigService
    """
    group_id = str(event.group_id)

    async with command_error_handler(matcher_recent_quotes, "解析参数"):
        limit, clamp_hint = _parse_recent_limit(
            arg.extract_plain_text(),
            str(arg),
        )

    async with command_error_handler(matcher_recent_quotes, "获取最近语录"):
        quotes = await quote_read_svc.get_recent_quotes_by_group(
            group_id,
            limit=limit,
        )
        if not quotes:
            await matcher_recent_quotes.finish(quote_read.quote_not_found())

        cfg = await config_svc.get_parsed_config(group_id)
        max_content_length = cfg.showcase.quote_content_max_length

        quote_boxes = await transform_quotes_to_template_boxes(
            quotes,
            group_id,
            quote_read_svc=quote_read_svc,
            user_svc=user_svc,
            image_store=image_store,
            show_author=True,
            show_time=True,
            max_content_length=max_content_length,
        )

        html = render_list(TemplateQuoteListData(
            title="最近语录",
            desc=f"当前群（{group_id}）",
            addition=f"共展示 {len(quote_boxes)} 条最近语录",
            clamp_hint=clamp_hint,
            quotes=quote_boxes,
        ))
        img = await html_render_svc.render(
            html,
            width=LISTING.width,
            height=LISTING.height,
        )
        await matcher_recent_quotes.finish(MsgSeg.image(img))


__all__ = [
    "handle_recent_quotes",
    "_parse_recent_limit",
]
