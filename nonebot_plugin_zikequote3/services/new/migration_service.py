"""
MigrationService —— 群组数据迁移领域服务。

合并原模块：
- ``group_migration_service.py``        群组迁移主流程
- ``quote_submigration_service.py``     语录子迁移
- ``userinfo_submigration_service.py``  用户信息子迁移

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

import itertools
import logging
from typing import Any, Dict, List, Optional, Sequence

from ...database.models.quotes import Quote, QuoteCreate
from ...database.repositories.group_member_repository import GroupMemberRepository
from ...database.repositories.group_nickname_repository import GroupNicknameRepository
from ...database.repositories.quote_repository import QuoteRepository
from ...exceptions import ResourceNotFoundError, ValidationException

logger = logging.getLogger(__name__)


class MigrationService:
    """
    群组数据迁移领域服务，通过构造函数注入 Repository 依赖。

    职责：
    1. 迁移前比较与统计
    2. 语录迁移执行
    3. 用户信息迁移执行
    """

    def __init__(
        self,
        quote_repo: QuoteRepository,
        group_member_repo: GroupMemberRepository,
        group_nickname_repo: GroupNicknameRepository,
    ) -> None:
        self._quote_repo = quote_repo
        self._group_member_repo = group_member_repo
        self._group_nickname_repo = group_nickname_repo

    # ------------------------------------------------------------------ #
    #  迁移前统计与比较
    # ------------------------------------------------------------------ #

    async def prepare_migration(
        self,
        source: str,
        target: str,
        *,
        overwrite: bool = False,
        deduplicate: bool = False,
        exclude_non_member: bool = False,
        keep_source: bool = True,
    ) -> Dict[str, Any]:
        """
        统计迁移所需的全部信息，返回比较结果。

        Args:
            source: 源群号。
            target: 目标群号。
            overwrite: 是否完全覆盖目标群语录。
            deduplicate: 是否对语录去重。
            exclude_non_member: 是否排除非目标群成员的语录。
            keep_source: 是否保留源群语录。

        Returns:
            包含以下键的字典：
            - ``source_quotes``: 源群语录列表
            - ``source_count``: 源群语录数
            - ``target_count``: 目标群原语录数
            - ``final_quotes``: 处理后的最终语录列表
            - ``final_count``: 最终语录数
            - ``before_members``: 迁移前目标群成员数
            - ``after_members``: 迁移后目标群成员数
        """
        source_quotes = list(
            await self._quote_repo.get_quotes_by_group(source)
        )
        target_quotes = list(
            await self._quote_repo.get_quotes_by_group(target)
        )

        source_members = await self._group_member_repo.get_members_by_group(source)
        target_members = await self._group_member_repo.get_members_by_group(target)
        target_qq_ids = {m.qq_id for m in target_members}

        # 记录源群 ID 集合
        source_ids = {q.quote_id for q in source_quotes}

        # 合并或覆写
        if overwrite:
            final_quotes = list(source_quotes)
        else:
            final_quotes = list(source_quotes) + list(target_quotes)

        # 更改归属
        for q in final_quotes:
            q.group_id = target

        # 排除非目标群成员
        if exclude_non_member:
            final_quotes = [q for q in final_quotes if q.author_id in target_qq_ids]

        # 去重
        if deduplicate:
            final_quotes = self._deduplicate_quotes(final_quotes)

        # 处理重复 ID
        final_quotes = self._resolve_duplicate_ids(
            final_quotes,
            force_new_ids_for_source=keep_source,
            source_ids=source_ids,
        )

        # 成员统计
        before_members = len(target_members)
        all_member_ids = {m.qq_id for m in target_members} | {
            m.qq_id for m in source_members
        }
        after_members = len(all_member_ids)

        return {
            "source_quotes": source_quotes,
            "source_count": len(source_quotes),
            "target_count": len(target_quotes),
            "final_quotes": final_quotes,
            "final_count": len(final_quotes),
            "before_members": before_members,
            "after_members": after_members,
        }

    # ------------------------------------------------------------------ #
    #  执行迁移
    # ------------------------------------------------------------------ #

    async def execute_migration(
        self,
        final_quotes: List[Quote],
        source: str,
        target: str,
        *,
        overwrite: bool = False,
        keep_source: bool = True,
        clear_member_info: bool = False,
    ) -> Dict[str, Any]:
        """
        执行群组数据迁移。

        Args:
            final_quotes: 经 :meth:`prepare_migration` 处理后的最终语录列表。
            source: 源群号。
            target: 目标群号。
            overwrite: 是否覆写模式。
            keep_source: 是否保留源群语录。
            clear_member_info: 是否清除源群用户信息。

        Returns:
            迁移结果摘要字典。
        """
        # 1. 语录迁移
        migrated_count = await self._migrate_quotes(
            final_quotes, source, target,
            overwrite=overwrite, keep_source=keep_source,
        )

        # 2. 用户信息迁移
        members_migrated = await self._migrate_user_infos(
            source, target, clear_member_info=clear_member_info,
        )

        result = {
            "quotes_migrated": migrated_count,
            "members_migrated": members_migrated,
            "source": source,
            "target": target,
        }
        logger.info("群组迁移完成: %s -> %s, 语录 %d 条", source, target, migrated_count)
        return result

    # ------------------------------------------------------------------ #
    #  语录子迁移（原 quote_submigration_service）
    # ------------------------------------------------------------------ #

    async def _migrate_quotes(
        self,
        final_quotes: List[Quote],
        source: str,
        target: str,
        *,
        overwrite: bool,
        keep_source: bool,
    ) -> int:
        """执行语录迁移，返回迁移的语录数。"""
        # 清空目标群语录（无论覆写还是合并模式都需要，因为写入的是完整集合）
        logger.info("正在清空目标群 %s 的语录...", target)
        await self._quote_repo.delete_quotes_by_group(target)

        # 如果不保留源群，先清空源群语录以释放 ID
        if not keep_source:
            logger.info("正在清空源群 %s 的语录 (Move 模式)...", source)
            await self._quote_repo.delete_quotes_by_group(source)

        # 批量写入
        if final_quotes:
            quotes_to_create = [
                QuoteCreate(
                    quote_id=q.quote_id,
                    author_id=q.author_id,
                    group_id=target,
                    content=q.content,
                    image_content_uuid=q.image_content_uuid,
                    total_show_time=q.total_show_time,
                )
                for q in final_quotes
            ]
            logger.info("正在向目标群 %s 写入 %d 条语录...", target, len(quotes_to_create))
            await self._quote_repo.batch_create_quotes(quotes_to_create)

        return len(final_quotes)

    # ------------------------------------------------------------------ #
    #  用户信息子迁移（原 userinfo_submigration_service）
    # ------------------------------------------------------------------ #

    async def _migrate_user_infos(
        self,
        source: str,
        target: str,
        *,
        clear_member_info: bool,
    ) -> int:
        """执行用户信息迁移，返回迁移的成员数。"""
        migrated = 0

        # 迁移群成员关系
        source_members = await self._group_member_repo.get_members_by_group(source)
        if source_members:
            source_qq_ids = [m.qq_id for m in source_members]
            logger.info(
                "正在将 %d 名成员从源群 %s 迁移至目标群 %s...",
                len(source_qq_ids), source, target,
            )
            await self._group_member_repo.batch_add_members(target, source_qq_ids)
            migrated = len(source_qq_ids)

        # 迁移群名片
        source_nicknames = await self._group_nickname_repo.get_nicknames_by_group(source)
        if source_nicknames:
            logger.info("正在迁移 %d 条群名片记录...", len(source_nicknames))
            for nickname in source_nicknames:
                try:
                    await self._group_nickname_repo.add_group_nickname(
                        qq_id=nickname.qq_id,
                        group_id=target,
                        current_using=False,
                        name=nickname.name,
                    )
                except Exception:
                    # 忽略重复或其他插入错误
                    pass

        # 清理源群信息
        if clear_member_info:
            logger.info("正在清理源群 %s 的用户信息...", source)
            await self._group_member_repo.delete_all_members_by_group(source)
            await self._group_nickname_repo.clear_group_all_nicknames(source)

        return migrated

    # ------------------------------------------------------------------ #
    #  内部工具方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _deduplicate_quotes(quotes: List[Quote]) -> List[Quote]:
        """基于作者、内容及图片去重，累加重复项的展示次数。"""
        merged: dict[tuple, Quote] = {}
        for q in quotes:
            fingerprint = (q.author_id, q.content, q.image_content_uuid)
            if fingerprint in merged:
                merged[fingerprint].total_show_time += q.total_show_time
            else:
                merged[fingerprint] = q
        return list(merged.values())

    @staticmethod
    def _resolve_duplicate_ids(
        quotes: List[Quote],
        *,
        force_new_ids_for_source: bool = False,
        source_ids: Optional[set[str]] = None,
    ) -> List[Quote]:
        """处理重复 ID，为冲突项分配新 ID。"""
        if not quotes:
            return quotes

        current_max = max(int(q.quote_id) for q in quotes)
        start_id = current_max + 1
        new_id_gen = (str(i) for i in itertools.count(start_id))
        seen: set[str] = set()

        for q in quotes:
            if force_new_ids_for_source and source_ids and q.quote_id in source_ids:
                q.quote_id = next(new_id_gen)
                continue
            if q.quote_id in seen:
                q.quote_id = next(new_id_gen)
            seen.add(q.quote_id)

        return quotes
