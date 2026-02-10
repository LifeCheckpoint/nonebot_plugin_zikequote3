"""
ImageRepository —— 图片数据仓储。

覆盖原 ``ImageDAO`` 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import or_, select, update

from ..models.images import Image, ImageCreate
from ..sa.models.image import ImageModel
from .base import BaseRepository


class ImageRepository(BaseRepository[ImageModel, ImageCreate, Image]):
    """
    图片 Repository，封装图片表的数据访问操作。

    :param session: 异步数据库会话
    :type session: AsyncSession
    """

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
        """
        创建新图片并返回 DTO。

        :param uuid: 图片 UUID
        :type uuid: str
        :param original_filename: 原始文件名
        :type original_filename: str
        :param stored_filename: 存储文件名
        :type stored_filename: str
        :param file_path: 文件路径
        :type file_path: str
        :param checksum_sha256: SHA256 校验和
        :type checksum_sha256: str
        :returns: 图片 DTO
        :rtype: Image
        """
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
        """
        根据 UUID 获取图片。

        :param uuid: 图片 UUID
        :type uuid: str
        :returns: 图片 DTO，不存在时返回 ``None``
        :rtype: Optional[Image]
        """
        return await self.get_by_id(uuid)

    async def image_exists(self, uuid: str) -> bool:
        """
        检查图片是否存在。

        :param uuid: 图片 UUID
        :type uuid: str
        :returns: 存在返回 ``True``
        :rtype: bool
        """
        return await self.exists_by_id(uuid)

    async def get_images_by_checksum(self, checksum_sha256: str) -> Sequence[Image]:
        """
        根据 SHA256 校验和获取图片。

        :param checksum_sha256: SHA256 校验和
        :type checksum_sha256: str
        :returns: 图片 DTO 序列
        :rtype: Sequence[Image]
        """
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
        """获取最近的图片（按时间倒序）。

        :param limit: 最大返回数量，``None`` 表示不限制。
        :type limit: Optional[int]
        :param offset: 分页偏移量。
        :type offset: int
        :returns: 图片 DTO 序列。
        :rtype: Sequence[Image]
        """
        stmt = select(ImageModel).order_by(ImageModel.time_stamp.desc())
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_images_by_original_filename(
        self, original_filename: str
    ) -> Sequence[Image]:
        """根据原始文件名获取图片。

        :param original_filename: 原始文件名（精确匹配）。
        :type original_filename: str
        :returns: 匹配的图片 DTO 序列（按时间升序）。
        :rtype: Sequence[Image]
        """
        stmt = (
            select(ImageModel)
            .where(ImageModel.original_filename == original_filename)
            .order_by(ImageModel.time_stamp)
        )
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def search_images_by_filename(self, filename_pattern: str) -> Sequence[Image]:
        """根据文件名模式搜索图片（模糊匹配原始/存储文件名）。

        :param filename_pattern: 文件名关键词，内部自动添加 ``%`` 通配符。
        :type filename_pattern: str
        :returns: 匹配的图片 DTO 序列（按时间降序）。
        :rtype: Sequence[Image]
        """
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
        """统计图片总数。

        :returns: 图片记录总数。
        :rtype: int
        """
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
        """更新图片信息（仅更新非 ``None`` 字段）。

        :param uuid: 图片唯一标识。
        :type uuid: str
        :param original_filename: 新的原始文件名。
        :type original_filename: Optional[str]
        :param stored_filename: 新的存储文件名。
        :type stored_filename: Optional[str]
        :param file_path: 新的文件路径。
        :type file_path: Optional[str]
        :param checksum_sha256: 新的 SHA-256 校验和。
        :type checksum_sha256: Optional[str]
        :returns: 是否成功更新（找到记录）。
        :rtype: bool
        """
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
        """删除图片。

        :param uuid: 图片唯一标识。
        :type uuid: str
        :returns: 是否成功删除。
        :rtype: bool
        """
        return await self.delete_by_id(uuid)

    # ---- 批量操作 ----

    async def batch_create_images(self, images: list[ImageCreate]) -> bool:
        """批量创建图片。

        :param images: 图片创建 DTO 列表。
        :type images: list[ImageCreate]
        :returns: 操作是否成功。
        :rtype: bool
        """
        if not images:
            return True
        instances = [ImageModel.from_create_dto(img) for img in images]
        self._session.add_all(instances)
        await self._session.flush()
        return True
