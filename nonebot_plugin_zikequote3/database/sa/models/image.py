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
    """
    图片 ORM 模型，对应 ``images`` 表。

    :param uuid: 图片 UUID，主键
    :type uuid: str
    :param original_filename: 原始文件名，可为空
    :type original_filename: Optional[str]
    :param stored_filename: 存储文件名
    :type stored_filename: str
    :param file_path: 文件路径
    :type file_path: str
    :param time_stamp: 创建时间，默认为当前时间
    :type time_stamp: datetime
    :param checksum_sha256: SHA256 校验和
    :type checksum_sha256: str
    """

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
        """
        转换为 Pydantic Full DTO ``Image``。

        :returns: 图片 DTO 对象
        :rtype: Image
        """
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
        """
        从 Pydantic ``ImageCreate`` DTO 创建 ORM 实例。

        :param dto: 创建图片的 DTO
        :type dto: ImageCreate
        :returns: 图片 ORM 实例
        :rtype: ImageModel
        """
        return cls(
            uuid=dto.uuid,
            original_filename=dto.original_filename,
            stored_filename=dto.stored_filename,
            file_path=dto.file_path,
            checksum_sha256=dto.checksum_sha256,
        )
