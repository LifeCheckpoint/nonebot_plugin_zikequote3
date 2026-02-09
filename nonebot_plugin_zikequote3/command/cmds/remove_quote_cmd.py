"""
删除语录命令处理器（dishka DI 版本）。

替代旧的 remove_quote_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
)
from nonebot.adapters import Message
from nonebot.params import CommandArg

from ..command_definition_new import matcher_remove_quote
from ...di import get_container
from ...services import QuoteWriteService
from ...utils.error_report import event_exception_failmsg_a, event_exception

logger = logging.getLogger(__name__)


@matcher_remove_quote.handle()
async def handle_remove_quote(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
) -> None:
    """
    删除语录。

    支持两种方式：
    1. 回复一条语录消息：``/删语录``
    2. 直接指定语录 ID：``/删语录 <quote_id>``
    """
    reply = event.reply
    arg_text = arg.extract_plain_text().strip()

    container = get_container()
    async with container() as request_scope:
        quote_write_svc = await request_scope.get(QuoteWriteService)

        quote_id: str | None = None

        # 方式1：通过回复消息获取语录 ID
        if reply is not None:
            with event_exception(operation="ignore"):
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

        async with event_exception_failmsg_a(matcher_remove_quote, "删除语录"):
            await quote_write_svc.delete_quote(quote_id)

        await matcher_remove_quote.finish("语录删除成功~(≧▽≦)")
