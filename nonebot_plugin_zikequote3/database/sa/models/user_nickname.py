"""
ORM 模型：user_nicknames 表。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .user import UserModel


class UserNicknameModel(Base):
    """
    用户昵称 ORM 模型，对应 ``user_nicknames`` 表。

    使用 ``(qq_id, name)`` 联合主键，匹配旧表结构。

    :param qq_id: QQ 号，外键关联 ``users.qq_id``，联合主键之一
    :type qq_id: str
    :param name: 昵称，联合主键之一
    :type name: str
    :param current_using: 是否正在使用
    :type current_using: bool
    """

    __tablename__ = "user_nicknames"

    qq_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.qq_id"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String, primary_key=True)
    current_using: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ---- relationships ----
    user: Mapped[UserModel] = relationship(back_populates="nicknames")

    # ---- DTO 转换 ----
    def to_dto(self):
        """
        转换为 Pydantic Full DTO ``UserNickname``。

        :returns: 用户昵称 DTO 对象
        :rtype: UserNickname
        """
        from ...models.user_nicknames import UserNickname

        return UserNickname(
            qq_id=self.qq_id,
            current_using=self.current_using,
            name=self.name,
        )

    @classmethod
    def from_create_dto(cls, dto) -> UserNicknameModel:
        """
        从 Pydantic ``UserNicknameCreate`` DTO 创建 ORM 实例。

        :param dto: 创建用户昵称的 DTO
        :type dto: UserNicknameCreate
        :returns: 用户昵称 ORM 实例
        :rtype: UserNicknameModel
        """
        return cls(
            qq_id=dto.qq_id,
            current_using=dto.current_using,
            name=dto.name,
        )
