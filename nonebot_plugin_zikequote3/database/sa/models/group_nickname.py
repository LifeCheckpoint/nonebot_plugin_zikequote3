"""
ORM 模型：group_nicknames 表。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .group import GroupModel
    from .user import UserModel


class GroupNicknameModel(Base):
    """群名片 ORM 模型，对应 ``group_nicknames`` 表。"""

    __tablename__ = "group_nicknames"

    # schema.sql 中 group_nicknames 没有显式主键，
    # 但 ORM 要求主键，因此添加自增 id 作为代理主键。
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qq_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.qq_id"), nullable=False
    )
    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.group_id"), nullable=False
    )
    current_using: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # ---- relationships ----
    group: Mapped[GroupModel] = relationship(back_populates="nicknames")
    user: Mapped[UserModel] = relationship()

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``GroupNickname``。"""
        from ...models.group_nicknames import GroupNickname

        return GroupNickname(
            qq_id=self.qq_id,
            group_id=self.group_id,
            current_using=self.current_using,
            name=self.name,
        )

    @classmethod
    def from_create_dto(cls, dto) -> GroupNicknameModel:
        """从 Pydantic ``GroupNicknameCreate`` DTO 创建 ORM 实例。"""
        return cls(
            qq_id=dto.qq_id,
            group_id=dto.group_id,
            current_using=dto.current_using,
            name=dto.name,
        )
