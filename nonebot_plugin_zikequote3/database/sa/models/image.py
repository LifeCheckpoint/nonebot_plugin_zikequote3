"""
ORM 模型：images 表。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from nonebot_plugin_zikequote3.database.sa.base import Base


class ImageModel(Base):
    """图片 ORM 模型，对应 ``images`` 表。"""

    __tablename__ = "images"

    uuid: Mapped[str] = mapped_column(String, primary_key=True)
    original_filename: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default=None
    )
    stored_filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    time_stamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    checksum_sha256: Mapped[str] = mapped_column(String, nullable=False)

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``Image``。"""
        from ...models.images import Image

        return Image(
            uuid=self.uuid,
            original_filename=self.original_filename,
            stored_filename=self.stored_filename,
            file_path=self.file_path,
            time_stamp=self.time_stamp,
            checksum_sha256=self.checksum_sha256,
        )

    @classmethod
    def from_create_dto(cls, dto) -> ImageModel:
        """从 Pydantic ``ImageCreate`` DTO 创建 ORM 实例。"""
        return cls(
            uuid=dto.uuid,
            original_filename=dto.original_filename,
            stored_filename=dto.stored_filename,
            file_path=dto.file_path,
            checksum_sha256=dto.checksum_sha256,
        )
