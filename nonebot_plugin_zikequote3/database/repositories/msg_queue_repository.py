"""
MsgQueueRepository —— 消息队列数据仓储，对应原 ``MsgQueueDAO``。

同时处理 ``msgs_queue`` 和 ``queue_group_message_counts`` 两张表。
覆盖原 DAO 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy import delete, func, select

from ..models.msgs_queue import MsgQueue, MsgQueueCreate
from ..models.queue_group_message_counts import (
    QueueGroupMessageCount,
    QueueGroupMessageCountCreate,
)
from ..sa.models.msg_queue import MsgQueueModel
from ..sa.models.queue_count import QueueGroupMessageCountModel
from .base import BaseRepository


class MsgQueueRepository(BaseRepository[MsgQueueModel, MsgQueueCreate, MsgQueue]):
    """消息队列 Repository。"""

    model_class = MsgQueueModel

    # ---- 创建 ----

    async def create_msg(
        self, msg_id: str, group_id: str, qq_id: str, content: str
    ) -> MsgQueue:
        """创建新的队列消息并返回 DTO。"""
        dto = MsgQueueCreate(msg_id=msg_id, group_id=group_id, qq_id=qq_id, content=content)
        return await self.create(dto)

    # ---- 查询 ----

    async def get_msg_by_id(self, msg_id: str) -> Optional[MsgQueue]:
        """根据消息 ID 获取消息。"""
        return await self.get_by_id(msg_id)

    async def get_msgs_by_group(
        self, group_id: str, *, limit: Optional[int] = None, offset: int = 0
    ) -> Sequence[MsgQueue]:
        """获取群组消息列表（取最后 limit 条，结果按时间升序）。"""
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
        """根据用户获取消息列表（按时间升序）。"""
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
        """获取群组最近的消息（按时间降序）。"""
        stmt = (
            select(MsgQueueModel)
            .where(MsgQueueModel.group_id == group_id)
            .order_by(MsgQueueModel.time_stamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_msgs_by_group(self, group_id: str) -> int:
        """统计群组消息数量。"""
        stmt = (
            select(func.count())
            .select_from(MsgQueueModel)
            .where(MsgQueueModel.group_id == group_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ---- 删除 ----

    async def clear_group_queue(self, group_id: str) -> bool:
        """清空群组的消息队列。"""
        stmt = delete(MsgQueueModel).where(MsgQueueModel.group_id == group_id)
        await self._session.execute(stmt)
        await self._session.flush()
        return True

    async def delete_old_msgs(self, days: int = 30) -> bool:
        """删除超过指定天数的旧消息。"""
        cutoff = datetime.now() - timedelta(days=days)
        stmt = delete(MsgQueueModel).where(MsgQueueModel.time_stamp < cutoff)
        await self._session.execute(stmt)
        await self._session.flush()
        return True

    # ---- queue_group_message_counts 相关 ----

    async def get_queue_count(self, group_id: str) -> Optional[QueueGroupMessageCount]:
        """获取群组的队列消息计数记录。"""
        instance = await self._session.get(QueueGroupMessageCountModel, group_id)
        return instance.to_dto() if instance else None

    async def set_queue_count(self, group_id: str, message_count: int) -> QueueGroupMessageCount:
        """设置群组的队列消息计数（存在则更新，不存在则创建）。"""
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
        """递增群组的队列消息计数。"""
        instance = await self._session.get(QueueGroupMessageCountModel, group_id)
        if instance:
            instance.message_count += delta
        else:
            instance = QueueGroupMessageCountModel(
                group_id=group_id, message_count=delta
            )
            self._session.add(instance)
        await self._session.flush()
        return instance.to_dto()

    async def reset_queue_count(self, group_id: str) -> bool:
        """重置群组的队列消息计数为 0。"""
        instance = await self._session.get(QueueGroupMessageCountModel, group_id)
        if instance:
            instance.message_count = 0
            await self._session.flush()
            return True
        return False
