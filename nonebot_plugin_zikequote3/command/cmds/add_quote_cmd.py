"""
添加语录命令处理器。

通过 @inject 装饰器自动从 dishka 容器获取服务依赖。
"""

from __future__ import annotations

from nonebot import logger

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
)

from ..command_definition import matcher_add_quote
from ...di import Inject, inject
from ...services import QuoteWriteService, GroupService
from ...database.image_store import ImageStore
from ._error_handlers import command_error_handler, suppress_error

async def _fetch_image_from_url_or_file(url_or_file: str) -> bytes:
    """
    从 URL 或本地文件路径获取图片二进制数据。

    :param url_or_file: 图片的 URL 地址或本地文件路径
    :type url_or_file: str
    :returns: 图片的二进制数据
    :rtype: bytes
    """
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
@inject
async def handle_add_quote(
    event: GroupMessageEvent,
    bot: Bot,
    quote_write_svc: QuoteWriteService = Inject(QuoteWriteService),
    group_svc: GroupService = Inject(GroupService),
    image_store: ImageStore = Inject(ImageStore),
) -> None:
    """
    处理添加语录命令。

    从回复消息中提取语录文本和图片，调用服务层写入数据库。

    :param event: 群消息事件
    :type event: GroupMessageEvent
    :param bot: Bot 实例
    :type bot: Bot
    :param quote_write_svc: 语录写入服务（DI 注入）
    :type quote_write_svc: QuoteWriteService
    :param group_svc: 群组服务（DI 注入）
    :type group_svc: GroupService
    :param image_store: 图片存储（DI 注入）
    :type image_store: ImageStore
    """
    reply = event.reply
    if reply is None:
        await matcher_add_quote.finish("您还没有回复想要加的语录呢(^///^)")

    if reply.sender.user_id == bot.self_id:
        await matcher_add_quote.finish("呀呀呀，怎么在添加我的语录呢？(>_<)")

    if reply.message.extract_plain_text().strip() == "" and reply.message.count("image") == 0:
        await matcher_add_quote.finish("语录内容不能为空哦~")

    group_id = str(event.group_id)

    # 确保群组记录存在（外键约束保护）
    await group_svc.ensure_group_exists(group_id)

    # 检查图片数据存在性
    image_uuid = None
    img_url_or_file: str = ""
    if reply.message.count("image") >= 1:
        async with command_error_handler(matcher_add_quote, "获取将要添加的图片数据"):
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
    async with command_error_handler(matcher_add_quote, "添加语录"):
        if image_uuid is not None:
            # 有图片时使用 add_quote_with_image_data，同时注册图片元数据到数据库
            stored_path = image_store.get_path(image_uuid)
            qid = await quote_write_svc.add_quote_with_image_data(
                group_id=group_id,
                author_id=str(reply.sender.user_id),
                content=content_text,
                image_uuid=image_uuid,
                original_filename=img_url_or_file,
                stored_filename=stored_path.name,
                file_path=str(stored_path),
                checksum_sha256=image_store.get_sha256(image_uuid),
            )
        else:
            qid = await quote_write_svc.add_quote(
                group_id=group_id,
                author_id=str(reply.sender.user_id),
                content=content_text,
                image_content_uuid=None,
            )

    await matcher_add_quote.send("语录添加成功~(≧▽≦)")

    # 检查用户-群映射存在性
    with suppress_error("检查用户-群映射"):
        await group_svc.ensure_member(group_id, str(reply.sender.user_id))

    # 添加消息映射
    with suppress_error("添加消息映射"):
        await quote_write_svc.create_msg_quote_mapping(
            str(reply.message_id), qid,
        )
