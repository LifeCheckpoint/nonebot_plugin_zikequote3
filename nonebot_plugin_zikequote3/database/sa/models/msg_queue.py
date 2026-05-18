"""
ORM 模型：msgs_queue 表。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nonebot_plugin_zikequote3.database.sa.base import Base


class MsgQueueModel(Base):
    """
    消息队列 ORM 模型，对应 ``msgs_queue`` 表。

    :param msg_id: 消息 ID，主键
    :type msg_id: str
    :param group_id: 群号，外键关联 ``groups.group_id``
    :type group_id: str
    :param qq_id: QQ 号，外键关联 ``users.qq_id``
    :type qq_id: str
    :param time_stamp: 消息时间，默认为当前时间
    :type time_stamp: datetime
    :param content: 消息内容
    :type content: str
    """

    __tablename__ = "msgs_queue"
    __table_args__ = (
        Index("ix_msgs_queue_group_id", "group_id"),
        Index("ix_msgs_queue_qq_id", "qq_id"),
        Index("ix_msgs_queue_time_stamp", "time_stamp"),
    )

    msg_id: Mapped[str] = mapped_column(String, primary_key=True)
    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.group_id", ondelete="CASCADE"), nullable=False
    )
    qq_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.qq_id", ondelete="CASCADE"), nullable=False
    )
    time_stamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ---- DTO 转换 ----
    def to_dto(self):
        """
        转换为 Pydantic Full DTO ``MsgQueue``。

        :returns: 消息队列 DTO 对象
        :rtype: MsgQueue
        """
        from ...models.msgs_queue import MsgQueue

        return MsgQueue(
            msg_id=self.msg_id,
            group_id=self.group_id,
            qq_id=self.qq_id,
            time_stamp=self.time_stamp,
            content=self.content,
        )

    @classmethod
    def from_create_dto(cls, dto) -> MsgQueueModel:
        """
        从 Pydantic ``MsgQueueCreate`` DTO 创建 ORM 实例。

        当 ``dto.time_stamp`` 为 ``None`` 时，依赖数据库列默认值 (``func.now()``)。

        :param dto: 创建消息的 DTO
        :type dto: MsgQueueCreate
        :returns: 消息队列 ORM 实例
        :rtype: MsgQueueModel
        """
        kwargs: dict = {
            "msg_id": dto.msg_id,
            "group_id": dto.group_id,
            "qq_id": dto.qq_id,
            "content": dto.content,
        }
        if getattr(dto, "time_stamp", None) is not None:
            kwargs["time_stamp"] = dto.time_stamp
        return cls(**kwargs)
