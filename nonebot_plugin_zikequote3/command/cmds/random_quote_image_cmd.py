"""
随机语录图命令处理器（dishka DI 版本）。

替代旧的 random_quote_image_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。
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

from ..command_definition_new import matcher_random_quote_image
from ...di import get_container
from ...services import QuoteReadService, QuoteWriteService, UserService
from ...database.image_store import ImageStore
from ...utils.error_report import event_exception_failmsg_a, event_exception

logger = logging.getLogger(__name__)


@matcher_random_quote_image.handle()
async def handle_random_quote_image(
    event: GroupMessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
) -> None:
    """随机语录图，仅返回含图片的语录。"""
    key = arg.extract_plain_text().strip()
    group_id = str(event.group_id)

    container = get_container()
    async with container() as request_scope:
        quote_read_svc = await request_scope.get(QuoteReadService)
        quote_write_svc = await request_scope.get(QuoteWriteService)
        user_svc = await request_scope.get(UserService)
        image_store = await request_scope.get(ImageStore)

        q_result = None

        async with event_exception_failmsg_a(matcher_random_quote_image, "获取语录图片"):
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
            with event_exception(operation="ignore"):
                await quote_read_svc.increment_show_time(q_result.quote_id)

            # 添加消息映射
            with event_exception(operation="ignore"):
                await quote_write_svc.create_msg_quote_mapping(
                    str(event.message_id), q_result.quote_id,
                )
