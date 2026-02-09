"""
ORM 模型：users 表。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .group_member import GroupMemberModel
    from .user_nickname import UserNicknameModel


class UserModel(Base):
    """用户 ORM 模型，对应 ``users`` 表。"""

    __tablename__ = "users"

    qq_id: Mapped[str] = mapped_column(String, primary_key=True)
    avatar: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True, default=None)

    # ---- relationships ----
    nicknames: Mapped[list[UserNicknameModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    group_memberships: Mapped[list[GroupMemberModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``User``。"""
        from ...models.users import User

        return User(qq_id=self.qq_id, avatar=self.avatar)

    @classmethod
    def from_create_dto(cls, dto) -> UserModel:
        """从 Pydantic ``UserCreate`` DTO 创建 ORM 实例。"""
        return cls(qq_id=dto.qq_id, avatar=dto.avatar)
