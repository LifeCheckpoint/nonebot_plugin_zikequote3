"""
QuoteWriteService —— 语录写入领域服务。

合并原模块：
- ``add_quote_service.py``   添加语录
- ``mapping_service.py``     消息ID→语录ID 映射
- ``quote_image_service.py`` 图片注册（元数据部分）

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

import logging
import random
from typing import Optional

from ..database.models.quotes import Quote
from ..database.repositories.image_repository import ImageRepository
from ..database.repositories.mapping_repository import MappingRepository
from ..database.repositories.quote_repository import QuoteRepository
from ..exceptions import (
    DatabaseOperationError,
    ImageNotFoundError,
    QuoteNotFoundError,
    ValidationException,
)
from .user_service import UserService

logger = logging.getLogger(__name__)


def _generate_quote_id() -> str:
    """生成 11 位随机数字语录 ID。"""
    return str(random.randint(10**10, 10**11 - 1))


class QuoteWriteService:
    """语录写入领域服务，通过构造函数注入 Repository 依赖。"""

    def __init__(
        self,
        quote_repo: QuoteRepository,
        image_repo: ImageRepository,
        mapping_repo: MappingRepository,
        user_service: UserService,
    ) -> None:
        self._quote_repo = quote_repo
        self._image_repo = image_repo
        self._mapping_repo = mapping_repo
        self._user_service = user_service

    # ------------------------------------------------------------------ #
    #  添加语录
    # ------------------------------------------------------------------ #

    async def add_quote(
        self,
        group_id: str,
        author_id: str,
        content: Optional[str] = None,
        image_content_uuid: Optional[str] = None,
    ) -> str:
        """
        添加一条语录。

        Args:
            group_id: 群号。
            author_id: 作者 QQ 号。
            content: 语录文本内容（与 image_content_uuid 至少提供一个）。
            image_content_uuid: 关联图片的 UUID。

        Returns:
            新创建的语录 ID。

        Raises:
            ValidationException: 内容和图片均为空。
            ImageNotFoundError: 指定的图片 UUID 不存在。
        """
        if not content and not image_content_uuid:
            raise ValidationException("语录内容和图片不能同时为空")

        # 确保图片存在
        if image_content_uuid is not None:
            exists = await self._image_repo.image_exists(image_content_uuid)
            if not exists:
                raise ImageNotFoundError(
                    f"图片 UUID 不存在: {image_content_uuid}"
                )

        # 确保作者用户记录存在
        await self._user_service.get_or_create_user(author_id)

        quote_id = _generate_quote_id()
        await self._quote_repo.create_quote(
            quote_id=quote_id,
            author_id=author_id,
            group_id=group_id,
            content=content,
            image_content_uuid=image_content_uuid,
        )
        logger.info(
            "语录已添加: quote_id=%s, group=%s, author=%s",
            quote_id, group_id, author_id,
        )
        return quote_id

    async def add_quote_with_image_data(
        self,
        group_id: str,
        author_id: str,
        content: Optional[str],
        image_uuid: str,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        checksum_sha256: str,
    ) -> str:
        """
        添加语录并同时注册图片元数据。

        先在 image_repo 中创建图片记录，再创建语录。

        Returns:
            新创建的语录 ID。
        """
        await self._image_repo.create_image(
            uuid=image_uuid,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            checksum_sha256=checksum_sha256,
        )
        return await self.add_quote(
            group_id=group_id,
            author_id=author_id,
            content=content,
            image_content_uuid=image_uuid,
        )

    # ------------------------------------------------------------------ #
    #  更新语录
    # ------------------------------------------------------------------ #

    async def update_quote(
        self,
        quote_id: str,
        content: Optional[str] = None,
        image_content_uuid: Optional[str] = None,
    ) -> None:
        """
        更新语录内容或图片。

        Raises:
            QuoteNotFoundError: 语录不存在。
            ImageNotFoundError: 指定的图片 UUID 不存在。
        """
        existing = await self._quote_repo.get_quote_by_id(quote_id)
        if existing is None:
            raise QuoteNotFoundError(f"语录不存在: {quote_id}")

        if image_content_uuid is not None:
            exists = await self._image_repo.image_exists(image_content_uuid)
            if not exists:
                raise ImageNotFoundError(
                    f"图片 UUID 不存在: {image_content_uuid}"
                )

        updated = await self._quote_repo.update_quote(
            quote_id=quote_id,
            content=content,
            image_content_uuid=image_content_uuid,
        )
        if not updated:
            raise DatabaseOperationError(f"更新语录失败: {quote_id}")

        logger.info("语录已更新: quote_id=%s", quote_id)

    # ------------------------------------------------------------------ #
    #  删除语录
    # ------------------------------------------------------------------ #

    async def delete_quote(self, quote_id: str) -> None:
        """
        删除语录。

        Raises:
            QuoteNotFoundError: 语录不存在。
        """
        existing = await self._quote_repo.get_quote_by_id(quote_id)
        if existing is None:
            raise QuoteNotFoundError(f"语录不存在: {quote_id}")

        deleted = await self._quote_repo.delete_quote(quote_id)
        if not deleted:
            raise DatabaseOperationError(f"删除语录失败: {quote_id}")

        # 同时清理关联的映射
        await self._mapping_repo.delete_mappings_by_quote_id(quote_id)

        logger.info("语录已删除: quote_id=%s", quote_id)

    # ------------------------------------------------------------------ #
    #  消息ID → 语录ID 映射（原 mapping_service.py）
    # ------------------------------------------------------------------ #

    async def create_msg_quote_mapping(self, msg_id: str, quote_id: str) -> None:
        """
        创建消息 ID 到语录 ID 的映射。

        Raises:
            DatabaseOperationError: 映射创建失败。
        """
        await self._mapping_repo.create_mapping(msg_id, quote_id)
        logger.debug("映射已创建: msg_id=%s -> quote_id=%s", msg_id, quote_id)

    async def get_quote_id_by_msg_id(self, msg_id: str) -> Optional[str]:
        """
        通过消息 ID 获取语录 ID。

        Returns:
            语录 ID，未找到则返回 ``None``。
        """
        return await self._mapping_repo.get_quote_id_by_msg_id(msg_id)
