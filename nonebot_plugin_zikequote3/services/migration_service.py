"""
MigrationService —— 群组数据迁移领域服务。

合并原模块：
- ``group_migration_service.py``        群组迁移主流程
- ``quote_submigration_service.py``     语录子迁移
- ``userinfo_submigration_service.py``  用户信息子迁移

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Literal, Optional, Sequence

from nonebot import logger
from sqlalchemy.exc import IntegrityError

from ..database.models.quotes import Quote
from ..database.repositories.group_member_repository import GroupMemberRepository
from ..database.repositories.group_nickname_repository import GroupNicknameRepository
from ..database.repositories.mapping_repository import MappingRepository
from ..database.repositories.quote_repository import QuoteRepository
from ..database.repositories.review_repository import ReviewRepository
from ..exceptions import OperationError


@dataclass(slots=True)
class _QuoteCandidate:
    quote: Quote
    origin: Literal["source", "target"]
    original_quote_id: str


@dataclass(slots=True)
class _RemovedQuoteCandidate:
    candidate: _QuoteCandidate
    reason: Literal["deduplicated", "overwrite", "exclude_non_member"]
    winner: Optional[_QuoteCandidate] = None


@dataclass(slots=True)
class _QuoteMigrationPlan:
    source_quotes: List[Quote]
    target_quotes: List[Quote]
    final_candidates: List[_QuoteCandidate]
    removed_candidates: List[_RemovedQuoteCandidate] = field(default_factory=list)

    @property
    def final_quotes(self) -> List[Quote]:
        return [candidate.quote for candidate in self.final_candidates]


@dataclass(slots=True, frozen=True)
class MigrationQuoteSnapshot:
    quote_id: str
    author_id: str
    group_id: str
    content: Optional[str]
    image_content_uuid: Optional[str]
    total_show_time: int
    time_stamp: datetime

    @classmethod
    def from_quote(cls, quote: Quote) -> "MigrationQuoteSnapshot":
        return cls(
            quote_id=quote.quote_id,
            author_id=quote.author_id,
            group_id=quote.group_id,
            content=quote.content,
            image_content_uuid=quote.image_content_uuid,
            total_show_time=quote.total_show_time,
            time_stamp=quote.time_stamp,
        )

    def to_quote(self) -> Quote:
        return Quote(
            quote_id=self.quote_id,
            author_id=self.author_id,
            group_id=self.group_id,
            content=self.content,
            image_content_uuid=self.image_content_uuid,
            total_show_time=self.total_show_time,
            time_stamp=self.time_stamp,
        )


@dataclass(slots=True, frozen=True)
class MigrationCandidateSnapshot:
    quote: MigrationQuoteSnapshot
    origin: Literal["source", "target"]
    original_quote_id: str

    @classmethod
    def from_candidate(
        cls, candidate: _QuoteCandidate,
    ) -> "MigrationCandidateSnapshot":
        return cls(
            quote=MigrationQuoteSnapshot.from_quote(candidate.quote),
            origin=candidate.origin,
            original_quote_id=candidate.original_quote_id,
        )

    def to_candidate(self) -> _QuoteCandidate:
        return _QuoteCandidate(
            quote=self.quote.to_quote(),
            origin=self.origin,
            original_quote_id=self.original_quote_id,
        )


@dataclass(slots=True, frozen=True)
class MigrationRemovedCandidateSnapshot:
    candidate: MigrationCandidateSnapshot
    reason: Literal["deduplicated", "overwrite", "exclude_non_member"]
    winner_origin: Optional[Literal["source", "target"]] = None
    winner_original_quote_id: Optional[str] = None

    @classmethod
    def from_removed_candidate(
        cls, removed: _RemovedQuoteCandidate,
    ) -> "MigrationRemovedCandidateSnapshot":
        winner_origin: Optional[Literal["source", "target"]] = None
        winner_original_quote_id: Optional[str] = None
        if removed.winner is not None:
            winner_origin = removed.winner.origin
            winner_original_quote_id = removed.winner.original_quote_id
        return cls(
            candidate=MigrationCandidateSnapshot.from_candidate(removed.candidate),
            reason=removed.reason,
            winner_origin=winner_origin,
            winner_original_quote_id=winner_original_quote_id,
        )


@dataclass(slots=True, frozen=True)
class MigrationStateSnapshot:
    source_quotes: tuple[MigrationQuoteSnapshot, ...]
    target_quotes: tuple[MigrationQuoteSnapshot, ...]
    source_member_ids: tuple[str, ...]
    target_member_ids: tuple[str, ...]
    source_nickname_keys: tuple[tuple[str, str], ...]
    target_nickname_keys: tuple[tuple[str, str], ...]


@dataclass(slots=True, frozen=True)
class MigrationSnapshot:
    source: str
    target: str
    overwrite: bool
    deduplicate: bool
    exclude_non_member: bool
    keep_source: bool
    state: MigrationStateSnapshot
    final_candidates: tuple[MigrationCandidateSnapshot, ...]
    removed_candidates: tuple[MigrationRemovedCandidateSnapshot, ...]

    @property
    def final_quotes(self) -> List[Quote]:
        return [candidate.quote.to_quote() for candidate in self.final_candidates]


@dataclass(slots=True, frozen=True)
class MigrationPreview:
    snapshot: MigrationSnapshot
    source_count: int
    target_count: int
    final_count: int
    before_members: int
    after_members: int

    @property
    def final_quotes(self) -> List[Quote]:
        return self.snapshot.final_quotes


class MigrationService:
    """
    群组数据迁移领域服务，通过构造函数注入 Repository 依赖。

    职责：

    1. 迁移前比较与统计
    2. 语录迁移执行
    3. 用户信息迁移执行

    :param quote_repo: 语录仓储实例
    :type quote_repo: QuoteRepository
    :param group_member_repo: 群成员仓储实例
    :type group_member_repo: GroupMemberRepository
    :param group_nickname_repo: 群名片仓储实例
    :type group_nickname_repo: GroupNicknameRepository
    :param review_repo: 评论仓储实例
    :type review_repo: ReviewRepository
    :param mapping_repo: 消息映射仓储实例
    :type mapping_repo: MappingRepository
    """

    def __init__(
        self,
        quote_repo: QuoteRepository,
        group_member_repo: GroupMemberRepository,
        group_nickname_repo: GroupNicknameRepository,
        review_repo: ReviewRepository,
        mapping_repo: MappingRepository,
    ) -> None:
        self._quote_repo = quote_repo
        self._group_member_repo = group_member_repo
        self._group_nickname_repo = group_nickname_repo
        self._review_repo = review_repo
        self._mapping_repo = mapping_repo

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
    ) -> MigrationPreview:
        """
        统计迁移所需的全部信息，并生成执行阶段必须消费的显式快照。

        :param source: 源群号
        :type source: str
        :param target: 目标群号
        :type target: str
        :param overwrite: 是否完全覆盖目标群语录
        :type overwrite: bool
        :param deduplicate: 是否对语录去重
        :type deduplicate: bool
        :param exclude_non_member: 是否排除非目标群成员的语录
        :type exclude_non_member: bool
        :param keep_source: 是否保留源群语录
        :type keep_source: bool
        :returns: 包含展示统计与执行快照的预览对象
        :rtype: MigrationPreview
        """
        state = await self._capture_migration_state(source, target)
        source_quotes = [quote.to_quote() for quote in state.source_quotes]
        target_quotes = [quote.to_quote() for quote in state.target_quotes]

        plan = await self._build_quote_migration_plan(
            source_quotes=source_quotes,
            target_quotes=target_quotes,
            target=target,
            target_member_ids=set(state.target_member_ids),
            overwrite=overwrite,
            deduplicate=deduplicate,
            exclude_non_member=exclude_non_member,
            keep_source=keep_source,
        )

        before_members = len(state.target_member_ids)
        after_members = len(set(state.target_member_ids) | set(state.source_member_ids))

        return MigrationPreview(
            snapshot=self._build_migration_snapshot(
                source=source,
                target=target,
                overwrite=overwrite,
                deduplicate=deduplicate,
                exclude_non_member=exclude_non_member,
                keep_source=keep_source,
                state=state,
                plan=plan,
            ),
            source_count=len(state.source_quotes),
            target_count=len(state.target_quotes),
            final_count=len(plan.final_candidates),
            before_members=before_members,
            after_members=after_members,
        )

    # ------------------------------------------------------------------ #
    #  执行迁移
    # ------------------------------------------------------------------ #

    async def execute_migration(
        self,
        snapshot: MigrationSnapshot,
        *,
        clear_member_info: bool = False,
    ) -> dict[str, Any]:
        """
        执行群组数据迁移。

        :param snapshot: 由 :meth:`prepare_migration` 生成并经用户确认的迁移快照
        :type snapshot: MigrationSnapshot
        :param clear_member_info: 是否清除源群用户信息
        :type clear_member_info: bool
        :returns: 迁移结果摘要字典
        :rtype: dict[str, Any]
        """
        await self._assert_snapshot_is_current(snapshot)
        plan = self._plan_from_snapshot(snapshot)

        migrated_count = await self._migrate_quotes(
            plan,
            snapshot.source,
            snapshot.target,
            keep_source=snapshot.keep_source,
        )

        members_migrated = await self._migrate_user_infos(
            snapshot.source,
            snapshot.target,
            clear_member_info=clear_member_info,
        )

        result = {
            "quotes_migrated": migrated_count,
            "members_migrated": members_migrated,
            "source": snapshot.source,
            "target": snapshot.target,
        }
        logger.info(
            "群组迁移完成: {} -> {}, 语录 {} 条",
            snapshot.source,
            snapshot.target,
            migrated_count,
        )
        return result

    async def _capture_migration_state(
        self,
        source: str,
        target: str,
    ) -> MigrationStateSnapshot:
        source_quotes = tuple(
            self._quote_to_snapshot(quote)
            for quote in await self._quote_repo.get_quotes_by_group(source)
        )
        target_quotes = tuple(
            self._quote_to_snapshot(quote)
            for quote in await self._quote_repo.get_quotes_by_group(target)
        )
        source_members = await self._group_member_repo.get_members_by_group(source)
        target_members = await self._group_member_repo.get_members_by_group(target)
        source_nicknames = await self._group_nickname_repo.get_nicknames_by_group(source)
        target_nicknames = await self._group_nickname_repo.get_nicknames_by_group(target)

        return MigrationStateSnapshot(
            source_quotes=source_quotes,
            target_quotes=target_quotes,
            source_member_ids=tuple(sorted(member.qq_id for member in source_members)),
            target_member_ids=tuple(sorted(member.qq_id for member in target_members)),
            source_nickname_keys=tuple(
                sorted((nickname.qq_id, nickname.name) for nickname in source_nicknames)
            ),
            target_nickname_keys=tuple(
                sorted((nickname.qq_id, nickname.name) for nickname in target_nicknames)
            ),
        )

    def _build_migration_snapshot(
        self,
        *,
        source: str,
        target: str,
        overwrite: bool,
        deduplicate: bool,
        exclude_non_member: bool,
        keep_source: bool,
        state: MigrationStateSnapshot,
        plan: _QuoteMigrationPlan,
    ) -> MigrationSnapshot:
        return MigrationSnapshot(
            source=source,
            target=target,
            overwrite=overwrite,
            deduplicate=deduplicate,
            exclude_non_member=exclude_non_member,
            keep_source=keep_source,
            state=state,
            final_candidates=tuple(
                MigrationCandidateSnapshot.from_candidate(candidate)
                for candidate in plan.final_candidates
            ),
            removed_candidates=tuple(
                MigrationRemovedCandidateSnapshot.from_removed_candidate(removed)
                for removed in plan.removed_candidates
            ),
        )

    async def _assert_snapshot_is_current(
        self, snapshot: MigrationSnapshot,
    ) -> None:
        current_state = await self._capture_migration_state(
            snapshot.source, snapshot.target,
        )
        if current_state == snapshot.state:
            return

        logger.warning(
            "群迁移预览快照已漂移: {} -> {}",
            snapshot.source,
            snapshot.target,
        )
        raise OperationError(
            "迁移预览已过期，底层数据已发生变化，请重新预览后再执行"
        )

    def _plan_from_snapshot(
        self, snapshot: MigrationSnapshot,
    ) -> _QuoteMigrationPlan:
        final_candidates = [
            candidate_snapshot.to_candidate()
            for candidate_snapshot in snapshot.final_candidates
        ]
        candidate_index = {
            (candidate.origin, candidate.original_quote_id): candidate
            for candidate in final_candidates
        }
        removed_candidates = [
            _RemovedQuoteCandidate(
                candidate=removed_snapshot.candidate.to_candidate(),
                reason=removed_snapshot.reason,
                winner=(
                    candidate_index.get(
                        (
                            removed_snapshot.winner_origin,
                            removed_snapshot.winner_original_quote_id,
                        )
                    )
                    if removed_snapshot.winner_origin is not None
                    and removed_snapshot.winner_original_quote_id is not None
                    else None
                ),
            )
            for removed_snapshot in snapshot.removed_candidates
        ]
        return _QuoteMigrationPlan(
            source_quotes=[quote.to_quote() for quote in snapshot.state.source_quotes],
            target_quotes=[quote.to_quote() for quote in snapshot.state.target_quotes],
            final_candidates=final_candidates,
            removed_candidates=removed_candidates,
        )

    @staticmethod
    def _quote_to_snapshot(quote: Quote) -> MigrationQuoteSnapshot:
        return MigrationQuoteSnapshot.from_quote(quote)

    # ------------------------------------------------------------------ #
    #  语录子迁移（原 quote_submigration_service）
    # ------------------------------------------------------------------ #

    async def _migrate_quotes(
        self,
        plan: _QuoteMigrationPlan,
        source: str,
        target: str,
        *,
        keep_source: bool,
    ) -> int:
        """
        执行非 destructive 语录迁移并显式处理关联引用。

        :param plan: 迁移计划
        :type plan: _QuoteMigrationPlan
        :param source: 源群号
        :type source: str
        :param target: 目标群号
        :type target: str
        :param keep_source: 是否保留源群语录
        :type keep_source: bool
        :returns: 迁移后的目标群语录数
        :rtype: int
        """
        reassignments: dict[str, str] = {}
        delete_with_cleanup: set[str] = set()
        delete_after_reassign: set[str] = set()

        cloned_quotes = [
            candidate.quote
            for candidate in plan.final_candidates
            if keep_source and candidate.origin == "source"
        ]
        if cloned_quotes:
            logger.info("正在为目标群 {} 克隆 {} 条源群语录...", target, len(cloned_quotes))
            await self._quote_repo.batch_clone_quotes(cloned_quotes)

        for removed in plan.removed_candidates:
            candidate = removed.candidate
            if candidate.origin == "source" and keep_source:
                continue
            if candidate.origin == "source" and removed.reason == "exclude_non_member":
                continue

            if removed.winner is not None:
                reassignments[candidate.original_quote_id] = removed.winner.quote.quote_id
                delete_after_reassign.add(candidate.original_quote_id)
            else:
                delete_with_cleanup.add(candidate.original_quote_id)

        for old_quote_id, new_quote_id in reassignments.items():
            logger.info("正在重写语录引用: {} -> {}", old_quote_id, new_quote_id)
            await self._review_repo.reassign_reviews_by_quote(
                old_quote_id=old_quote_id,
                new_quote_id=new_quote_id,
            )
            await self._mapping_repo.reassign_mappings_by_quote(
                old_quote_id=old_quote_id,
                new_quote_id=new_quote_id,
            )

        if not keep_source:
            for candidate in plan.final_candidates:
                if candidate.origin == "source":
                    await self._quote_repo.update_quote_migration_state(
                        quote_id=candidate.original_quote_id,
                        group_id=target,
                        total_show_time=candidate.quote.total_show_time,
                    )
                else:
                    await self._quote_repo.update_quote_migration_state(
                        quote_id=candidate.original_quote_id,
                        total_show_time=candidate.quote.total_show_time,
                    )
        else:
            for candidate in plan.final_candidates:
                if candidate.origin == "target":
                    await self._quote_repo.update_quote_migration_state(
                        quote_id=candidate.original_quote_id,
                        total_show_time=candidate.quote.total_show_time,
                    )

        for quote_id in delete_with_cleanup:
            logger.info("正在显式清理被移除语录 {} 的评论与消息映射...", quote_id)
            await self._review_repo.delete_reviews_by_quote(quote_id)
            await self._mapping_repo.delete_mappings_by_quote_id(quote_id)
            await self._quote_repo.delete_quote(quote_id)

        for quote_id in delete_after_reassign:
            logger.info("正在删除已完成引用重写的语录 {}...", quote_id)
            await self._quote_repo.delete_quote(quote_id)

        return len(plan.final_candidates)

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
        """
        执行用户信息迁移，返回迁移的成员数。

        :param source: 源群号
        :type source: str
        :param target: 目标群号
        :type target: str
        :param clear_member_info: 是否清除源群用户信息
        :type clear_member_info: bool
        :returns: 迁移的成员数
        :rtype: int
        """
        migrated = 0

        source_members = await self._group_member_repo.get_members_by_group(source)
        if source_members:
            source_qq_ids = [member.qq_id for member in source_members]
            logger.info(
                "正在将 {} 名成员从源群 {} 迁移至目标群 {}...",
                len(source_qq_ids),
                source,
                target,
            )
            await self._group_member_repo.batch_add_members(target, source_qq_ids)
            migrated = len(source_qq_ids)

        source_nicknames = await self._group_nickname_repo.get_nicknames_by_group(source)
        target_nicknames = await self._group_nickname_repo.get_nicknames_by_group(target)
        existing_target_pairs = {
            (nickname.qq_id, nickname.name) for nickname in target_nicknames
        }

        if source_nicknames:
            logger.info("正在迁移 {} 条群名片记录...", len(source_nicknames))
            for nickname in source_nicknames:
                nickname_key = (nickname.qq_id, nickname.name)
                if nickname_key in existing_target_pairs:
                    continue
                try:
                    await self._group_nickname_repo.add_group_nickname(
                        qq_id=nickname.qq_id,
                        group_id=target,
                        current_using=False,
                        name=nickname.name,
                    )
                    existing_target_pairs.add(nickname_key)
                except IntegrityError as exc:
                    if self._is_duplicate_conflict(exc):
                        logger.info(
                            "群名片重复，按预期跳过: qq_id={}, group_id={}, name={}",
                            nickname.qq_id,
                            target,
                            nickname.name,
                        )
                        continue
                    raise OperationError(
                        f"迁移群名片失败: qq_id={nickname.qq_id}, group_id={target}, name={nickname.name}"
                    ) from exc
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # pragma: no cover - 精确错误路径由单测覆盖
                    raise OperationError(
                        f"迁移群名片失败: qq_id={nickname.qq_id}, group_id={target}, name={nickname.name}"
                    ) from exc

        if clear_member_info:
            logger.info("正在清理源群 {} 的用户信息...", source)
            await self._group_member_repo.delete_all_members_by_group(source)
            await self._group_nickname_repo.clear_group_all_nicknames(source)

        return migrated

    # ------------------------------------------------------------------ #
    #  计划构建与内部工具方法
    # ------------------------------------------------------------------ #

    async def _build_quote_migration_plan(
        self,
        *,
        source_quotes: Sequence[Quote],
        target_quotes: Sequence[Quote],
        target: str,
        target_member_ids: set[str],
        overwrite: bool,
        deduplicate: bool,
        exclude_non_member: bool,
        keep_source: bool,
    ) -> _QuoteMigrationPlan:
        source_candidates = [
            _QuoteCandidate(
                quote=self._copy_quote(quote, group_id=target),
                origin="source",
                original_quote_id=quote.quote_id,
            )
            for quote in source_quotes
        ]
        target_candidates = [
            _QuoteCandidate(
                quote=self._copy_quote(quote),
                origin="target",
                original_quote_id=quote.quote_id,
            )
            for quote in target_quotes
        ]

        removed_candidates: list[_RemovedQuoteCandidate] = []
        if overwrite:
            final_candidates = list(source_candidates)
            removed_candidates.extend(
                _RemovedQuoteCandidate(candidate=candidate, reason="overwrite")
                for candidate in target_candidates
            )
        else:
            final_candidates = list(target_candidates) + list(source_candidates)

        if exclude_non_member:
            filtered_candidates: list[_QuoteCandidate] = []
            for candidate in final_candidates:
                if (
                    candidate.origin == "source"
                    and candidate.quote.author_id not in target_member_ids
                ):
                    removed_candidates.append(
                        _RemovedQuoteCandidate(
                            candidate=candidate,
                            reason="exclude_non_member",
                        )
                    )
                    continue
                filtered_candidates.append(candidate)
            final_candidates = filtered_candidates

        if deduplicate:
            final_candidates, deduplicated_candidates = self._deduplicate_candidates(
                final_candidates
            )
            removed_candidates.extend(deduplicated_candidates)

        if keep_source:
            await self._assign_clone_quote_ids(
                final_candidates,
                existing_quotes=[*source_quotes, *target_quotes],
            )

        return _QuoteMigrationPlan(
            source_quotes=list(source_quotes),
            target_quotes=list(target_quotes),
            final_candidates=final_candidates,
            removed_candidates=removed_candidates,
        )

    def _deduplicate_candidates(
        self,
        candidates: Sequence[_QuoteCandidate],
    ) -> tuple[list[_QuoteCandidate], list[_RemovedQuoteCandidate]]:
        winners: dict[tuple[str, Optional[str], Optional[str]], _QuoteCandidate] = {}
        ordered_winners: list[_QuoteCandidate] = []
        removed: list[_RemovedQuoteCandidate] = []

        for candidate in candidates:
            fingerprint = (
                candidate.quote.author_id,
                candidate.quote.content,
                candidate.quote.image_content_uuid,
            )
            winner = winners.get(fingerprint)
            if winner is None:
                winners[fingerprint] = candidate
                ordered_winners.append(candidate)
                continue

            winner.quote.total_show_time += candidate.quote.total_show_time
            removed.append(
                _RemovedQuoteCandidate(
                    candidate=candidate,
                    reason="deduplicated",
                    winner=winner,
                )
            )

        return ordered_winners, removed

    async def _assign_clone_quote_ids(
        self,
        candidates: Sequence[_QuoteCandidate],
        *,
        existing_quotes: Sequence[Quote],
    ) -> None:
        source_candidates = [
            candidate for candidate in candidates if candidate.origin == "source"
        ]
        if not source_candidates:
            return

        used_ids = {quote.quote_id for quote in existing_quotes}
        next_id_generator = await self._new_quote_id_generator(existing_quotes)

        for candidate in source_candidates:
            new_id = next(next_id_generator)
            while new_id in used_ids:
                new_id = next(next_id_generator)
            candidate.quote = self._copy_quote(candidate.quote, quote_id=new_id)
            used_ids.add(new_id)

    async def _new_quote_id_generator(
        self,
        existing_quotes: Sequence[Quote],
    ):
        numeric_ids = [
            parsed_id
            for parsed_id in (
                self._parse_int_quote_id(quote.quote_id) for quote in existing_quotes
            )
            if parsed_id is not None
        ]
        current_max = max(numeric_ids, default=0)
        db_max_raw = await self._quote_repo.get_max_quote_id()
        db_max = db_max_raw if isinstance(db_max_raw, int) else 0
        start_id = max(current_max, db_max) + 1
        return (str(number) for number in itertools.count(start_id))

    @staticmethod
    def _copy_quote(
        quote: Quote,
        *,
        quote_id: Optional[str] = None,
        group_id: Optional[str] = None,
        total_show_time: Optional[int] = None,
    ) -> Quote:
        return Quote(
            quote_id=quote_id or quote.quote_id,
            author_id=quote.author_id,
            group_id=group_id or quote.group_id,
            content=quote.content,
            image_content_uuid=quote.image_content_uuid,
            total_show_time=(
                quote.total_show_time if total_show_time is None else total_show_time
            ),
            time_stamp=quote.time_stamp,
        )

    @staticmethod
    def _parse_int_quote_id(value: str) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_duplicate_conflict(exc: IntegrityError) -> bool:
        message = str(exc).lower()
        return (
            "unique constraint failed" in message
            or "unique violation" in message
            or "duplicate" in message
        )

    # ------------------------------------------------------------------ #
    #  兼容保留的静态方法（供既有单测与辅助逻辑复用）
    # ------------------------------------------------------------------ #

    @staticmethod
    def _deduplicate_quotes(quotes: List[Quote]) -> List[Quote]:
        """
        基于作者、内容及图片去重，累加重复项的展示次数。

        :param quotes: 待去重的语录列表
        :type quotes: List[Quote]
        :returns: 去重后的语录列表
        :rtype: List[Quote]
        """
        merged: dict[tuple[str, Optional[str], Optional[str]], Quote] = {}
        for quote in quotes:
            fingerprint = (quote.author_id, quote.content, quote.image_content_uuid)
            if fingerprint in merged:
                merged[fingerprint].total_show_time += quote.total_show_time
            else:
                merged[fingerprint] = quote
        return list(merged.values())

    @staticmethod
    def _resolve_duplicate_ids(
        quotes: List[Quote],
        *,
        force_new_ids_for_source: bool = False,
        source_ids: Optional[set[str]] = None,
    ) -> List[Quote]:
        """
        处理重复 ID，为冲突项分配新 ID。

        :param quotes: 语录列表
        :type quotes: List[Quote]
        :param force_new_ids_for_source: 是否强制为源群语录分配新 ID
        :type force_new_ids_for_source: bool
        :param source_ids: 源群语录 ID 集合
        :type source_ids: Optional[set[str]]
        :returns: 处理后的语录列表
        :rtype: List[Quote]
        """
        if not quotes:
            return quotes

        numeric_ids = [
            parsed_id
            for parsed_id in (MigrationService._parse_int_quote_id(q.quote_id) for q in quotes)
            if parsed_id is not None
        ]
        start_id = max(numeric_ids, default=0) + 1
        new_id_gen = (str(number) for number in itertools.count(start_id))
        seen: set[str] = set()

        for quote in quotes:
            needs_new_id = (
                force_new_ids_for_source
                and source_ids is not None
                and quote.quote_id in source_ids
            ) or quote.quote_id in seen
            if needs_new_id:
                new_id = next(new_id_gen)
                while new_id in seen or (source_ids is not None and new_id in source_ids):
                    new_id = next(new_id_gen)
                quote.quote_id = new_id
            seen.add(quote.quote_id)

        return quotes
