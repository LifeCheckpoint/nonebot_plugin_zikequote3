"""
ORM 模型：queue_group_message_counts 表。
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from nonebot_plugin_zikequote3.database.sa.base import Base


class QueueGroupMessageCountModel(Base):
    """
    群消息计数 ORM 模型，对应 ``queue_group_message_counts`` 表。

    :param group_id: 群号，外键关联 ``groups.group_id``，主键
    :type group_id: str
    :param message_count: 消息计数，默认为 0
    :type message_count: int
    """

    __tablename__ = "queue_group_message_counts"

    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.group_id", ondelete="CASCADE"), primary_key=True
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # ---- DTO 转换 ----
    def to_dto(self):
        """
        转换为 Pydantic Full DTO ``QueueGroupMessageCount``。

        :returns: 群消息计数 DTO 对象
        :rtype: QueueGroupMessageCount
        """
        from ...models.queue_group_message_counts import QueueGroupMessageCount

        return QueueGroupMessageCount(
            group_id=self.group_id,
            message_count=self.message_count,
        )

    @classmethod
    def from_create_dto(cls, dto) -> QueueGroupMessageCountModel:
        """
        从 Pydantic ``QueueGroupMessageCountCreate`` DTO 创建 ORM 实例。

        :param dto: 创建群消息计数的 DTO
        :type dto: QueueGroupMessageCountCreate
        :returns: 群消息计数 ORM 实例
        :rtype: QueueGroupMessageCountModel
        """
        return cls(
            group_id=dto.group_id,
            message_count=dto.message_count,
        )
