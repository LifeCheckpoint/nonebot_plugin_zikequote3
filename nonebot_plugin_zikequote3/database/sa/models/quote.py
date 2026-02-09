"""
ORM 模型：quotes 表。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .group import GroupModel
    from .image import ImageModel
    from .review import ReviewModel
    from .user import UserModel


class QuoteModel(Base):
    """语录 ORM 模型，对应 ``quotes`` 表。"""

    __tablename__ = "quotes"

    quote_id: Mapped[str] = mapped_column(String, primary_key=True)
    time_stamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    author_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.qq_id"), nullable=False
    )
    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.group_id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_content_uuid: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("images.uuid", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    total_show_time: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # ---- relationships ----
    author: Mapped["UserModel"] = relationship(  # noqa: F821
        "UserModel",
        foreign_keys=[author_id],
        lazy="select",
    )
    group: Mapped["GroupModel"] = relationship(  # noqa: F821
        "GroupModel",
        foreign_keys=[group_id],
        lazy="select",
    )
    image: Mapped[Optional[ImageModel]] = relationship(
        "ImageModel",
        foreign_keys=[image_content_uuid],
        lazy="select",
    )
    reviews: Mapped[list[ReviewModel]] = relationship(
        "ReviewModel",
        back_populates="quote",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``Quote``。"""
        from ...models.quotes import Quote

        return Quote(
            quote_id=self.quote_id,
            time_stamp=self.time_stamp,
            author_id=self.author_id,
            group_id=self.group_id,
            content=self.content,
            image_content_uuid=self.image_content_uuid,
            total_show_time=self.total_show_time,
        )

    @classmethod
    def from_create_dto(cls, dto) -> QuoteModel:
        """从 Pydantic ``QuoteCreate`` DTO 创建 ORM 实例。"""
        return cls(
            quote_id=dto.quote_id,
            author_id=dto.author_id,
            group_id=dto.group_id,
            content=dto.content,
            image_content_uuid=dto.image_content_uuid,
            total_show_time=dto.total_show_time,
        )
