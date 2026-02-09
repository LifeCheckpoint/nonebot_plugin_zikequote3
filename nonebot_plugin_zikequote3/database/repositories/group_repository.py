"""
GroupRepository —— 群组数据仓储，对应原 ``GroupDAO``。

覆盖原 DAO 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select, update

from ..models.groups import Group, GroupCreate
from ..sa.models.group import GroupModel
from .base import BaseRepository


class GroupRepository(BaseRepository[GroupModel, GroupCreate, Group]):
    """群组 Repository。"""

    model_class = GroupModel

    # ---- 便捷创建 ----

    async def create_group(self, group_id: str, name: str) -> Group:
        """创建新群组并返回 DTO。"""
        dto = GroupCreate(group_id=group_id, name=name)
        return await self.create(dto)

    # ---- 查询 ----

    async def get_group_by_id(self, group_id: str) -> Optional[Group]:
        """根据群号获取群组。"""
        return await self.get_by_id(group_id)

    async def group_exists(self, group_id: str) -> bool:
        """检查群组是否存在。"""
        return await self.exists_by_id(group_id)

    async def find_groups_by_name(self, name: str) -> Sequence[Group]:
        """根据群名称精确查找群组。"""
        stmt = select(GroupModel).where(GroupModel.name == name)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def search_groups_by_name_like(self, name_pattern: str) -> Sequence[Group]:
        """根据群名称模糊搜索群组（支持 ``%`` 通配符）。"""
        stmt = select(GroupModel).where(GroupModel.name.like(name_pattern))
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_groups_with_name_containing(self, keyword: str) -> Sequence[Group]:
        """获取群名称包含指定关键词的群组。"""
        pattern = f"%{keyword}%"
        return await self.search_groups_by_name_like(pattern)

    async def get_groups_by_ids(self, group_ids: list[str]) -> Sequence[Group]:
        """根据群号列表批量获取群组。"""
        if not group_ids:
            return []
        stmt = select(GroupModel).where(GroupModel.group_id.in_(group_ids))
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_all_groups_ordered_by_name(self) -> Sequence[Group]:
        """获取所有群组，按名称排序。"""
        stmt = select(GroupModel).order_by(GroupModel.name)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_groups(self) -> int:
        """统计群组总数。"""
        return await self.count()

    # ---- 更新 ----

    async def update_group(self, group_id: str, name: str) -> bool:
        """更新群组名称。"""
        stmt = (
            update(GroupModel)
            .where(GroupModel.group_id == group_id)
            .values(name=name)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    async def update_or_create_group(self, group_id: str, name: str) -> Group:
        """更新或创建群组（不存在则创建，存在则更新名称）。"""
        instance = await self._session.get(GroupModel, group_id)
        if instance:
            instance.name = name
            await self._session.flush()
            return instance.to_dto()
        return await self.create_group(group_id, name)

    # ---- 删除 ----

    async def delete_group(self, group_id: str) -> bool:
        """删除群组。"""
        return await self.delete_by_id(group_id)

    # ---- 批量操作 ----

    async def batch_create_groups(self, groups: list[dict]) -> bool:
        """批量创建群组。每个 dict 包含 ``group_id`` 和 ``name``。"""
        if not groups:
            return True
        instances = [
            GroupModel(group_id=g["group_id"], name=g["name"])
            for g in groups
        ]
        self._session.add_all(instances)
        await self._session.flush()
        return True
