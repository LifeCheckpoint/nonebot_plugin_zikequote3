"""
随机语录图命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageSegment as MsgSeg,
)
from nonebot.adapters import Message
from nonebot.params import CommandArg

from ..command_definition import matcher_random_quote_image
from ...di import Inject, inject
from ...services import QuoteReadService, QuoteWriteService
from ...database.image_store import ImageStore
from ._error_handlers import command_error_handler, suppress_error

logger = logging.getLogger(__name__)


@matcher_random_quote_image.handle()
@inject
async def handle_random_quote_image(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
    quote_read_svc: QuoteReadService = Inject(QuoteReadService),
    quote_write_svc: QuoteWriteService = Inject(QuoteWriteService),
    image_store: ImageStore = Inject(ImageStore),
) -> None:
    """
    处理随机语录图命令。

    随机获取一条含图片的语录，仅发送图片内容。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param bot: Bot 实例
    :type bot: Bot
    :param arg: 命令参数消息体
    :type arg: Message
    :param quote_read_svc: 语录读取服务（DI 注入）
    :type quote_read_svc: QuoteReadService
    :param quote_write_svc: 语录写入服务（DI 注入）
    :type quote_write_svc: QuoteWriteService
    :param image_store: 图片存储（DI 注入）
    :type image_store: ImageStore
    """
    key = arg.extract_plain_text().strip()
    group_id = str(event.group_id)

    q_result = None

    async with command_error_handler(matcher_random_quote_image, "获取语录图片"):
        # 获取随机语录，然后在命令层过滤含图片的
        # 使用 get_quotes_by_group 获取全部，再筛选含图片的
        quotes = list(await quote_read_svc.get_quotes_by_group(group_id))

        if key:
            quotes = [q for q in quotes if q.content and key in q.content]

        # 过滤含图片的语录
        quotes = [q for q in quotes if q.image_content_uuid is not None]

        if not quotes:
            await matcher_random_quote_image.finish("没有找到符合条件的语录哦~")

        import random
        q_result = random.choice(quotes)

        if q_result.image_content_uuid is None:
            await matcher_random_quote_image.finish("没有找到符合条件的语录哦~")

        # 发送语录图片
        img_path = image_store.get_path(q_result.image_content_uuid)
        image_data = img_path.read_bytes()
        await matcher_random_quote_image.send(MsgSeg.image(image_data))

    # 更新语录出现次数
    if q_result is not None:
        with suppress_error("更新语录出现次数"):
            await quote_read_svc.increment_show_time(q_result.quote_id)

        # 添加消息映射
        with suppress_error("添加消息映射"):
            await quote_write_svc.create_msg_quote_mapping(
                str(event.message_id), q_result.quote_id,
            )
