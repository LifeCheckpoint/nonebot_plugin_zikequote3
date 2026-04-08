"""
QuoteWriteService —— 语录写入领域服务。

合并原模块：
- ``add_quote_service.py``   添加语录
- ``mapping_service.py``     消息ID→语录ID 映射
- ``quote_image_service.py`` 图片注册（元数据部分）

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

from nonebot import logger
import random
from typing import Optional

from ..database.models.quotes import Quote
from ..database.repositories.group_repository import GroupRepository
from ..database.repositories.image_repository import ImageRepository
from ..database.repositories.mapping_repository import MappingRepository
from ..database.repositories.quote_repository import QuoteRepository
from ..exceptions import (
    DatabaseOperationError,
    ImageNotFoundError,
    PermissionDeniedError,
    QuoteNotFoundError,
    ValidationException,
)
from ..vector_search.capability import (
    UnavailableVectorSearchService,
    VectorSearchCapability,
)
from .config_service import ConfigService
from .user_service import UserService

def _generate_quote_id() -> str:
    """
    生成 11 位随机数字语录 ID。

    :returns: 11 位随机数字字符串
    :rtype: str
    """
    return str(random.randint(10**10, 10**11 - 1))

class QuoteWriteService:
    """
    语录写入领域服务，通过构造函数注入 Repository 依赖。

    :param quote_repo: 语录仓储实例
    :type quote_repo: QuoteRepository
    :param image_repo: 图片仓储实例
    :type image_repo: ImageRepository
    :param mapping_repo: 映射仓储实例
    :type mapping_repo: MappingRepository
    :param user_service: 用户服务实例
    :type user_service: UserService
    """

    def __init__(
        self,
        quote_repo: QuoteRepository,
        image_repo: ImageRepository,
        mapping_repo: MappingRepository,
        user_service: UserService,
        config_service: ConfigService,
        group_repo: GroupRepository | None = None,
        vector_search_svc: VectorSearchCapability | None = None,
    ) -> None:
        self._quote_repo = quote_repo
        self._image_repo = image_repo
        self._mapping_repo = mapping_repo
        self._user_service = user_service
        self._config_service = config_service
        self._group_repo = group_repo
        self._vector_search_svc = vector_search_svc or UnavailableVectorSearchService(
            "未提供向量搜索能力"
        )

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

        :param group_id: 群号
        :type group_id: str
        :param author_id: 作者 QQ 号
        :type author_id: str
        :param content: 语录文本内容（与 image_content_uuid 至少提供一个）
        :type content: Optional[str]
        :param image_content_uuid: 关联图片的 UUID
        :type image_content_uuid: Optional[str]
        :returns: 新创建的语录 ID
        :rtype: str
        :raises ValidationException: 内容和图片均为空
        :raises ImageNotFoundError: 指定的图片 UUID 不存在
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

        # 确保群组记录存在（兜底保护）
        if self._group_repo is not None:
            await self._group_repo.ensure_group_exists(group_id)

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
            "语录已添加: quote_id={}, group={}, author={}",
            quote_id, group_id, author_id,
        )

        # 异步更新向量索引（不影响主流程）
        quote = await self._quote_repo.get_quote_by_id(quote_id)
        if quote is not None:
            await self._try_index_quote(quote)

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

        :param group_id: 群号
        :type group_id: str
        :param author_id: 作者 QQ 号
        :type author_id: str
        :param content: 语录文本内容
        :type content: Optional[str]
        :param image_uuid: 图片 UUID
        :type image_uuid: str
        :param original_filename: 原始文件名
        :type original_filename: str
        :param stored_filename: 存储文件名
        :type stored_filename: str
        :param file_path: 文件存储路径
        :type file_path: str
        :param checksum_sha256: 文件 SHA-256 校验和
        :type checksum_sha256: str
        :returns: 新创建的语录 ID
        :rtype: str
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

        :param quote_id: 语录 ID
        :type quote_id: str
        :param content: 新的文本内容
        :type content: Optional[str]
        :param image_content_uuid: 新的图片 UUID
        :type image_content_uuid: Optional[str]
        :raises QuoteNotFoundError: 语录不存在
        :raises ImageNotFoundError: 指定的图片 UUID 不存在
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

        logger.info("语录已更新: quote_id={}", quote_id)

        # 异步更新向量索引（不影响主流程）
        updated_quote = await self._quote_repo.get_quote_by_id(quote_id)
        if updated_quote is not None:
            await self._try_index_quote(updated_quote)

    # ------------------------------------------------------------------ #
    #  删除语录
    # ------------------------------------------------------------------ #

    async def get_quote_by_id(self, quote_id: str) -> Optional[Quote]:
        """按语录 ID 查询语录对象。"""
        return await self._quote_repo.get_quote_by_id(quote_id)

    async def delete_quote(
        self,
        quote_id: str,
        *,
        operator_id: str,
        allow_delete_others: bool = False,
    ) -> None:
        """
        删除语录。

        :param quote_id: 语录 ID
        :type quote_id: str
        :param operator_id: 执行删除的操作者 ID
        :type operator_id: str
        :param allow_delete_others: 是否允许删除他人语录
        :type allow_delete_others: bool
        :raises QuoteNotFoundError: 语录不存在
        :raises PermissionDeniedError: 操作者无权删除该语录
        """
        existing = await self._quote_repo.get_quote_by_id(quote_id)
        if existing is None:
            raise QuoteNotFoundError(f"语录不存在: {quote_id}")

        self._ensure_delete_permission(
            quote_id=quote_id,
            owner_id=existing.author_id,
            operator_id=operator_id,
            allow_delete_others=allow_delete_others,
        )

        deleted = await self._quote_repo.delete_quote(quote_id)
        if not deleted:
            raise DatabaseOperationError(f"删除语录失败: {quote_id}")

        # 同时清理关联的映射
        await self._mapping_repo.delete_mappings_by_quote_id(quote_id)

        logger.info("语录已删除: quote_id={}", quote_id)

        # 异步删除向量索引（不影响主流程）
        await self._try_remove_quote(quote_id, existing.group_id)

    def _ensure_delete_permission(
        self,
        *,
        quote_id: str,
        owner_id: str,
        operator_id: str,
        allow_delete_others: bool,
    ) -> None:
        """校验删除语录时的操作者归属约束。"""
        if not operator_id:
            raise PermissionDeniedError(
                f"删除语录缺少操作者上下文（quote_id={quote_id}）"
            )
        if owner_id == operator_id or allow_delete_others:
            return

        logger.warning(
            "越权删除语录被拒绝: quote_id={}, owner={}, operator={}, allow_delete_others={}",
            quote_id,
            owner_id,
            operator_id,
            allow_delete_others,
        )
        raise PermissionDeniedError(f"仅可删除自己的语录（quote_id={quote_id}）")

    # ------------------------------------------------------------------ #
    #  消息ID → 语录ID 映射（原 mapping_service.py）
    # ------------------------------------------------------------------ #

    async def create_msg_quote_mapping(self, msg_id: str, quote_id: str) -> None:
        """
        创建消息 ID 到语录 ID 的映射。

        :param msg_id: 消息 ID
        :type msg_id: str
        :param quote_id: 语录 ID
        :type quote_id: str
        :raises DatabaseOperationError: 映射创建失败
        """
        await self._mapping_repo.create_mapping(msg_id, quote_id)
        logger.debug("映射已创建: msg_id={} -> quote_id={}", msg_id, quote_id)

    async def get_quote_id_by_msg_id(self, msg_id: str) -> Optional[str]:
        """
        通过消息 ID 获取语录 ID。

        :param msg_id: 消息 ID
        :type msg_id: str
        :returns: 语录 ID，未找到则返回 ``None``
        :rtype: Optional[str]
        """
        return await self._mapping_repo.get_quote_id_by_msg_id(msg_id)

    # ------------------------------------------------------------------ #
    #  向量索引辅助方法
    # ------------------------------------------------------------------ #

    async def _try_index_quote(self, quote: Quote) -> None:
        """尝试为语录建立向量索引，失败仅记录日志。

        当向量能力不可用或群组未启用 embedding 时静默跳过。

        :param quote: 待索引的语录对象。
        :type quote: Quote
        """
        if not self._vector_search_svc.get_status().available:
            return
        try:
            cfg = await self._config_service.get_parsed_config(quote.group_id)
            if not cfg.embedding.enabled:
                return
            await self._vector_search_svc.index_quote(quote)
        except Exception as e:
            logger.warning("向量索引更新失败 (quote_id={}): {}", quote.quote_id, e)

    async def _try_remove_quote(self, quote_id: str, group_id: str) -> None:
        """尝试删除语录的向量索引，失败仅记录日志。

        当向量能力不可用或群组未启用 embedding 时静默跳过。

        :param quote_id: 待删除索引的语录 ID。
        :type quote_id: str
        :param group_id: 群组 ID。
        :type group_id: str
        """
        if not self._vector_search_svc.get_status().available:
            return
        try:
            cfg = await self._config_service.get_parsed_config(group_id)
            if not cfg.embedding.enabled:
                return
            await self._vector_search_svc.remove_quote(quote_id)
        except Exception as e:
            logger.warning("向量索引删除失败 (quote_id={}): {}", quote_id, e)

    # ------------------------------------------------------------------ #
    #  去重检查
    # ------------------------------------------------------------------ #

    async def check_quote_exists(self, author_id: str, content: str) -> bool:
        """
        检查指定作者和内容的语录是否已存在（用于去重）。

        :param author_id: 作者 QQ 号
        :type author_id: str
        :param content: 语录文本内容
        :type content: str
        :returns: ``True`` 表示已存在相同语录
        :rtype: bool
        """
        return await self._quote_repo.check_quote_exists_by_author_content(
            author_id, content
        )
