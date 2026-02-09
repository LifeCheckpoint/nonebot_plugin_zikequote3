"""
ORM 模型：user_nicknames 表。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .user import UserModel


class UserNicknameModel(Base):
    """用户昵称 ORM 模型，对应 ``user_nicknames`` 表。"""

    __tablename__ = "user_nicknames"

    # schema.sql 中 user_nicknames 没有显式主键，
    # 但 ORM 要求主键，因此添加自增 id 作为代理主键。
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qq_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.qq_id"), nullable=False
    )
    current_using: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # ---- relationships ----
    user: Mapped[UserModel] = relationship(back_populates="nicknames")

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``UserNickname``。"""
        from ...models.user_nicknames import UserNickname

        return UserNickname(
            qq_id=self.qq_id,
            current_using=self.current_using,
            name=self.name,
        )

    @classmethod
    def from_create_dto(cls, dto) -> UserNicknameModel:
        """从 Pydantic ``UserNicknameCreate`` DTO 创建 ORM 实例。"""
        return cls(
            qq_id=dto.qq_id,
            current_using=dto.current_using,
            name=dto.name,
        )
