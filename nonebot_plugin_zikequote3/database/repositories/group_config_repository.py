"""
GroupConfigRepository —— 群自定义配置数据仓储，对应原 ``GroupConfigsDAO``。

覆盖原 DAO 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select, update

from ..models.group_configs import GroupConfigs, GroupConfigsCreate
from ..sa.models.group_config import GroupConfigModel
from .base import BaseRepository


class GroupConfigRepository(BaseRepository[GroupConfigModel, GroupConfigsCreate, GroupConfigs]):
    """群自定义配置 Repository。"""

    model_class = GroupConfigModel

    # ---- 创建 ----

    async def create_group_config(self, group_id: str, toml_config: str) -> GroupConfigs:
        """创建群自定义配置并返回 DTO。"""
        dto = GroupConfigsCreate(group_id=group_id, toml_config=toml_config)
        return await self.create(dto)

    # ---- 查询 ----

    async def get_group_config_by_id(self, group_id: str) -> Optional[GroupConfigs]:
        """根据群号获取群自定义配置。"""
        return await self.get_by_id(group_id)

    async def group_config_exists(self, group_id: str) -> bool:
        """检查群自定义配置是否存在。"""
        return await self.exists_by_id(group_id)

    async def get_toml_config_by_group_id(self, group_id: str) -> Optional[str]:
        """根据群号获取 TOML 配置内容。"""
        instance = await self._session.get(GroupConfigModel, group_id)
        return instance.toml_config if instance else None

    async def get_group_configs_by_ids(self, group_ids: list[str]) -> Sequence[GroupConfigs]:
        """根据群号列表批量获取群自定义配置。"""
        if not group_ids:
            return []
        stmt = select(GroupConfigModel).where(GroupConfigModel.group_id.in_(group_ids))
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_all_group_configs(self) -> Sequence[GroupConfigs]:
        """获取所有群自定义配置。"""
        stmt = select(GroupConfigModel).order_by(GroupConfigModel.group_id)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_group_configs(self) -> int:
        """统计群自定义配置总数。"""
        return await self.count()

    # ---- 更新 ----

    async def update_group_config(self, group_id: str, toml_config: str) -> bool:
        """更新群自定义配置。"""
        stmt = (
            update(GroupConfigModel)
            .where(GroupConfigModel.group_id == group_id)
            .values(toml_config=toml_config)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    async def update_or_create_group_config(
        self, group_id: str, toml_config: str
    ) -> GroupConfigs:
        """更新或创建群自定义配置。"""
        instance = await self._session.get(GroupConfigModel, group_id)
        if instance:
            instance.toml_config = toml_config
            await self._session.flush()
            return instance.to_dto()
        return await self.create_group_config(group_id, toml_config)

    async def set_toml_config(self, group_id: str, toml_config: str) -> GroupConfigs:
        """设置群 TOML 配置内容（等同于 update_or_create）。"""
        return await self.update_or_create_group_config(group_id, toml_config)

    # ---- 删除 ----

    async def delete_group_config(self, group_id: str) -> bool:
        """删除群自定义配置。"""
        return await self.delete_by_id(group_id)

    # ---- 批量操作 ----

    async def batch_create_group_configs(self, configs: list[dict]) -> bool:
        """批量创建群自定义配置。每个 dict 包含 ``group_id`` 和 ``toml_config``。"""
        if not configs:
            return True
        instances = [
            GroupConfigModel(group_id=c["group_id"], toml_config=c["toml_config"])
            for c in configs
        ]
        self._session.add_all(instances)
        await self._session.flush()
        return True
