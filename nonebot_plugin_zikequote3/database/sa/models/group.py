"""
ORM 模型：groups 表。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .group_member import GroupMemberModel
    from .group_nickname import GroupNicknameModel


class GroupModel(Base):
    """群组 ORM 模型，对应 ``groups`` 表。"""

    __tablename__ = "groups"

    group_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # ---- relationships ----
    nicknames: Mapped[list[GroupNicknameModel]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )
    members: Mapped[list[GroupMemberModel]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``Group``。"""
        from ...models.groups import Group

        return Group(group_id=self.group_id, name=self.name)

    @classmethod
    def from_create_dto(cls, dto) -> GroupModel:
        """从 Pydantic ``GroupCreate`` DTO 创建 ORM 实例。"""
        return cls(group_id=dto.group_id, name=dto.name)
