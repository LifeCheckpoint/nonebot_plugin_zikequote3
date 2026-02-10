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
    """
    群成员关系 ORM 模型，对应 ``group_members`` 表（联合主键）。

    :param group_id: 群号，外键关联 ``groups.group_id``，联合主键之一
    :type group_id: str
    :param qq_id: QQ 号，外键关联 ``users.qq_id``，联合主键之一
    :type qq_id: str
    """

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
        """
        转换为 Pydantic Full DTO ``GroupMember``。

        :returns: 群成员关系 DTO 对象
        :rtype: GroupMember
        """
        from ...models.group_members import GroupMember

        return GroupMember(group_id=self.group_id, qq_id=self.qq_id)

    @classmethod
    def from_create_dto(cls, dto) -> GroupMemberModel:
        """
        从 Pydantic ``GroupMemberCreate`` DTO 创建 ORM 实例。

        :param dto: 创建群成员关系的 DTO
        :type dto: GroupMemberCreate
        :returns: 群成员关系 ORM 实例
        :rtype: GroupMemberModel
        """
        return cls(group_id=dto.group_id, qq_id=dto.qq_id)
