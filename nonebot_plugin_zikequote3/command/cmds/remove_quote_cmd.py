"""
删除语录命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
"""

from __future__ import annotations

from nonebot import logger

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
)
from nonebot.adapters import Message
from nonebot.params import CommandArg

from ..command_definition import matcher_remove_quote
from ...di import Inject, inject
from ...services import QuoteWriteService
from ._error_handlers import command_error_handler, suppress_error

@matcher_remove_quote.handle()
@inject
async def handle_remove_quote(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
    quote_write_svc: QuoteWriteService = Inject(QuoteWriteService),
) -> None:
    """
    处理删除语录命令。

    支持两种方式：

    1. 回复一条语录消息：``/删语录``
    2. 直接指定语录 ID：``/删语录 <quote_id>``

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param bot: Bot 实例
    :type bot: Bot
    :param arg: 命令参数消息体
    :type arg: Message
    :param quote_write_svc: 语录写入服务（DI 注入）
    :type quote_write_svc: QuoteWriteService
    """
    reply = event.reply
    arg_text = arg.extract_plain_text().strip()

    quote_id: str | None = None

    # 方式1：通过回复消息获取语录 ID
    if reply is not None:
        with suppress_error("通过回复消息获取语录ID"):
            quote_id = await quote_write_svc.get_quote_id_by_msg_id(
                str(reply.message_id)
            )

    # 方式2：通过命令参数获取语录 ID
    if quote_id is None and arg_text:
        quote_id = arg_text

    if not quote_id:
        await matcher_remove_quote.finish(
            "请回复一条语录消息或提供语录 ID 来删除哦~"
        )

    async with command_error_handler(matcher_remove_quote, "删除语录"):
        await quote_write_svc.delete_quote(quote_id)

    await matcher_remove_quote.finish("语录删除成功~(≧▽≦)")
