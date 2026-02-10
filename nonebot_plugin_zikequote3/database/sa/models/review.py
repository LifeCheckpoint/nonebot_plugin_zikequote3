"""
ORM 模型：reviews 表。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .quote import QuoteModel


class ReviewModel(Base):
    """
    评论 ORM 模型，对应 ``reviews`` 表。

    :param review_id: 评论 ID，主键
    :type review_id: str
    :param time_stamp: 评论时间，默认为当前时间
    :type time_stamp: datetime
    :param author_id: 评论者 QQ 号，外键关联 ``users.qq_id``
    :type author_id: str
    :param quote_id: 语录 ID，外键关联 ``quotes.quote_id``
    :type quote_id: str
    :param content: 评论内容
    :type content: str
    """

    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String, primary_key=True)
    time_stamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
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
        """
        转换为 Pydantic Full DTO ``Review``。

        :returns: 评论 DTO 对象
        :rtype: Review
        """
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
        """
        从 Pydantic ``ReviewCreate`` DTO 创建 ORM 实例。

        :param dto: 创建评论的 DTO
        :type dto: ReviewCreate
        :returns: 评论 ORM 实例
        :rtype: ReviewModel
        """
        return cls(
            review_id=dto.review_id,
            author_id=dto.author_id,
            quote_id=dto.quote_id,
            content=dto.content,
        )
