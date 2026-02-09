"""
ORM 模型：group_members 表。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .group import GroupModel
    from .user import UserModel


class GroupMemberModel(Base):
    """群成员关系 ORM 模型，对应 ``group_members`` 表（联合主键）。"""

    __tablename__ = "group_members"

    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.group_id", ondelete="CASCADE"), primary_key=True
    )
    qq_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.qq_id", ondelete="CASCADE"), primary_key=True
    )

    # ---- relationships ----
    group: Mapped[GroupModel] = relationship(back_populates="members")
    user: Mapped[UserModel] = relationship(back_populates="group_memberships")

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``GroupMember``。"""
        from ...models.group_members import GroupMember

        return GroupMember(group_id=self.group_id, qq_id=self.qq_id)

    @classmethod
    def from_create_dto(cls, dto) -> GroupMemberModel:
        """从 Pydantic ``GroupMemberCreate`` DTO 创建 ORM 实例。"""
        return cls(group_id=dto.group_id, qq_id=dto.qq_id)
