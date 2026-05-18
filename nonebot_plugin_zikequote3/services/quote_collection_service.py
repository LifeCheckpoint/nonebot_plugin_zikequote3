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
from nonebot import logger
import random
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Optional, Protocol, Sequence

from ..database.models.msgs_queue import MsgQueue
from ..database.repositories.msg_queue_repository import MsgQueueRepository
from ..exceptions import OperationError, ValidationException
from .group_service import GroupService
from .quote_write_service import QuoteWriteService
from .review_service import AUTHOR_AI, ReviewService
from .user_service import UserService

# ------------------------------------------------------------------ #
#  LLM 筛选结果数据类
# ------------------------------------------------------------------ #

class SelectedQuote:
    """
    LLM 筛选出的单条语录。

    :param msg_id: 消息 ID
    :type msg_id: str
    :param content: 语录文本内容
    :type content: str
    :param comment: AI 评论，默认为空字符串
    :type comment: str
    :param quote_id: 语录 ID（可选）
    :type quote_id: Optional[str]
    """

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

        :param messages: ``[(msg_id, display_name, content), ...]``
        :type messages: Sequence[tuple[str, str, str]]
        :param group_id: 群号
        :type group_id: str
        :returns: 筛选出的语录列表
        :rtype: list[SelectedQuote]
        """
        ...

# ------------------------------------------------------------------ #
#  基于键的非阻塞锁（迁移自 lock_service.py）
# ------------------------------------------------------------------ #

class CollectionLockError(OperationError):
    """当尝试获取一个已被持有的收集锁时抛出。"""


class CollectionLockManager:
    """APP 级共享收集锁管理器。"""

    def __init__(self) -> None:
        self._locks: dict[str, str] = {}

    def is_locked(self, key: str) -> bool:
        """
        检查指定键是否已被锁定。

        :param key: 锁键
        :type key: str
        :returns: 是否已锁定
        :rtype: bool
        """
        return key in self._locks

    def acquire(self, key: str, msg: str = "") -> None:
        """
        获取锁，若已被持有则抛出异常。

        :param key: 锁键
        :type key: str
        :param msg: 锁定时的提示消息
        :type msg: str
        :raises CollectionLockError: 锁已被持有
        """
        if key in self._locks:
            raise CollectionLockError(
                self._locks[key] or f"群 {key} 的收集锁已被持有"
            )
        self._locks[key] = msg

    def release(self, key: str) -> None:
        """
        释放锁。

        :param key: 锁键
        :type key: str
        """
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

    :param msg_queue_repo: 消息队列仓储实例
    :type msg_queue_repo: MsgQueueRepository
    :param quote_write_service: 语录写入服务实例
    :type quote_write_service: QuoteWriteService
    :param user_service: 用户服务实例
    :type user_service: UserService
    :param group_service: 群组服务实例
    :type group_service: GroupService
    :param message_filter: 消息筛选器（可选）
    :type message_filter: Optional[MessageFilter]
    """

    def __init__(
        self,
        msg_queue_repo: MsgQueueRepository,
        quote_write_service: QuoteWriteService,
        user_service: UserService,
        group_service: GroupService,
        review_service: ReviewService,
        lock_manager: CollectionLockManager,
        message_filter: Optional[MessageFilter] = None,
    ) -> None:
        self._msg_queue_repo = msg_queue_repo
        self._quote_write_service = quote_write_service
        self._user_service = user_service
        self._group_service = group_service
        self._review_service = review_service
        self._lock_manager = lock_manager
        self._message_filter = message_filter

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

        :param group_id: 群号
        :type group_id: str
        :param msg_id: 消息 ID
        :type msg_id: str
        :param user_id: 发送者 QQ 号
        :type user_id: str
        :param content: 消息文本内容
        :type content: str
        """
        # 确保用户存在
        await self._user_service.get_or_create_user(user_id)

        content = content.strip()
        if not content:
            return

        # 入队
        await self._msg_queue_repo.create_msg(
            msg_id=msg_id,
            group_id=group_id,
            qq_id=user_id,
            content=content,
        )
        logger.debug(
            "消息已入队: group={}, msg_id={}, user={}",
            group_id, msg_id, user_id,
        )

    async def get_queue_count(self, group_id: str) -> int:
        """
        获取指定群组的队列消息数。

        :param group_id: 群号
        :type group_id: str
        :returns: 队列消息数
        :rtype: int
        """
        return await self._msg_queue_repo.count_msgs_by_group(group_id)

    async def should_trigger_collection(
        self, group_id: str, threshold: int
    ) -> bool:
        """
        检查队列消息数是否达到收集阈值。

        :param group_id: 群号
        :type group_id: str
        :param threshold: 触发收集的消息数阈值
        :type threshold: int
        :returns: ``True`` 表示已达到阈值，应触发收集
        :rtype: bool
        """
        count = await self.get_queue_count(group_id)
        return count >= threshold

    async def clear_queue(self, group_id: str) -> None:
        """
        清空指定群组的消息队列。

        :param group_id: 群号
        :type group_id: str
        """
        await self._msg_queue_repo.clear_group_queue(group_id)
        logger.info("队列已清空: group={}", group_id)

    async def get_queue_messages(
        self, group_id: str, *, limit: Optional[int] = None
    ) -> Sequence[MsgQueue]:
        """
        获取队列中的消息列表。

        :param group_id: 群号
        :type group_id: str
        :param limit: 最多返回条数，``None`` 表示全部
        :type limit: Optional[int]
        :returns: 消息列表（按时间升序）
        :rtype: Sequence[MsgQueue]
        """
        return await self._msg_queue_repo.get_msgs_by_group(
            group_id, limit=limit
        )

    # ------------------------------------------------------------------ #
    #  收集锁
    # ------------------------------------------------------------------ #

    def is_collecting(self, group_id: str) -> bool:
        """
        检查指定群组是否正在收集中。

        :param group_id: 群号
        :type group_id: str
        :returns: 是否正在收集
        :rtype: bool
        """
        return self._lock_manager.is_locked(group_id)

    def acquire_lock(self, group_id: str) -> None:
        """
        获取收集锁。

        :param group_id: 群号
        :type group_id: str
        :raises CollectionLockError: 锁已被持有
        """
        self._lock_manager.acquire(
            group_id, f"群 {group_id} 正在收集中，请稍后再试"
        )

    def release_lock(self, group_id: str) -> None:
        """
        释放收集锁。

        :param group_id: 群号
        :type group_id: str
        """
        self._lock_manager.release(group_id)

    async def _run_with_lock(
        self,
        group_id: str,
        action: Callable[[], Coroutine[Any, Any, list[CollectedQuote]]],
    ) -> list[CollectedQuote]:
        """在共享收集锁保护下执行收集相关动作。"""
        self.acquire_lock(group_id)
        try:
            return await action()
        finally:
            self.release_lock(group_id)

    # ------------------------------------------------------------------ #
    #  收集流程
    # ------------------------------------------------------------------ #

    async def collect_and_save(
        self,
        group_id: str,
        *,
        allow_duplicate: bool,
        limit: Optional[int] = None,
    ) -> list[CollectedQuote]:
        """
        执行收集流程：从队列取出消息 → 筛选 → 保存为语录。

        :param group_id: 群号
        :type group_id: str
        :param limit: 从队列取出的最大消息数
        :type limit: Optional[int]
        :param allow_duplicate: 是否允许重复语录
        :type allow_duplicate: bool
        :returns: 收集结果列表，每项包含 quote_id 和可选的 AI 评论
        :rtype: list[CollectedQuote]
        :raises CollectionLockError: 群组正在收集中
        :raises ValidationException: 队列为空
        """

        async def _action() -> list[CollectedQuote]:
            return await self._do_collect(
                group_id,
                limit=limit,
                allow_duplicate=allow_duplicate,
            )

        return await self._run_with_lock(group_id, _action)

    async def collect_and_finalize(
        self,
        group_id: str,
        *,
        allow_duplicate: bool,
        limit: Optional[int] = None,
    ) -> list[CollectedQuote]:
        """
        执行完整收集闭环：保存语录 → 追加 AI 评论 → 清理队列。

        若任一步骤失败，则异常向上抛出，由 REQUEST 级事务统一回滚，
        从而避免留下“已保存语录、未清队列”的半成功状态。
        """

        async def _action() -> list[CollectedQuote]:
            collected = await self._do_collect(
                group_id,
                limit=limit,
                allow_duplicate=allow_duplicate,
            )
            await self._append_ai_reviews(collected)
            await self.clear_queue(group_id)
            return collected

        return await self._run_with_lock(group_id, _action)

    async def _do_collect(
        self,
        group_id: str,
        *,
        allow_duplicate: bool,
        limit: Optional[int] = None,
    ) -> list[CollectedQuote]:
        """
        收集流程内部实现。

        :param group_id: 群号
        :type group_id: str
        :param limit: 从队列取出的最大消息数
        :type limit: Optional[int]
        :param allow_duplicate: 是否允许重复语录
        :type allow_duplicate: bool
        :returns: 收集结果列表
        :rtype: list[CollectedQuote]
        :raises ValidationException: 队列为空
        """
        # 1. 取出队列消息
        messages = await self._msg_queue_repo.get_msgs_by_group(
            group_id, limit=limit
        )
        if not messages:
            raise ValidationException("消息队列为空，无法执行收集")

        logger.info(
            "开始收集 (group={}): 队列中 {} 条消息",
            group_id, len(messages),
        )

        # 2. 筛选
        selected = await self._select_quotes(messages, group_id)
        if not selected:
            logger.info("收集完成但无筛选结果: group={}", group_id)
            return []

        # 3. 保存
        collected: list[CollectedQuote] = []
        saved_details: list[tuple[str, str, str]] = []  # (quote_id, author_id, content)
        messages_by_id = {msg.msg_id: msg for msg in messages}
        for item in selected:
            source_msg = messages_by_id.get(item.msg_id)
            if source_msg is None:
                logger.warning("消息数据未找到: msg_id={}", item.msg_id)
                continue

            author_id = source_msg.qq_id
            content = item.content

            # 去重检查
            if not allow_duplicate:
                exists = await self._quote_write_service.check_quote_exists(
                    author_id, content
                )
                if exists:
                    logger.debug(
                        "跳过重复语录: author={}, content={}",
                        author_id, content[:30],
                    )
                    continue

            quote_id = await self._quote_write_service.add_quote(
                group_id=group_id,
                author_id=author_id,
                content=content,
            )
            comment = item.comment.strip() if item.comment and item.comment.strip() else None
            collected.append(CollectedQuote(
                quote_id=quote_id,
                comment=comment,
            ))
            saved_details.append((quote_id, author_id, content))

        if collected:
            detail_lines = "; ".join(
                f"[{qid}] user={aid} \"{ct[:50]}\""
                for qid, aid, ct in saved_details
            )
            logger.info(
                "收集完成 (group={}): 保存 {}/{} 条 — {}",
                group_id, len(collected), len(selected), detail_lines,
            )
        else:
            logger.info(
                "收集完成 (group={}): 筛选 {} 条但最终保存 0 条",
                group_id, len(selected),
            )
        return collected

    async def _append_ai_reviews(
        self,
        collected: Sequence[CollectedQuote],
    ) -> None:
        """为收集结果中的 AI 评论统一建档。"""
        for item in collected:
            if item.comment:
                await self._review_service.add_review(
                    quote_id=item.quote_id,
                    author_id=AUTHOR_AI,
                    content=item.comment,
                )

    async def _select_quotes(
        self,
        messages: Sequence[MsgQueue],
        group_id: str,
    ) -> list[SelectedQuote]:
        """
        筛选消息。

        如果注入了 ``MessageFilter``，使用它进行筛选；
        否则将所有消息原样返回（即不做筛选）。

        :param messages: 待筛选的消息列表
        :type messages: Sequence[MsgQueue]
        :param group_id: 群号
        :type group_id: str
        :returns: 筛选后的语录列表
        :rtype: list[SelectedQuote]
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
