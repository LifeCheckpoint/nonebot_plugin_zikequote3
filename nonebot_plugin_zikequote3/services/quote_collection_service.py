"""
QuoteCollectionService —— 语录收集领域服务。

合并原模块：
- ``queue_service.py``          消息队列管理
- ``save_service.py``           从队列保存语录
- ``lock_service.py``           收集锁机制
- ``llm_selection_service.py``  LLM 筛选编排（LLM 调用通过 Protocol 抽象）

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Optional, Protocol, Sequence

from ..database.models.msgs_queue import MsgQueue
from ..database.repositories.msg_queue_repository import MsgQueueRepository
from ..exceptions import ResourceNotFoundError, ValidationException
from .group_service import GroupService
from .quote_write_service import QuoteWriteService
from .user_service import UserService

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  LLM 筛选结果数据类
# ------------------------------------------------------------------ #


class SelectedQuote:
    """LLM 筛选出的单条语录。"""

    __slots__ = ("msg_id", "content", "comment", "quote_id")

    def __init__(
        self,
        msg_id: str,
        content: str,
        comment: str = "",
        quote_id: Optional[str] = None,
    ) -> None:
        self.msg_id = msg_id
        self.content = content
        self.comment = comment
        self.quote_id = quote_id


# ------------------------------------------------------------------ #
#  收集结果数据类
# ------------------------------------------------------------------ #


@dataclass
class CollectedQuote:
    """收集流程产出的单条语录，包含 quote_id 和可选的 AI 评论。"""

    quote_id: str
    comment: Optional[str] = None


# ------------------------------------------------------------------ #
#  LLM 筛选器 Protocol（可选依赖）
# ------------------------------------------------------------------ #


class MessageFilter(Protocol):
    """
    消息筛选器协议。

    实现者负责从一组消息中筛选出值得保存为语录的内容。
    默认实现可以是 LLM 筛选，也可以是基于规则的筛选。
    """

    async def filter_messages(
        self,
        messages: Sequence[tuple[str, str, str]],
        group_id: str,
    ) -> list[SelectedQuote]:
        """
        从消息列表中筛选出值得保存的语录。

        Args:
            messages: ``[(msg_id, display_name, content), ...]``
            group_id: 群号。

        Returns:
            筛选出的语录列表。
        """
        ...


# ------------------------------------------------------------------ #
#  基于键的非阻塞锁（迁移自 lock_service.py）
# ------------------------------------------------------------------ #


class CollectionLockError(Exception):
    """当尝试获取一个已被持有的收集锁时抛出。"""

    pass


class _KeyedLock:
    """基于键的非阻塞锁，同一键重复获取会立即失败。"""

    def __init__(self) -> None:
        self._locks: dict[str, str] = {}

    def is_locked(self, key: str) -> bool:
        return key in self._locks

    def acquire(self, key: str, msg: str = "") -> None:
        if key in self._locks:
            raise CollectionLockError(
                self._locks[key] or f"群 {key} 的收集锁已被持有"
            )
        self._locks[key] = msg

    def release(self, key: str) -> None:
        self._locks.pop(key, None)


# ------------------------------------------------------------------ #
#  QuoteCollectionService
# ------------------------------------------------------------------ #


class QuoteCollectionService:
    """
    语录收集领域服务。

    职责：
    1. 管理消息收集队列（入队 / 计数 / 清空）
    2. 判断是否达到收集阈值
    3. 执行收集流程：取出队列消息 → 筛选 → 保存为语录
    4. 提供收集锁，防止同一群组并发收集
    """

    def __init__(
        self,
        msg_queue_repo: MsgQueueRepository,
        quote_write_service: QuoteWriteService,
        user_service: UserService,
        group_service: GroupService,
        message_filter: Optional[MessageFilter] = None,
    ) -> None:
        self._msg_queue_repo = msg_queue_repo
        self._quote_write_service = quote_write_service
        self._user_service = user_service
        self._group_service = group_service
        self._message_filter = message_filter
        self._lock = _KeyedLock()

    # ------------------------------------------------------------------ #
    #  队列管理
    # ------------------------------------------------------------------ #

    async def enqueue_message(
        self,
        group_id: str,
        msg_id: str,
        user_id: str,
        content: str,
    ) -> None:
        """
        将消息加入收集队列。

        同时确保用户和群组记录存在。

        Args:
            group_id: 群号。
            msg_id: 消息 ID。
            user_id: 发送者 QQ 号。
            content: 消息文本内容。
        """
        # 确保用户存在
        await self._user_service.get_or_create_user(user_id)

        # 入队
        await self._msg_queue_repo.create_msg(
            msg_id=msg_id,
            group_id=group_id,
            qq_id=user_id,
            content=content.strip(),
        )
        logger.debug(
            "消息已入队: group=%s, msg_id=%s, user=%s",
            group_id, msg_id, user_id,
        )

    async def get_queue_count(self, group_id: str) -> int:
        """获取指定群组的队列消息数。"""
        return await self._msg_queue_repo.count_msgs_by_group(group_id)

    async def should_trigger_collection(
        self, group_id: str, threshold: int
    ) -> bool:
        """
        检查队列消息数是否达到收集阈值。

        Args:
            group_id: 群号。
            threshold: 触发收集的消息数阈值。

        Returns:
            ``True`` 表示已达到阈值，应触发收集。
        """
        count = await self.get_queue_count(group_id)
        return count >= threshold

    async def clear_queue(self, group_id: str) -> None:
        """清空指定群组的消息队列。"""
        await self._msg_queue_repo.clear_group_queue(group_id)
        logger.info("队列已清空: group=%s", group_id)

    async def get_queue_messages(
        self, group_id: str, *, limit: Optional[int] = None
    ) -> Sequence[MsgQueue]:
        """
        获取队列中的消息列表。

        Args:
            group_id: 群号。
            limit: 最多返回条数，``None`` 表示全部。

        Returns:
            消息列表（按时间升序）。
        """
        return await self._msg_queue_repo.get_msgs_by_group(
            group_id, limit=limit
        )

    # ------------------------------------------------------------------ #
    #  收集锁
    # ------------------------------------------------------------------ #

    def is_collecting(self, group_id: str) -> bool:
        """检查指定群组是否正在收集中。"""
        return self._lock.is_locked(group_id)

    def acquire_lock(self, group_id: str) -> None:
        """
        获取收集锁。

        Raises:
            CollectionLockError: 锁已被持有。
        """
        self._lock.acquire(group_id, f"群 {group_id} 正在收集中，请稍后再试")

    def release_lock(self, group_id: str) -> None:
        """释放收集锁。"""
        self._lock.release(group_id)

    # ------------------------------------------------------------------ #
    #  收集流程
    # ------------------------------------------------------------------ #

    async def collect_and_save(
        self,
        group_id: str,
        *,
        limit: Optional[int] = None,
        allow_duplicate: bool = True,
    ) -> list[CollectedQuote]:
        """
        执行收集流程：从队列取出消息 → 筛选 → 保存为语录。

        Args:
            group_id: 群号。
            limit: 从队列取出的最大消息数。
            allow_duplicate: 是否允许重复语录。

        Returns:
            收集结果列表，每项包含 quote_id 和可选的 AI 评论。

        Raises:
            CollectionLockError: 群组正在收集中。
            ValidationException: 队列为空。
        """
        self.acquire_lock(group_id)
        try:
            return await self._do_collect(
                group_id,
                limit=limit,
                allow_duplicate=allow_duplicate,
            )
        finally:
            self.release_lock(group_id)

    async def _do_collect(
        self,
        group_id: str,
        *,
        limit: Optional[int] = None,
        allow_duplicate: bool = True,
    ) -> list[CollectedQuote]:
        """收集流程内部实现。"""
        # 1. 取出队列消息
        messages = await self._msg_queue_repo.get_msgs_by_group(
            group_id, limit=limit
        )
        if not messages:
            raise ValidationException("消息队列为空，无法执行收集")

        # 2. 筛选
        selected = await self._select_quotes(messages, group_id)
        if not selected:
            logger.info("收集完成但无筛选结果: group=%s", group_id)
            return []

        # 3. 保存
        collected: list[CollectedQuote] = []
        for item in selected:
            # 查找原始消息获取作者信息
            source_msg = await self._msg_queue_repo.get_msg_by_id(item.msg_id)
            if source_msg is None:
                logger.warning("消息数据未找到: msg_id=%s", item.msg_id)
                continue

            author_id = source_msg.qq_id
            content = item.content

            # 去重检查
            if not allow_duplicate:
                from ..database.repositories.quote_repository import (
                    QuoteRepository,
                )

                # 通过 quote_write_service 内部的 repo 检查
                # 这里直接跳过重复的
                exists = await self._quote_write_service._quote_repo.check_quote_exists_by_author_content(
                    author_id, content
                )
                if exists:
                    logger.debug(
                        "跳过重复语录: author=%s, content=%s",
                        author_id, content[:30],
                    )
                    continue

            try:
                quote_id = await self._quote_write_service.add_quote(
                    group_id=group_id,
                    author_id=author_id,
                    content=content,
                )
                comment = item.comment if item.comment else None
                collected.append(CollectedQuote(
                    quote_id=quote_id,
                    comment=comment,
                ))
            except Exception:
                logger.warning(
                    "保存语录失败: msg_id=%s", item.msg_id, exc_info=True
                )

        logger.info(
            "收集完成: group=%s, saved=%d/%d",
            group_id, len(collected), len(selected),
        )
        return collected

    async def _select_quotes(
        self,
        messages: Sequence[MsgQueue],
        group_id: str,
    ) -> list[SelectedQuote]:
        """
        筛选消息。

        如果注入了 ``MessageFilter``，使用它进行筛选；
        否则将所有消息原样返回（即不做筛选）。
        """
        if self._message_filter is not None:
            # 构建 (msg_id, display_name, content) 元组
            msg_tuples: list[tuple[str, str, str]] = []
            for msg in messages:
                display_name = await self._user_service.get_display_name(
                    msg.qq_id, group_id
                )
                msg_tuples.append((msg.msg_id, display_name, msg.content))

            return await self._message_filter.filter_messages(
                msg_tuples, group_id
            )

        # 无筛选器时，所有消息都作为候选
        return [
            SelectedQuote(msg_id=msg.msg_id, content=msg.content)
            for msg in messages
        ]
