"""
添加语录命令处理器（dishka DI 版本）。

替代旧的 add_quote_cmd.py，消除星号导入和延迟导入，
通过 dishka 容器获取服务依赖。
"""

from __future__ import annotations

import logging

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
)

from ..command_definition import matcher_add_quote
from ...di import get_container
from ...services import QuoteWriteService, UserService, GroupService
from ...database.image_store import ImageStore
from ...utils.error_report import event_exception_failmsg_a, event_exception

logger = logging.getLogger(__name__)


async def _fetch_image_from_url_or_file(url_or_file: str) -> bytes:
    """从 URL 或本地文件路径获取图片数据。"""
    import aiohttp

    if url_or_file.startswith(("http://", "https://")):
        async with aiohttp.ClientSession() as session:
            async with session.get(url_or_file) as resp:
                resp.raise_for_status()
                return await resp.read()
    else:
        from pathlib import Path

        return Path(url_or_file).read_bytes()


@matcher_add_quote.handle()
async def handle_add_quote(
    event: GroupMessageEvent,
    bot: Bot,
) -> None:
    """添加语录。"""
    reply = event.reply
    if reply is None:
        await matcher_add_quote.finish("您还没有回复想要加的语录呢(^///^)")

    if reply.sender.user_id == bot.self_id:
        await matcher_add_quote.finish("呀呀呀，怎么在添加我的语录呢？(>_<)")

    if reply.message.extract_plain_text().strip() == "" and reply.message.count("image") == 0:
        await matcher_add_quote.finish("语录内容不能为空哦~")

    group_id = str(event.group_id)

    container = get_container()
    async with container() as request_scope:
        quote_write_svc = await request_scope.get(QuoteWriteService)
        user_svc = await request_scope.get(UserService)
        group_svc = await request_scope.get(GroupService)
        image_store = await request_scope.get(ImageStore)

        # 检查图片数据存在性
        image_uuid = None
        if reply.message.count("image") >= 1:
            async with event_exception_failmsg_a(matcher_add_quote, "获取将要添加的图片数据"):
                picseg_data = reply.message.get("image")[0].data
                img_url_or_file = picseg_data.get("url") or picseg_data.get("file", "")
                img_data = await _fetch_image_from_url_or_file(img_url_or_file)
                # 使用 ImageStore 上传图片并获取 UUID
                image_uuid = image_store.upload(img_data, filename=img_url_or_file)

        # 检查语录内容存在性
        content_text = (
            reply.message.extract_plain_text().strip()
            if not reply.message.only("image")
            else None
        )

        qid: str = ""
        async with event_exception_failmsg_a(matcher_add_quote, "添加语录"):
            qid = await quote_write_svc.add_quote(
                group_id=group_id,
                author_id=str(reply.sender.user_id),
                content=content_text,
                image_content_uuid=image_uuid,
            )

        await matcher_add_quote.send("语录添加成功~(≧▽≦)")

        # 检查用户-群映射存在性
        with event_exception(operation="ignore"):
            await group_svc.ensure_member(group_id, str(reply.sender.user_id))

        # 添加消息映射
        with event_exception(operation="ignore"):
            await quote_write_svc.create_msg_quote_mapping(
                str(reply.message_id), qid,
            )
