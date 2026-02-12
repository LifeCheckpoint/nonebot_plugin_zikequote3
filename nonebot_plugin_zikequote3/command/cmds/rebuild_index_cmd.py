"""重建语录向量索引命令处理器。

通过 ``@inject`` 装饰器自动从 dishka 容器获取服务依赖。
支持 ``--all`` 选项重建所有群的索引（需要管理员权限）。
使用 ``asyncio.create_task`` 后台执行重建，避免阻塞用户交互。
"""

from __future__ import annotations

import asyncio
import logging

from dishka import AsyncContainer
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot_plugin_alconna import Query

from ..command_definition import matcher_rebuild_index
from ...di import Inject, get_container, inject
from ...vector_search.search_service import VectorSearchService

logger = logging.getLogger(__name__)


async def _do_rebuild(
    container: AsyncContainer,
    bot: Bot,
    event: GroupMessageEvent,
    group_id: str | None,
    scope_desc: str,
) -> None:
    """后台执行重建索引，完成后通过 bot.send 发送结果。

    在内部创建独立的 REQUEST 作用域来获取 :class:`VectorSearchService`，
    避免使用 handler 中已关闭的 REQUEST 作用域。

    :param container: dishka 异步容器。
    :type container: AsyncContainer
    :param bot: Bot 实例，用于发送消息。
    :type bot: Bot
    :param event: 群消息事件，用于确定发送目标。
    :type event: GroupMessageEvent
    :param group_id: 群组 ID，为 ``None`` 时重建全部群。
    :type group_id: str | None
    :param scope_desc: 重建范围描述文本，用于消息提示。
    :type scope_desc: str
    """
    try:
        async with container() as request_container:
            vector_search_svc = await request_container.get(VectorSearchService)
            count = await vector_search_svc.reindex_all(group_id)
        await bot.send(event, f"✅ 索引重建完成！{scope_desc}共索引了 {count} 条语录。")
    except Exception as e:
        logger.error("后台重建索引失败: %s", e)
        await bot.send(event, f"❌ 索引重建失败: {e}")


@matcher_rebuild_index.handle()
@inject
async def handle_rebuild_index(
    bot: Bot,
    event: GroupMessageEvent,
    rebuild_all: Query[bool] = Query("rebuild_all.value", False),
    vector_search_svc: VectorSearchService = Inject(VectorSearchService),
) -> None:
    """处理重建语录向量索引命令。

    :param bot: Bot 实例，用于后台任务发送消息。
    :type bot: Bot
    :param event: 群消息事件。
    :type event: GroupMessageEvent
    :param rebuild_all: 是否重建所有群的索引。
    :type rebuild_all: Query[bool]
    :param vector_search_svc: 向量搜索服务（DI 注入，仅用于检查是否启用）。
    :type vector_search_svc: VectorSearchService
    """
    if vector_search_svc is None:
        await matcher_rebuild_index.finish(
            "向量搜索功能未启用，请先在配置中启用 embedding。"
        )

    group_id = str(event.group_id)
    do_all = rebuild_all.result if rebuild_all.available else False

    if do_all:
        scope_desc = "所有群"
        target_group: str | None = None
    else:
        scope_desc = f"本群({group_id})"
        target_group = group_id

    await matcher_rebuild_index.send(
        f"⏳ 正在后台重建{scope_desc}的语录向量索引，完成后会通知你..."
    )

    asyncio.create_task(
        _do_rebuild(get_container(), bot, event, target_group, scope_desc)
    )
