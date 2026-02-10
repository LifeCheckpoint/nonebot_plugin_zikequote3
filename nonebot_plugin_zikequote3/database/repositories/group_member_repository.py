"""
GroupMemberRepository —— 群成员关系数据仓储。

处理 ``group_members`` 表（联合主键 ``group_id``, ``qq_id``）的数据访问操作，
覆盖原 ``GroupMemberDAO`` 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import delete, func, select

from ..models.group_members import GroupMember, GroupMemberCreate
from ..sa.models.group_member import GroupMemberModel
from .base import BaseRepository


class GroupMemberRepository(BaseRepository[GroupMemberModel, GroupMemberCreate, GroupMember]):
    """
    群成员关系 Repository（联合主键）。

    :param session: 异步数据库会话
    :type session: AsyncSession
    """

    model_class = GroupMemberModel

    # ---- 创建 ----

    async def create_group_member(self, group_id: str, qq_id: str) -> GroupMember:
        """
        创建新群成员关系并返回 DTO。

        :param group_id: 群号
        :type group_id: str
        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 群成员关系 DTO
        :rtype: GroupMember
        """
        dto = GroupMemberCreate(group_id=group_id, qq_id=qq_id)
        return await self.create(dto)

    async def update_or_create_member(self, group_id: str, qq_id: str) -> GroupMember:
        """
        更新或创建群成员关系（不存在则创建）。

        :param group_id: 群号
        :type group_id: str
        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 群成员关系 DTO
        :rtype: GroupMember
        """
        instance = await self._session.get(GroupMemberModel, (group_id, qq_id))
        if instance:
            return instance.to_dto()
        return await self.create_group_member(group_id, qq_id)

    # ---- 查询 ----

    async def get_group_member(self, group_id: str, qq_id: str) -> Optional[GroupMember]:
        """
        根据群号和 QQ 号获取群成员。

        :param group_id: 群号
        :type group_id: str
        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 群成员关系 DTO，不存在时返回 ``None``
        :rtype: Optional[GroupMember]
        """
        instance = await self._session.get(GroupMemberModel, (group_id, qq_id))
        return instance.to_dto() if instance else None

    async def group_member_exists(self, group_id: str, qq_id: str) -> bool:
        """
        检查群成员关系是否存在。

        :param group_id: 群号
        :type group_id: str
        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 存在返回 ``True``
        :rtype: bool
        """
        instance = await self._session.get(GroupMemberModel, (group_id, qq_id))
        return instance is not None

    # 兼容旧 DAO 的别名
    is_group_member_exists = group_member_exists

    async def get_members_by_group(self, group_id: str) -> Sequence[GroupMember]:
        """
        获取群组的所有成员。

        :param group_id: 群号
        :type group_id: str
        :returns: 群成员关系 DTO 序列
        :rtype: Sequence[GroupMember]
        """
        stmt = select(GroupMemberModel).where(GroupMemberModel.group_id == group_id)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_groups_by_user(self, qq_id: str) -> Sequence[GroupMember]:
        """
        获取用户加入的所有群组。

        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 群成员关系 DTO 序列
        :rtype: Sequence[GroupMember]
        """
        stmt = select(GroupMemberModel).where(GroupMemberModel.qq_id == qq_id)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_members_by_group(self, group_id: str) -> int:
        """
        统计群组成员数量。

        :param group_id: 群号
        :type group_id: str
        :returns: 成员数量
        :rtype: int
        """
        stmt = (
            select(func.count())
            .select_from(GroupMemberModel)
            .where(GroupMemberModel.group_id == group_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_groups_by_user(self, qq_id: str) -> int:
        """
        统计用户加入的群组数量。

        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 群组数量
        :rtype: int
        """
        stmt = (
            select(func.count())
            .select_from(GroupMemberModel)
            .where(GroupMemberModel.qq_id == qq_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ---- 删除 ----

    async def delete_group_member(self, group_id: str, qq_id: str) -> bool:
        """
        删除群成员关系。

        :param group_id: 群号
        :type group_id: str
        :param qq_id: QQ 号
        :type qq_id: str
        :returns: 删除成功返回 ``True``
        :rtype: bool
        """
        instance = await self._session.get(GroupMemberModel, (group_id, qq_id))
        if instance:
            await self._session.delete(instance)
            await self._session.flush()
            return True
        return False

    async def delete_all_members_by_group(self, group_id: str) -> None:
        """
        删除群组的所有成员关系。

        :param group_id: 群号
        :type group_id: str
        """
        stmt = delete(GroupMemberModel).where(GroupMemberModel.group_id == group_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def delete_all_groups_by_user(self, qq_id: str) -> None:
        """
        删除用户的所有群组关系。

        :param qq_id: QQ 号
        :type qq_id: str
        """
        stmt = delete(GroupMemberModel).where(GroupMemberModel.qq_id == qq_id)
        await self._session.execute(stmt)
        await self._session.flush()

    # ---- 批量操作 ----

    async def batch_add_members(self, group_id: str, qq_ids: list[str]) -> bool:
        """
        批量添加群成员（已存在的跳过）。

        :param group_id: 群号
        :type group_id: str
        :param qq_ids: QQ 号列表
        :type qq_ids: list[str]
        :returns: 操作成功返回 ``True``
        :rtype: bool
        """
        if not qq_ids:
            return True
        for qq_id in qq_ids:
            existing = await self._session.get(GroupMemberModel, (group_id, qq_id))
            if not existing:
                self._session.add(GroupMemberModel(group_id=group_id, qq_id=qq_id))
        await self._session.flush()
        return True

    async def batch_remove_members(self, group_id: str, qq_ids: list[str]) -> bool:
        """
        批量移除群成员。

        :param group_id: 群号
        :type group_id: str
        :param qq_ids: QQ 号列表
        :type qq_ids: list[str]
        :returns: 操作成功返回 ``True``
        :rtype: bool
        """
        if not qq_ids:
            return True
        stmt = (
            delete(GroupMemberModel)
            .where(GroupMemberModel.group_id == group_id)
            .where(GroupMemberModel.qq_id.in_(qq_ids))
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return True
