"""
ImageRepository —— 图片数据仓储，对应原 ``ImageDAO``。

覆盖原 DAO 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import or_, select, update

from ..models.images import Image, ImageCreate
from ..sa.models.image import ImageModel
from .base import BaseRepository


class ImageRepository(BaseRepository[ImageModel, ImageCreate, Image]):
    """图片 Repository。"""

    model_class = ImageModel

    # ---- 便捷创建 ----

    async def create_image(
        self,
        uuid: str,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        checksum_sha256: str,
    ) -> Image:
        """创建新图片并返回 DTO。"""
        dto = ImageCreate(
            uuid=uuid,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            checksum_sha256=checksum_sha256,
        )
        return await self.create(dto)

    # ---- 查询 ----

    async def get_by_uuid(self, uuid: str) -> Optional[Image]:
        """根据 UUID 获取图片。"""
        return await self.get_by_id(uuid)

    async def image_exists(self, uuid: str) -> bool:
        """检查图片是否存在。"""
        return await self.exists_by_id(uuid)

    async def get_images_by_checksum(self, checksum_sha256: str) -> Sequence[Image]:
        """根据 SHA256 校验和获取图片。"""
        stmt = (
            select(ImageModel)
            .where(ImageModel.checksum_sha256 == checksum_sha256)
            .order_by(ImageModel.time_stamp)
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_recent_images(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> Sequence[Image]:
        """获取最近的图片（按时间倒序）。"""
        stmt = select(ImageModel).order_by(ImageModel.time_stamp.desc())
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_images_by_original_filename(
        self, original_filename: str
    ) -> Sequence[Image]:
        """根据原始文件名获取图片。"""
        stmt = (
            select(ImageModel)
            .where(ImageModel.original_filename == original_filename)
            .order_by(ImageModel.time_stamp)
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def search_images_by_filename(self, filename_pattern: str) -> Sequence[Image]:
        """根据文件名模式搜索图片（模糊匹配原始/存储文件名）。"""
        pattern = f"%{filename_pattern}%"
        stmt = (
            select(ImageModel)
            .where(
                or_(
                    ImageModel.original_filename.like(pattern),
                    ImageModel.stored_filename.like(pattern),
                )
            )
            .order_by(ImageModel.time_stamp.desc())
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_images(self) -> int:
        """统计图片总数。"""
        return await self.count()

    # ---- 更新 ----

    async def update_image(
        self,
        uuid: str,
        original_filename: Optional[str] = None,
        stored_filename: Optional[str] = None,
        file_path: Optional[str] = None,
        checksum_sha256: Optional[str] = None,
    ) -> bool:
        """更新图片信息（仅更新非 None 字段）。"""
        values: dict = {}
        if original_filename is not None:
            values["original_filename"] = original_filename
        if stored_filename is not None:
            values["stored_filename"] = stored_filename
        if file_path is not None:
            values["file_path"] = file_path
        if checksum_sha256 is not None:
            values["checksum_sha256"] = checksum_sha256
        if not values:
            return True
        stmt = update(ImageModel).where(ImageModel.uuid == uuid).values(**values)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    # ---- 删除 ----

    async def delete_image(self, uuid: str) -> bool:
        """删除图片。"""
        return await self.delete_by_id(uuid)

    # ---- 批量操作 ----

    async def batch_create_images(self, images: list[ImageCreate]) -> bool:
        """批量创建图片。"""
        if not images:
            return True
        instances = [ImageModel.from_create_dto(img) for img in images]
        self._session.add_all(instances)
        await self._session.flush()
        return True
