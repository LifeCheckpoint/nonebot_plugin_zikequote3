"""
GroupNicknameRepository —— 群名片数据仓储，对应原 ``GroupNicknameDAO``。

覆盖原 DAO 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from sqlalchemy import delete, func, select, update

from ..models.group_nicknames import GroupNickname, GroupNicknameCreate
from ..sa.models.group_nickname import GroupNicknameModel
from .base import BaseRepository


class GroupNicknameRepository(BaseRepository[GroupNicknameModel, GroupNicknameCreate, GroupNickname]):
    """群名片 Repository。"""

    model_class = GroupNicknameModel

    # ---- 创建 ----

    async def add_group_nickname(
        self, qq_id: str, group_id: str, current_using: bool, name: str
    ) -> GroupNickname:
        """添加群名片并返回 DTO。"""
        dto = GroupNicknameCreate(
            qq_id=qq_id, group_id=group_id, current_using=current_using, name=name
        )
        return await self.create(dto)

    # ---- 查询 ----

    async def get_current_group_nickname(self, qq_id: str, group_id: str) -> Optional[str]:
        """获取用户在群组中当前使用的名片名称，不存在返回 None。"""
        stmt = select(GroupNicknameModel).where(
            GroupNicknameModel.qq_id == qq_id,
            GroupNicknameModel.group_id == group_id,
            GroupNicknameModel.current_using == True,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return row.name if row else None

    async def get_all_group_nicknames(self, qq_id: str, group_id: str) -> Sequence[GroupNickname]:
        """获取用户在群组中的所有名片记录。"""
        stmt = select(GroupNicknameModel).where(
            GroupNicknameModel.qq_id == qq_id,
            GroupNicknameModel.group_id == group_id,
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_nicknames_by_group(self, group_id: str) -> Sequence[GroupNickname]:
        """获取群组中的所有名片记录。"""
        stmt = select(GroupNicknameModel).where(GroupNicknameModel.group_id == group_id)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_user_all_group_nicknames(self, qq_id: str) -> Sequence[GroupNickname]:
        """获取用户在所有群组中的名片记录。"""
        stmt = select(GroupNicknameModel).where(GroupNicknameModel.qq_id == qq_id)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def search_users_by_nickname_in_group(
        self, name_pattern: str, group_id: str
    ) -> Sequence[GroupNickname]:
        """通过昵称模式搜索群组内用户（LIKE 匹配）。"""
        stmt = select(GroupNicknameModel).where(
            GroupNicknameModel.name.like(name_pattern),
            GroupNicknameModel.group_id == group_id,
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_group_nickname_statistics(self, group_id: str) -> Dict[str, Any]:
        """获取群组名片统计信息。"""
        stmt = (
            select(
                func.count().label("total_nicknames"),
                func.count(func.distinct(GroupNicknameModel.qq_id)).label("users_with_nicknames"),
                func.count(
                    func.nullif(GroupNicknameModel.current_using, False)
                ).label("current_nicknames"),
            )
            .select_from(GroupNicknameModel)
            .where(GroupNicknameModel.group_id == group_id)
        )
        result = await self._session.execute(stmt)
        row = result.one()
        return {
            "total_nicknames": row.total_nicknames,
            "users_with_nicknames": row.users_with_nicknames,
            "current_nicknames": row.current_nicknames,
        }

    # ---- 更新 ----

    async def set_current_group_nickname(self, qq_id: str, group_id: str, name: str) -> bool:
        """设置用户在群组中的当前名片（先取消该群组中所有 current_using，再设置目标；若不存在则创建）。"""
        # 1. 取消该用户在该群组的所有 current_using
        stmt_clear = (
            update(GroupNicknameModel)
            .where(
                GroupNicknameModel.qq_id == qq_id,
                GroupNicknameModel.group_id == group_id,
            )
            .values(current_using=False)
        )
        await self._session.execute(stmt_clear)

        # 2. 设置目标名片为 current_using
        stmt_set = (
            update(GroupNicknameModel)
            .where(
                GroupNicknameModel.qq_id == qq_id,
                GroupNicknameModel.group_id == group_id,
                GroupNicknameModel.name == name,
            )
            .values(current_using=True)
        )
        result = await self._session.execute(stmt_set)

        # 3. 若目标名片不存在，则创建
        if result.rowcount == 0:  # type: ignore[union-attr]
            instance = GroupNicknameModel(
                qq_id=qq_id, group_id=group_id, current_using=True, name=name
            )
            self._session.add(instance)

        await self._session.flush()
        return True

    # ---- 删除 ----

    async def remove_group_nickname(self, qq_id: str, group_id: str, name: str) -> bool:
        """删除指定群名片，返回是否成功。"""
        stmt = select(GroupNicknameModel).where(
            GroupNicknameModel.qq_id == qq_id,
            GroupNicknameModel.group_id == group_id,
            GroupNicknameModel.name == name,
        )
        result = await self._session.execute(stmt)
        instance = result.scalars().first()
        if instance:
            await self._session.delete(instance)
            await self._session.flush()
            return True
        return False

    async def clear_user_group_nicknames(self, qq_id: str, group_id: str) -> bool:
        """清空用户在指定群组中的所有名片。"""
        stmt = delete(GroupNicknameModel).where(
            GroupNicknameModel.qq_id == qq_id,
            GroupNicknameModel.group_id == group_id,
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return True

    async def clear_group_all_nicknames(self, group_id: str) -> bool:
        """清空群组中所有用户的名片。"""
        stmt = delete(GroupNicknameModel).where(GroupNicknameModel.group_id == group_id)
        await self._session.execute(stmt)
        await self._session.flush()
        return True
