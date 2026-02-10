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
    """
    群名片 ORM 模型，对应 ``group_nicknames`` 表。

    :param id: 自增代理主键
    :type id: int
    :param qq_id: QQ 号，外键关联 ``users.qq_id``
    :type qq_id: str
    :param group_id: 群号，外键关联 ``groups.group_id``
    :type group_id: str
    :param current_using: 是否正在使用
    :type current_using: bool
    :param name: 群名片名称
    :type name: str
    """

    __tablename__ = "group_nicknames"

    # 原始表定义中无显式主键，ORM 要求主键，故添加自增 id 作为代理主键
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
        """
        转换为 Pydantic Full DTO ``GroupNickname``。

        :returns: 群名片 DTO 对象
        :rtype: GroupNickname
        """
        from ...models.group_nicknames import GroupNickname

        return GroupNickname(
            qq_id=self.qq_id,
            group_id=self.group_id,
            current_using=self.current_using,
            name=self.name,
        )

    @classmethod
    def from_create_dto(cls, dto) -> GroupNicknameModel:
        """
        从 Pydantic ``GroupNicknameCreate`` DTO 创建 ORM 实例。

        :param dto: 创建群名片的 DTO
        :type dto: GroupNicknameCreate
        :returns: 群名片 ORM 实例
        :rtype: GroupNicknameModel
        """
        return cls(
            qq_id=dto.qq_id,
            group_id=dto.group_id,
            current_using=dto.current_using,
            name=dto.name,
        )
