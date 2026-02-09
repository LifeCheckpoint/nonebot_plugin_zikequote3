"""
ORM 模型：reviews 表。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .quote import QuoteModel


class ReviewModel(Base):
    """评论 ORM 模型，对应 ``reviews`` 表。"""

    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String, primary_key=True)
    time_stamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP"
    )
    author_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.qq_id"), nullable=False
    )
    quote_id: Mapped[str] = mapped_column(
        String, ForeignKey("quotes.quote_id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ---- relationships ----
    quote: Mapped[QuoteModel] = relationship(
        "QuoteModel",
        back_populates="reviews",
    )

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``Review``。"""
        from ...models.reviews import Review

        return Review(
            review_id=self.review_id,
            time_stamp=self.time_stamp,
            author_id=self.author_id,
            quote_id=self.quote_id,
            content=self.content,
        )

    @classmethod
    def from_create_dto(cls, dto) -> ReviewModel:
        """从 Pydantic ``ReviewCreate`` DTO 创建 ORM 实例。"""
        return cls(
            review_id=dto.review_id,
            author_id=dto.author_id,
            quote_id=dto.quote_id,
            content=dto.content,
        )
