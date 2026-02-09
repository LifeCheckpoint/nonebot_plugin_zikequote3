"""
GroupMemberRepository —— 群成员关系数据仓储，对应原 ``GroupMemberDAO``。

注意：group_members 表使用联合主键 (group_id, qq_id)。
覆盖原 DAO 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import delete, func, select

from ..models.group_members import GroupMember, GroupMemberCreate
from ..sa.models.group_member import GroupMemberModel
from .base import BaseRepository


class GroupMemberRepository(BaseRepository[GroupMemberModel, GroupMemberCreate, GroupMember]):
    """群成员关系 Repository（联合主键）。"""

    model_class = GroupMemberModel

    # ---- 创建 ----

    async def create_group_member(self, group_id: str, qq_id: str) -> GroupMember:
        """创建新群成员关系并返回 DTO。"""
        dto = GroupMemberCreate(group_id=group_id, qq_id=qq_id)
        return await self.create(dto)

    async def update_or_create_member(self, group_id: str, qq_id: str) -> GroupMember:
        """更新或创建群成员关系（不存在则创建）。"""
        instance = await self._session.get(GroupMemberModel, (group_id, qq_id))
        if instance:
            return instance.to_dto()
        return await self.create_group_member(group_id, qq_id)

    # ---- 查询 ----

    async def get_group_member(self, group_id: str, qq_id: str) -> Optional[GroupMember]:
        """根据群号和 QQ 号获取群成员。"""
        instance = await self._session.get(GroupMemberModel, (group_id, qq_id))
        return instance.to_dto() if instance else None

    async def group_member_exists(self, group_id: str, qq_id: str) -> bool:
        """检查群成员关系是否存在。"""
        instance = await self._session.get(GroupMemberModel, (group_id, qq_id))
        return instance is not None

    # 兼容旧 DAO 的别名
    is_group_member_exists = group_member_exists

    async def get_members_by_group(self, group_id: str) -> Sequence[GroupMember]:
        """获取群组的所有成员。"""
        stmt = select(GroupMemberModel).where(GroupMemberModel.group_id == group_id)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_groups_by_user(self, qq_id: str) -> Sequence[GroupMember]:
        """获取用户加入的所有群组。"""
        stmt = select(GroupMemberModel).where(GroupMemberModel.qq_id == qq_id)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_members_by_group(self, group_id: str) -> int:
        """统计群组成员数量。"""
        stmt = (
            select(func.count())
            .select_from(GroupMemberModel)
            .where(GroupMemberModel.group_id == group_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_groups_by_user(self, qq_id: str) -> int:
        """统计用户加入的群组数量。"""
        stmt = (
            select(func.count())
            .select_from(GroupMemberModel)
            .where(GroupMemberModel.qq_id == qq_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ---- 删除 ----

    async def delete_group_member(self, group_id: str, qq_id: str) -> bool:
        """删除群成员关系。"""
        instance = await self._session.get(GroupMemberModel, (group_id, qq_id))
        if instance:
            await self._session.delete(instance)
            await self._session.flush()
            return True
        return False

    async def delete_all_members_by_group(self, group_id: str) -> None:
        """删除群组的所有成员关系。"""
        stmt = delete(GroupMemberModel).where(GroupMemberModel.group_id == group_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def delete_all_groups_by_user(self, qq_id: str) -> None:
        """删除用户的所有群组关系。"""
        stmt = delete(GroupMemberModel).where(GroupMemberModel.qq_id == qq_id)
        await self._session.execute(stmt)
        await self._session.flush()

    # ---- 批量操作 ----

    async def batch_add_members(self, group_id: str, qq_ids: list[str]) -> bool:
        """批量添加群成员（已存在的跳过）。"""
        if not qq_ids:
            return True
        for qq_id in qq_ids:
            existing = await self._session.get(GroupMemberModel, (group_id, qq_id))
            if not existing:
                self._session.add(GroupMemberModel(group_id=group_id, qq_id=qq_id))
        await self._session.flush()
        return True

    async def batch_remove_members(self, group_id: str, qq_ids: list[str]) -> bool:
        """批量移除群成员。"""
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
