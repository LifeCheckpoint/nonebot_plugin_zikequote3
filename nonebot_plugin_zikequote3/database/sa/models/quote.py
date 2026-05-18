"""
ORM 模型：quotes 表。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_plugin_zikequote3.database.sa.base import Base

if TYPE_CHECKING:
    from .group import GroupModel
    from .image import ImageModel
    from .review import ReviewModel
    from .user import UserModel


class QuoteModel(Base):
    """
    语录 ORM 模型，对应 ``quotes`` 表。

    :param quote_id: 语录 ID，主键
    :type quote_id: str
    :param time_stamp: 创建时间，默认为当前时间
    :type time_stamp: datetime
    :param author_id: 作者 QQ 号，外键关联 ``users.qq_id``
    :type author_id: str
    :param group_id: 群号，外键关联 ``groups.group_id``
    :type group_id: str
    :param content: 语录内容，可为空（与图片至少存在一项）
    :type content: Optional[str]
    :param image_content_uuid: 关联图片 UUID，可为空
    :type image_content_uuid: Optional[str]
    :param total_show_time: 总展示次数，默认为 0
    :type total_show_time: int
    """

    __tablename__ = "quotes"
    __table_args__ = (
        CheckConstraint(
            "(content IS NOT NULL AND content != '') OR image_content_uuid IS NOT NULL",
            name="ck_quotes_content_or_image_present",
        ),
        Index("ix_quotes_group_id", "group_id"),
        Index("ix_quotes_author_id", "author_id"),
        Index("ix_quotes_total_show_time", "total_show_time"),
    )

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
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
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
        """
        转换为 Pydantic Full DTO ``Quote``。

        :returns: 语录 DTO 对象
        :rtype: Quote
        """
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
        """
        从 Pydantic ``QuoteCreate`` DTO 创建 ORM 实例。

        :param dto: 创建语录的 DTO
        :type dto: QuoteCreate
        :returns: 语录 ORM 实例
        :rtype: QuoteModel
        """
        return cls(
            quote_id=dto.quote_id,
            author_id=dto.author_id,
            group_id=dto.group_id,
            content=dto.content,
            image_content_uuid=dto.image_content_uuid,
            total_show_time=dto.total_show_time,
        )
