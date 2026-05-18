"""
MsgQueueRepository —— 消息队列数据仓储，对应原 ``MsgQueueDAO``。

同时处理 ``msgs_queue`` 和 ``queue_group_message_counts`` 两张表。
覆盖原 DAO 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy import delete, func, insert, select, update as sa_update

from ..models.msgs_queue import MsgQueue, MsgQueueCreate
from ..models.queue_group_message_counts import (
    QueueGroupMessageCount,
    QueueGroupMessageCountCreate,
)
from ..sa.models.msg_queue import MsgQueueModel
from ..sa.models.queue_count import QueueGroupMessageCountModel
from .base import BaseRepository


class MsgQueueRepository(BaseRepository[MsgQueueModel, MsgQueueCreate, MsgQueue]):
    """消息队列 Repository。

    同时管理 ``msgs_queue`` 和 ``queue_group_message_counts`` 两张表，
    对应原 ``MsgQueueDAO`` 的全部公开方法。
    """

    model_class = MsgQueueModel

    # ---- 创建 ----

    async def create_msg(
        self, msg_id: str, group_id: str, qq_id: str, content: str
    ) -> MsgQueue:
        """创建新的队列消息并返回 DTO。

        :param msg_id: 消息 ID。
        :type msg_id: str
        :param group_id: 群组 ID。
        :type group_id: str
        :param qq_id: 用户 QQ ID。
        :type qq_id: str
        :param content: 消息内容。
        :type content: str
        :returns: 创建后的消息 DTO。
        :rtype: MsgQueue
        """
        dto = MsgQueueCreate(msg_id=msg_id, group_id=group_id, qq_id=qq_id, content=content)
        return await self.create(dto)

    # ---- 查询 ----

    async def get_msg_by_id(self, msg_id: str) -> Optional[MsgQueue]:
        """根据消息 ID 获取消息。

        :param msg_id: 消息 ID。
        :type msg_id: str
        :returns: 消息 DTO，不存在时返回 ``None``。
        :rtype: Optional[MsgQueue]
        """
        return await self.get_by_id(msg_id)

    async def get_msgs_by_group(
        self, group_id: str, *, limit: Optional[int] = None, offset: int = 0
    ) -> Sequence[MsgQueue]:
        """获取群组消息列表（取最后 *limit* 条，结果按时间升序）。

        :param group_id: 群组 ID。
        :type group_id: str
        :param limit: 最大返回数量，``None`` 表示不限制。
        :type limit: Optional[int]
        :param offset: 分页偏移量。
        :type offset: int
        :returns: 消息 DTO 序列。
        :rtype: Sequence[MsgQueue]
        """
        if limit is not None:
            # 子查询：先按时间降序取最后 limit 条
            sub = (
                select(MsgQueueModel)
                .where(MsgQueueModel.group_id == group_id)
                .order_by(MsgQueueModel.time_stamp.desc())
                .limit(limit)
                .offset(offset)
                .subquery()
            )
            stmt = select(MsgQueueModel).join(
                sub, MsgQueueModel.msg_id == sub.c.msg_id
            ).order_by(MsgQueueModel.time_stamp.asc())
        else:
            stmt = (
                select(MsgQueueModel)
                .where(MsgQueueModel.group_id == group_id)
                .order_by(MsgQueueModel.time_stamp.asc())
            )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_msgs_by_user(
        self, qq_id: str, *, limit: Optional[int] = None, offset: int = 0
    ) -> Sequence[MsgQueue]:
        """根据用户获取消息列表（按时间升序）。

        :param qq_id: 用户 QQ ID。
        :type qq_id: str
        :param limit: 最大返回数量，``None`` 表示不限制。
        :type limit: Optional[int]
        :param offset: 分页偏移量。
        :type offset: int
        :returns: 消息 DTO 序列。
        :rtype: Sequence[MsgQueue]
        """
        stmt = (
            select(MsgQueueModel)
            .where(MsgQueueModel.qq_id == qq_id)
            .order_by(MsgQueueModel.time_stamp.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_recent_msgs_by_group(
        self, group_id: str, limit: int = 100
    ) -> Sequence[MsgQueue]:
        """获取群组最近的消息（按时间降序）。

        :param group_id: 群组 ID。
        :type group_id: str
        :param limit: 最大返回数量。
        :type limit: int
        :returns: 消息 DTO 序列。
        :rtype: Sequence[MsgQueue]
        """
        stmt = (
            select(MsgQueueModel)
            .where(MsgQueueModel.group_id == group_id)
            .order_by(MsgQueueModel.time_stamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_msgs_by_group(self, group_id: str) -> int:
        """统计群组消息数量。

        :param group_id: 群组 ID。
        :type group_id: str
        :returns: 消息数量。
        :rtype: int
        """
        stmt = (
            select(func.count())
            .select_from(MsgQueueModel)
            .where(MsgQueueModel.group_id == group_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ---- 删除 ----

    async def clear_group_queue(self, group_id: str) -> bool:
        """清空群组的消息队列。

        :param group_id: 群组 ID。
        :type group_id: str
        :returns: 始终返回 ``True``。
        :rtype: bool
        """
        stmt = delete(MsgQueueModel).where(MsgQueueModel.group_id == group_id)
        await self._session.execute(stmt)
        await self._session.flush()
        return True

    async def delete_old_msgs(self, days: int = 30) -> bool:
        """删除超过指定天数的旧消息。

        :param days: 保留天数，超过此天数的消息将被删除。
        :type days: int
        :returns: 始终返回 ``True``。
        :rtype: bool
        """
        cutoff = datetime.now() - timedelta(days=days)
        stmt = delete(MsgQueueModel).where(MsgQueueModel.time_stamp < cutoff)
        await self._session.execute(stmt)
        await self._session.flush()
        return True

    # ---- queue_group_message_counts 相关 ----

    async def get_queue_count(self, group_id: str) -> Optional[QueueGroupMessageCount]:
        """获取群组的队列消息计数记录。

        :param group_id: 群组 ID。
        :type group_id: str
        :returns: 计数 DTO，不存在时返回 ``None``。
        :rtype: Optional[QueueGroupMessageCount]
        """
        instance = await self._session.get(QueueGroupMessageCountModel, group_id)
        return instance.to_dto() if instance else None

    async def set_queue_count(self, group_id: str, message_count: int) -> QueueGroupMessageCount:
        """设置群组的队列消息计数（存在则更新，不存在则创建）。

        :param group_id: 群组 ID。
        :type group_id: str
        :param message_count: 目标计数值。
        :type message_count: int
        :returns: 更新/创建后的计数 DTO。
        :rtype: QueueGroupMessageCount
        """
        instance = await self._session.get(QueueGroupMessageCountModel, group_id)
        if instance:
            instance.message_count = message_count
        else:
            instance = QueueGroupMessageCountModel(
                group_id=group_id, message_count=message_count
            )
            self._session.add(instance)
        await self._session.flush()
        return instance.to_dto()

    async def increment_queue_count(self, group_id: str, delta: int = 1) -> QueueGroupMessageCount:
        """递增群组的队列消息计数。

        若记录不存在则以 *delta* 为初始值创建。

        :param group_id: 群组 ID。
        :type group_id: str
        :param delta: 递增量。
        :type delta: int
        :returns: 更新/创建后的计数 DTO。
        :rtype: QueueGroupMessageCount
        """
        stmt = (
            sa_update(QueueGroupMessageCountModel)
            .where(QueueGroupMessageCountModel.group_id == group_id)
            .values(message_count=QueueGroupMessageCountModel.message_count + delta)
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            stmt = insert(QueueGroupMessageCountModel).values(
                group_id=group_id, message_count=delta
            )
            await self._session.execute(stmt)
        await self._session.flush()
        instance = await self._session.get(QueueGroupMessageCountModel, group_id)
        return instance.to_dto()

    async def reset_queue_count(self, group_id: str) -> bool:
        """重置群组的队列消息计数为 0。

        :param group_id: 群组 ID。
        :type group_id: str
        :returns: 是否成功重置（记录存在时为 ``True``）。
        :rtype: bool
        """
        instance = await self._session.get(QueueGroupMessageCountModel, group_id)
        if instance:
            instance.message_count = 0
            await self._session.flush()
            return True
        return False
