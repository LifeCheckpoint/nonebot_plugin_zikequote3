"""
StatisticsService 单元测试。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from nonebot_plugin_zikequote3.database.models.group_members import GroupMember
from nonebot_plugin_zikequote3.database.models.quotes import Quote
from nonebot_plugin_zikequote3.exceptions import ResourceNotFoundError, ValidationException
from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService


# ---------------------------------------------------------------------------
# get_group_ranking
# ---------------------------------------------------------------------------


class TestGetGroupRanking:
    """get_group_ranking 测试。"""

    async def test_returns_ranking_list(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        mock_quote_repo.get_author_ranking.return_value = [
            ("111", 10),
            ("222", 5),
        ]
        result = await statistics_service.get_group_ranking("g1", limit=10)
        assert len(result) == 2
        assert result[0] == {"author_id": "111", "quote_count": 10}
        assert result[1] == {"author_id": "222", "quote_count": 5}
        mock_quote_repo.get_author_ranking.assert_awaited_once_with("g1", limit=10)

    async def test_raises_when_no_data(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        mock_quote_repo.get_author_ranking.return_value = []
        with pytest.raises(ResourceNotFoundError):
            await statistics_service.get_group_ranking("g1")


# ---------------------------------------------------------------------------
# get_group_statistics
# ---------------------------------------------------------------------------


class TestGetGroupStatistics:
    async def test_returns_stats_dict(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        expected = {
            "total_quotes": 100,
            "unique_authors": 10,
            "total_shows": 500,
            "avg_shows": 5.0,
        }
        mock_quote_repo.get_quote_statistics_by_group.return_value = expected
        result = await statistics_service.get_group_statistics("g1")
        assert result == expected


# ---------------------------------------------------------------------------
# get_personal_quotes
# ---------------------------------------------------------------------------


def _make_quote(qid: str, author: str = "111", group: str = "g1") -> Quote:
    return Quote(
        quote_id=qid,
        author_id=author,
        group_id=group,
        content=f"content-{qid}",
        image_content_uuid=None,
        total_show_time=0,
        time_stamp=datetime(2025, 1, 1),
    )


class TestGetPersonalQuotes:
    async def test_default_pagination(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        quotes = [_make_quote(str(i)) for i in range(5)]
        mock_quote_repo.get_quotes_by_group_and_author.return_value = quotes

        result, total, real_from, real_to = await statistics_service.get_personal_quotes(
            "111", "g1", max_count=3
        )
        assert total == 5
        assert real_from == 2
        assert real_to == 4
        assert len(result) == 3

    async def test_from_index_only(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        quotes = [_make_quote(str(i)) for i in range(10)]
        mock_quote_repo.get_quotes_by_group_and_author.return_value = quotes

        result, total, real_from, real_to = await statistics_service.get_personal_quotes(
            "111", "g1", from_index=3, max_count=4
        )
        assert total == 10
        assert real_from == 2  # 3-1
        assert real_to == 5   # 2+4-1
        assert len(result) == 4

    async def test_from_and_to_index(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        quotes = [_make_quote(str(i)) for i in range(10)]
        mock_quote_repo.get_quotes_by_group_and_author.return_value = quotes

        result, total, real_from, real_to = await statistics_service.get_personal_quotes(
            "111", "g1", from_index=2, to_index=5
        )
        assert total == 10
        assert real_from == 1
        assert real_to == 4
        assert len(result) == 4

    async def test_raises_when_no_quotes(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        mock_quote_repo.get_quotes_by_group_and_author.return_value = []
        with pytest.raises(ResourceNotFoundError):
            await statistics_service.get_personal_quotes("111", "g1")


# ---------------------------------------------------------------------------
# search_quotes
# ---------------------------------------------------------------------------


class TestSearchQuotes:
    async def test_keyword_search(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        quotes = [
            _make_quote("1"),
            _make_quote("2"),
        ]
        quotes[0].content = "hello world"
        quotes[1].content = "goodbye"
        mock_quote_repo.get_quotes_by_group.return_value = quotes

        result, total = await statistics_service.search_quotes("hello", "g1")
        assert total == 1
        assert result[0].quote_id == "1"

    async def test_regex_search(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        quotes = [_make_quote("1"), _make_quote("2")]
        quotes[0].content = "abc123"
        quotes[1].content = "xyz"
        mock_quote_repo.get_quotes_by_group.return_value = quotes

        result, total = await statistics_service.search_quotes(
            r"\d+", "g1", use_regex=True
        )
        assert total == 1

    async def test_invalid_regex_raises(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        mock_quote_repo.get_quotes_by_group.return_value = [_make_quote("1")]
        with pytest.raises(ValidationException):
            await statistics_service.search_quotes("[invalid", "g1", use_regex=True)

    async def test_max_results_truncation(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        quotes = [_make_quote(str(i)) for i in range(10)]
        for q in quotes:
            q.content = "match"
        mock_quote_repo.get_quotes_by_group.return_value = quotes

        result, total = await statistics_service.search_quotes(
            "match", "g1", max_results=3
        )
        assert total == 10
        assert len(result) == 3

    async def test_filter_by_author(
        self, statistics_service: StatisticsService, mock_quote_repo: AsyncMock
    ) -> None:
        q1 = _make_quote("1", author="aaa")
        q2 = _make_quote("2", author="bbb")
        q1.content = "match"
        q2.content = "match"
        mock_quote_repo.get_quotes_by_group.return_value = [q1, q2]

        result, total = await statistics_service.search_quotes(
            "match", "g1", author_id="aaa"
        )
        assert total == 1
        assert result[0].author_id == "aaa"
