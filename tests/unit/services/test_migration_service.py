"""
MigrationService 单元测试。
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from unittest.mock import AsyncMock

import pytest

from nonebot_plugin_zikequote3.database.models.group_members import GroupMember
from nonebot_plugin_zikequote3.database.models.group_nicknames import GroupNickname
from nonebot_plugin_zikequote3.database.models.quotes import Quote
from nonebot_plugin_zikequote3.exceptions import OperationError
from nonebot_plugin_zikequote3.services.migration_service import MigrationService


def _make_quote(
    qid: str,
    author: str = "111",
    group: str = "src",
    content: str = "text",
) -> Quote:
    return Quote(
        quote_id=qid,
        author_id=author,
        group_id=group,
        content=content,
        image_content_uuid=None,
        total_show_time=1,
        time_stamp=datetime(2025, 1, 1),
    )


def _make_member(qq_id: str, group_id: str = "src") -> GroupMember:
    return GroupMember(qq_id=qq_id, group_id=group_id)


def _make_nickname(
    qq_id: str, group_id: str, name: str, current: bool = True
) -> GroupNickname:
    return GroupNickname(
        qq_id=qq_id, group_id=group_id, name=name, current_using=current
    )


# ---------------------------------------------------------------------------
# _deduplicate_quotes (static)
# ---------------------------------------------------------------------------


class TestDeduplicateQuotes:
    def test_no_duplicates(self) -> None:
        quotes = [_make_quote("1", content="a"), _make_quote("2", content="b")]
        result = MigrationService._deduplicate_quotes(quotes)
        assert len(result) == 2

    def test_merges_duplicates(self) -> None:
        q1 = _make_quote("1", author="111", content="same")
        q2 = _make_quote("2", author="111", content="same")
        q1.total_show_time = 3
        q2.total_show_time = 5
        result = MigrationService._deduplicate_quotes([q1, q2])
        assert len(result) == 1
        assert result[0].total_show_time == 8


# ---------------------------------------------------------------------------
# _resolve_duplicate_ids (static)
# ---------------------------------------------------------------------------


class TestResolveDuplicateIds:
    def test_no_conflicts(self) -> None:
        quotes = [_make_quote("1"), _make_quote("2")]
        result = MigrationService._resolve_duplicate_ids(quotes)
        ids = [q.quote_id for q in result]
        assert ids == ["1", "2"]

    def test_resolves_conflicts(self) -> None:
        quotes = [_make_quote("1"), _make_quote("1")]
        result = MigrationService._resolve_duplicate_ids(quotes)
        ids = [q.quote_id for q in result]
        assert len(set(ids)) == 2  # all unique

    def test_force_new_ids_for_source(self) -> None:
        quotes = [_make_quote("1"), _make_quote("2")]
        source_ids = {"1"}
        result = MigrationService._resolve_duplicate_ids(
            quotes, force_new_ids_for_source=True, source_ids=source_ids
        )
        assert result[0].quote_id != "1"  # source id replaced
        assert result[1].quote_id == "2"  # non-source kept


# ---------------------------------------------------------------------------
# prepare_migration
# ---------------------------------------------------------------------------


class TestPrepareMigration:
    async def test_merge_mode(
        self,
        migration_service: MigrationService,
        mock_quote_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quotes_by_group.side_effect = lambda gid: (
            [_make_quote("1", group="src")] if gid == "src"
            else [_make_quote("2", group="tgt")]
        )
        mock_group_member_repo.get_members_by_group.side_effect = lambda gid: (
            [_make_member("111", "src")] if gid == "src"
            else [_make_member("222", "tgt")]
        )

        info = await migration_service.prepare_migration(
            "src", "tgt", overwrite=False
        )
        assert info["source_count"] == 1
        assert info["target_count"] == 1
        assert info["final_count"] == 2
        assert info["before_members"] == 1
        assert info["after_members"] == 2

    async def test_overwrite_mode(
        self,
        migration_service: MigrationService,
        mock_quote_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quotes_by_group.side_effect = lambda gid: (
            [_make_quote("1", group="src")] if gid == "src"
            else [_make_quote("2", group="tgt"), _make_quote("3", group="tgt")]
        )
        mock_group_member_repo.get_members_by_group.return_value = []

        info = await migration_service.prepare_migration(
            "src", "tgt", overwrite=True
        )
        assert info["final_count"] == 1  # only source


# ---------------------------------------------------------------------------
# execute_migration
# ---------------------------------------------------------------------------


class TestExecuteMigration:
    async def test_basic_migration_clones_source_quotes_without_group_wide_delete(
        self,
        migration_service: MigrationService,
        mock_quote_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quotes_by_group.side_effect = lambda gid: (
            [_make_quote("1", group="src")] if gid == "src" else []
        )
        mock_quote_repo.get_max_quote_id.return_value = 9
        mock_quote_repo.batch_clone_quotes.return_value = True
        mock_group_member_repo.get_members_by_group.side_effect = lambda gid: (
            [_make_member("111", "src")] if gid == "src" else []
        )
        mock_group_nickname_repo.get_nicknames_by_group.return_value = []
        mock_group_member_repo.batch_add_members.return_value = True

        result = await migration_service.execute_migration(
            [_make_quote("10", group="tgt")], "src", "tgt"
        )

        assert result["quotes_migrated"] == 1
        assert result["members_migrated"] == 1
        mock_quote_repo.batch_clone_quotes.assert_awaited_once()
        mock_quote_repo.delete_quotes_by_group.assert_not_awaited()

    async def test_migration_with_clear_member_info(
        self,
        migration_service: MigrationService,
        mock_quote_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quotes_by_group.side_effect = lambda gid: []
        mock_group_member_repo.get_members_by_group.return_value = []
        mock_group_nickname_repo.get_nicknames_by_group.return_value = []

        await migration_service.execute_migration(
            [], "src", "tgt", clear_member_info=True
        )
        mock_group_member_repo.delete_all_members_by_group.assert_awaited_with("src")
        mock_group_nickname_repo.clear_group_all_nicknames.assert_awaited_with("src")

    async def test_migration_move_mode_updates_source_quote_in_place(
        self,
        migration_service: MigrationService,
        mock_quote_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
    ) -> None:
        source_quote = _make_quote("1", group="src")
        mock_quote_repo.get_quotes_by_group.side_effect = lambda gid: (
            [source_quote] if gid == "src" else []
        )
        mock_quote_repo.update_quote_migration_state.return_value = True
        mock_group_member_repo.get_members_by_group.return_value = []
        mock_group_nickname_repo.get_nicknames_by_group.return_value = []

        await migration_service.execute_migration(
            [_make_quote("1", group="tgt")], "src", "tgt", keep_source=False
        )

        mock_quote_repo.update_quote_migration_state.assert_awaited_once_with(
            quote_id="1",
            group_id="tgt",
            total_show_time=1,
        )
        mock_quote_repo.delete_quotes_by_group.assert_not_awaited()

    async def test_migration_reassigns_reviews_and_mappings_when_deduplicate_removes_quote(
        self,
        migration_service: MigrationService,
        mock_quote_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
        mock_review_repo: AsyncMock,
        mock_mapping_repo: AsyncMock,
    ) -> None:
        source_quote = _make_quote("1", group="src", content="same")
        target_quote = _make_quote("2", group="tgt", content="same")
        target_quote.total_show_time = 4
        mock_quote_repo.get_quotes_by_group.side_effect = lambda gid: (
            [source_quote] if gid == "src" else [target_quote]
        )
        mock_quote_repo.update_quote_migration_state.return_value = True
        mock_quote_repo.delete_quote.return_value = True
        mock_group_member_repo.get_members_by_group.return_value = []
        mock_group_nickname_repo.get_nicknames_by_group.return_value = []
        mock_review_repo.reassign_reviews_by_quote.return_value = True
        mock_mapping_repo.reassign_mappings_by_quote.return_value = True

        result = await migration_service.execute_migration(
            [],
            "src",
            "tgt",
            keep_source=False,
            deduplicate=True,
        )

        assert result["quotes_migrated"] == 1
        mock_review_repo.reassign_reviews_by_quote.assert_awaited_once_with(
            old_quote_id="1",
            new_quote_id="2",
        )
        mock_mapping_repo.reassign_mappings_by_quote.assert_awaited_once_with(
            old_quote_id="1",
            new_quote_id="2",
        )
        mock_quote_repo.delete_quote.assert_awaited_once_with("1")
        mock_quote_repo.delete_quotes_by_group.assert_not_awaited()

    async def test_group_nickname_failure_is_not_silently_swallowed(
        self,
        migration_service: MigrationService,
        mock_quote_repo: AsyncMock,
        mock_group_member_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quotes_by_group.side_effect = lambda gid: []
        mock_group_member_repo.get_members_by_group.return_value = []
        mock_group_nickname_repo.get_nicknames_by_group.side_effect = [
            [_make_nickname("111", "src", "card")],
            [],
        ]
        mock_group_nickname_repo.add_group_nickname.side_effect = RuntimeError("boom")

        with pytest.raises(OperationError, match="迁移群名片失败"):
            await migration_service.execute_migration([], "src", "tgt")
