"""
ORM 模型：msgs_queue 表。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from nonebot_plugin_zikequote3.database.sa.base import Base


class MsgQueueModel(Base):
    """消息队列 ORM 模型，对应 ``msgs_queue`` 表。"""

    __tablename__ = "msgs_queue"

    msg_id: Mapped[str] = mapped_column(String, primary_key=True)
    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.group_id", ondelete="CASCADE"), nullable=False
    )
    qq_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.qq_id", ondelete="CASCADE"), nullable=False
    )
    time_stamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``MsgQueue``。"""
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
        """从 Pydantic ``MsgQueueCreate`` DTO 创建 ORM 实例。"""
        return cls(
            msg_id=dto.msg_id,
            group_id=dto.group_id,
            qq_id=dto.qq_id,
            content=dto.content,
        )
