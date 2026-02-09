"""
MappingRepository —— 消息ID-语录ID映射数据仓储，对应原 ``MappingDAO``。

覆盖原 DAO 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import delete, func, select, update

from ..models.msgid_quoteid_map import MsgQuoteID, MsgQuoteIDCreate
from ..sa.models.mapping import MsgIdQuoteIdMapModel
from .base import BaseRepository


class MappingRepository(BaseRepository[MsgIdQuoteIdMapModel, MsgQuoteIDCreate, MsgQuoteID]):
    """消息ID-语录ID映射 Repository。"""

    model_class = MsgIdQuoteIdMapModel

    # ---- 创建 ----

    async def create_mapping(self, msg_id: str, quote_id: str) -> MsgQuoteID:
        """创建新的映射关系并返回 DTO。"""
        dto = MsgQuoteIDCreate(msg_id=msg_id, quote_id=quote_id)
        return await self.create(dto)

    async def update_or_create_mapping(self, msg_id: str, quote_id: str) -> MsgQuoteID:
        """更新或创建映射关系。"""
        instance = await self._session.get(MsgIdQuoteIdMapModel, msg_id)
        if instance:
            instance.quote_id = quote_id
            await self._session.flush()
            return instance.to_dto()
        return await self.create_mapping(msg_id, quote_id)

    # ---- 查询 ----

    async def get_mapping_by_msg_id(self, msg_id: str) -> Optional[MsgQuoteID]:
        """根据消息 ID 获取映射关系。"""
        return await self.get_by_id(msg_id)

    async def get_quote_id_by_msg_id(self, msg_id: str) -> Optional[str]:
        """根据消息 ID 获取语录 ID。"""
        instance = await self._session.get(MsgIdQuoteIdMapModel, msg_id)
        return instance.quote_id if instance else None

    async def get_mappings_by_quote_id(self, quote_id: str) -> Sequence[MsgQuoteID]:
        """根据语录 ID 获取所有相关的映射关系。"""
        stmt = select(MsgIdQuoteIdMapModel).where(
            MsgIdQuoteIdMapModel.quote_id == quote_id
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def mapping_exists(self, msg_id: str) -> bool:
        """检查消息 ID 的映射关系是否存在。"""
        return await self.exists_by_id(msg_id)

    async def get_mappings_by_msg_ids(self, msg_ids: list[str]) -> Sequence[MsgQuoteID]:
        """根据消息 ID 列表批量获取映射关系。"""
        if not msg_ids:
            return []
        stmt = select(MsgIdQuoteIdMapModel).where(
            MsgIdQuoteIdMapModel.msg_id.in_(msg_ids)
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_mappings_by_quote_id(self, quote_id: str) -> int:
        """统计语录 ID 对应的映射关系数量。"""
        stmt = (
            select(func.count())
            .select_from(MsgIdQuoteIdMapModel)
            .where(MsgIdQuoteIdMapModel.quote_id == quote_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_all_mappings(self) -> Sequence[MsgQuoteID]:
        """获取所有映射关系。"""
        stmt = select(MsgIdQuoteIdMapModel)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    # ---- 删除 ----

    async def delete_mapping_by_msg_id(self, msg_id: str) -> bool:
        """根据消息 ID 删除映射关系。"""
        return await self.delete_by_id(msg_id)

    async def delete_mappings_by_quote_id(self, quote_id: str) -> bool:
        """根据语录 ID 删除所有相关的映射关系。"""
        stmt = delete(MsgIdQuoteIdMapModel).where(
            MsgIdQuoteIdMapModel.quote_id == quote_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    async def clear_all_mappings(self) -> bool:
        """清空所有映射关系。"""
        stmt = delete(MsgIdQuoteIdMapModel)
        await self._session.execute(stmt)
        await self._session.flush()
        return True

    # ---- 批量操作 ----

    async def batch_create_mappings(self, mappings: list[dict]) -> bool:
        """批量创建映射关系。每个 dict 包含 ``msg_id`` 和 ``quote_id``。"""
        if not mappings:
            return True
        instances = [
            MsgIdQuoteIdMapModel(msg_id=m["msg_id"], quote_id=m["quote_id"])
            for m in mappings
        ]
        self._session.add_all(instances)
        await self._session.flush()
        return True
