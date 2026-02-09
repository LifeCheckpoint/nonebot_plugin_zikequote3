"""
ORM 模型：msgid_quoteid_map 表。
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from nonebot_plugin_zikequote3.database.sa.base import Base


class MsgIdQuoteIdMapModel(Base):
    """消息ID-语录ID映射 ORM 模型，对应 ``msgid_quoteid_map`` 表。"""

    __tablename__ = "msgid_quoteid_map"

    msg_id: Mapped[str] = mapped_column(String, primary_key=True)
    quote_id: Mapped[str] = mapped_column(
        String, ForeignKey("quotes.quote_id", ondelete="CASCADE"), nullable=False
    )

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``MsgQuoteID``。"""
        from ...models.msgid_quoteid_map import MsgQuoteID

        return MsgQuoteID(
            msg_id=self.msg_id,
            quote_id=self.quote_id,
        )

    @classmethod
    def from_create_dto(cls, dto) -> MsgIdQuoteIdMapModel:
        """从 Pydantic ``MsgQuoteIDCreate`` DTO 创建 ORM 实例。"""
        return cls(
            msg_id=dto.msg_id,
            quote_id=dto.quote_id,
        )
