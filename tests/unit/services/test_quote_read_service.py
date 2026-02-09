"""
QuoteReadService 单元测试。

覆盖：按ID查询、随机语录、搜索、语录+评论、展示次数、加权算法、图片元数据。
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from nonebot_plugin_zikequote3.database.models.images import Image
from nonebot_plugin_zikequote3.database.models.quotes import Quote
from nonebot_plugin_zikequote3.database.models.reviews import Review
from nonebot_plugin_zikequote3.exceptions import (
    ImageNotFoundError,
    QuoteNotFoundError,
)
from nonebot_plugin_zikequote3.services.new.quote_read_service import QuoteReadService


# ------------------------------------------------------------------ #
#  辅助工厂
# ------------------------------------------------------------------ #

_NOW = datetime.now(tz=timezone.utc)


def _make_quote(**overrides) -> Quote:
    defaults = {
        "quote_id": "10000000001",
        "author_id": "12345",
        "group_id": "99999",
        "content": "测试语录",
        "image_content_uuid": None,
        "total_show_time": 0,
        "time_stamp": _NOW,
    }
    defaults.update(overrides)
    return Quote(**defaults)


def _make_review(**overrides) -> Review:
    defaults = {
        "review_id": "r-001",
        "author_id": "67890",
        "quote_id": "10000000001",
        "content": "好语录！",
        "time_stamp": _NOW,
    }
    defaults.update(overrides)
    return Review(**defaults)


def _make_image(**overrides) -> Image:
    defaults = {
        "uuid": "img-001",
        "original_filename": "test.png",
        "stored_filename": "img-001.png",
        "file_path": "/images/img-001.png",
        "checksum_sha256": "abc123",
        "time_stamp": _NOW,
    }
    defaults.update(overrides)
    return Image(**defaults)


# ================================================================== #
#  单条查询
# ================================================================== #


class TestGetQuote:
    """测试 get_quote / get_quote_or_raise。"""

    @pytest.mark.asyncio
    async def test_get_quote_found(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        expected = _make_quote()
        mock_quote_repo.get_quote_by_id.return_value = expected

        result = await quote_read_service.get_quote("10000000001")

        assert result == expected
        mock_quote_repo.get_quote_by_id.assert_awaited_once_with("10000000001")

    @pytest.mark.asyncio
    async def test_get_quote_not_found(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quote_by_id.return_value = None

        result = await quote_read_service.get_quote("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_quote_or_raise_found(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        expected = _make_quote()
        mock_quote_repo.get_quote_by_id.return_value = expected

        result = await quote_read_service.get_quote_or_raise("10000000001")

        assert result == expected

    @pytest.mark.asyncio
    async def test_get_quote_or_raise_not_found(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quote_by_id.return_value = None

        with pytest.raises(QuoteNotFoundError):
            await quote_read_service.get_quote_or_raise("nonexistent")


# ================================================================== #
#  列表查询
# ================================================================== #


class TestListQuotes:
    """测试列表查询方法。"""

    @pytest.mark.asyncio
    async def test_get_quotes_by_group(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        quotes = [_make_quote(quote_id="q1"), _make_quote(quote_id="q2")]
        mock_quote_repo.get_quotes_by_group.return_value = quotes

        result = await quote_read_service.get_quotes_by_group("99999", limit=10, offset=0)

        assert len(result) == 2
        mock_quote_repo.get_quotes_by_group.assert_awaited_once_with(
            "99999", limit=10, offset=0,
        )

    @pytest.mark.asyncio
    async def test_get_quotes_by_author(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quotes_by_author.return_value = [_make_quote()]

        result = await quote_read_service.get_quotes_by_author("12345")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_quotes_by_group_and_author(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quotes_by_group_and_author.return_value = [_make_quote()]

        result = await quote_read_service.get_quotes_by_group_and_author("99999", "12345")

        assert len(result) == 1


# ================================================================== #
#  搜索
# ================================================================== #


class TestSearchQuotes:
    """测试搜索方法。"""

    @pytest.mark.asyncio
    async def test_search_quotes_by_keyword(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.search_quotes_by_content.return_value = [
            _make_quote(content="包含关键词的语录"),
        ]

        result = await quote_read_service.search_quotes("关键词", "99999")

        assert len(result) == 1
        mock_quote_repo.search_quotes_by_content.assert_awaited_once_with(
            "关键词", "99999", limit=None, offset=0,
        )

    @pytest.mark.asyncio
    async def test_search_quotes_empty_result(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.search_quotes_by_content.return_value = []

        result = await quote_read_service.search_quotes("不存在的词")

        assert len(result) == 0


# ================================================================== #
#  语录 + 评论
# ================================================================== #


class TestGetQuoteWithReviews:
    """测试 get_quote_with_reviews。"""

    @pytest.mark.asyncio
    async def test_found(
        self, quote_read_service: QuoteReadService,
        mock_quote_repo: AsyncMock, mock_review_repo: AsyncMock,
    ) -> None:
        quote = _make_quote()
        reviews = [_make_review(), _make_review(review_id="r-002", content="第二条")]
        mock_quote_repo.get_quote_by_id.return_value = quote
        mock_review_repo.get_reviews_by_quote.return_value = reviews

        result = await quote_read_service.get_quote_with_reviews("10000000001")

        assert result is not None
        q, rs = result
        assert q == quote
        assert len(rs) == 2

    @pytest.mark.asyncio
    async def test_not_found(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quote_by_id.return_value = None

        result = await quote_read_service.get_quote_with_reviews("nonexistent")

        assert result is None


# ================================================================== #
#  展示次数
# ================================================================== #


class TestIncrementShowTime:
    """测试 increment_show_time。"""

    @pytest.mark.asyncio
    async def test_increment_success(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.increment_show_time.return_value = True

        await quote_read_service.increment_show_time("10000000001")

        mock_quote_repo.increment_show_time.assert_awaited_once_with("10000000001")

    @pytest.mark.asyncio
    async def test_increment_nonexistent_raises(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.increment_show_time.return_value = False

        with pytest.raises(QuoteNotFoundError):
            await quote_read_service.increment_show_time("nonexistent")


# ================================================================== #
#  随机语录
# ================================================================== #


class TestGetRandomQuote:
    """测试 get_random_quote（均匀随机）。"""

    @pytest.mark.asyncio
    async def test_random_from_pool(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        pool = [_make_quote(quote_id=f"q{i}") for i in range(5)]
        mock_quote_repo.get_quotes_by_group.return_value = pool

        result = await quote_read_service.get_random_quote("99999")

        assert result is not None
        assert result.quote_id in {f"q{i}" for i in range(5)}

    @pytest.mark.asyncio
    async def test_random_empty_pool(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quotes_by_group.return_value = []

        result = await quote_read_service.get_random_quote("99999")

        assert result is None

    @pytest.mark.asyncio
    async def test_random_with_author_filter(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        pool = [_make_quote(quote_id="q1", author_id="12345")]
        mock_quote_repo.get_quotes_by_group_and_author.return_value = pool

        result = await quote_read_service.get_random_quote("99999", author_id="12345")

        assert result is not None
        mock_quote_repo.get_quotes_by_group_and_author.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_random_with_keyword_filter(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        pool = [
            _make_quote(quote_id="q1", content="包含关键词"),
            _make_quote(quote_id="q2", content="不包含"),
        ]
        mock_quote_repo.get_quotes_by_group.return_value = pool

        result = await quote_read_service.get_random_quote("99999", keyword="关键词")

        assert result is not None
        assert result.quote_id == "q1"


# ================================================================== #
#  加权随机语录
# ================================================================== #


class TestGetRandomQuoteWeighted:
    """测试 get_random_quote_weighted（IFW / LogIFW）。"""

    @pytest.mark.asyncio
    async def test_ifw_algorithm(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        pool = [
            _make_quote(quote_id="q1", total_show_time=10),
            _make_quote(quote_id="q2", total_show_time=0),
        ]
        mock_quote_repo.get_quotes_by_group.return_value = pool

        result = await quote_read_service.get_random_quote_weighted(
            "99999", algorithm="ifw", lambda_=1.0, a_=1.0,
        )

        assert result is not None
        assert result.quote_id in {"q1", "q2"}

    @pytest.mark.asyncio
    async def test_logifw_algorithm(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        pool = [
            _make_quote(quote_id="q1", total_show_time=5),
            _make_quote(quote_id="q2", total_show_time=1),
        ]
        mock_quote_repo.get_quotes_by_group.return_value = pool

        result = await quote_read_service.get_random_quote_weighted(
            "99999", algorithm="logifw", lambda_=1.0, a_=1.0, log_a_=2.0,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_unknown_algorithm_fallback(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        pool = [_make_quote(quote_id="q1")]
        mock_quote_repo.get_quotes_by_group.return_value = pool

        result = await quote_read_service.get_random_quote_weighted(
            "99999", algorithm="unknown_algo",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_weighted_empty_pool(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quotes_by_group.return_value = []

        result = await quote_read_service.get_random_quote_weighted("99999")

        assert result is None

    @pytest.mark.asyncio
    async def test_weighted_single_item(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        pool = [_make_quote(quote_id="only")]
        mock_quote_repo.get_quotes_by_group.return_value = pool

        result = await quote_read_service.get_random_quote_weighted("99999")

        assert result is not None
        assert result.quote_id == "only"


# ================================================================== #
#  加权算法静态方法
# ================================================================== #


class TestWeightAlgorithms:
    """测试 _calc_ifw_weights / _calc_logifw_weights 静态方法。"""

    def test_ifw_weights_sum_to_one(self) -> None:
        quotes = [
            _make_quote(quote_id="q1", total_show_time=0),
            _make_quote(quote_id="q2", total_show_time=5),
            _make_quote(quote_id="q3", total_show_time=10),
        ]
        weights = QuoteReadService._calc_ifw_weights(quotes, lambda_=1.0, a_=1.0)

        assert abs(sum(weights.values()) - 1.0) < 1e-9
        # 展示次数少的权重应更高
        assert weights["q1"] > weights["q3"]

    def test_logifw_weights_sum_to_one(self) -> None:
        quotes = [
            _make_quote(quote_id="q1", total_show_time=0),
            _make_quote(quote_id="q2", total_show_time=5),
            _make_quote(quote_id="q3", total_show_time=10),
        ]
        weights = QuoteReadService._calc_logifw_weights(
            quotes, lambda_=1.0, a_=1.0, log_a_=2.0,
        )

        assert abs(sum(weights.values()) - 1.0) < 1e-9
        assert weights["q1"] > weights["q3"]

    def test_ifw_equal_show_times_uniform(self) -> None:
        """所有语录展示次数相同时，权重应均匀。"""
        quotes = [
            _make_quote(quote_id=f"q{i}", total_show_time=5) for i in range(4)
        ]
        weights = QuoteReadService._calc_ifw_weights(quotes, lambda_=1.0, a_=1.0)

        expected = 1.0 / 4
        for w in weights.values():
            assert abs(w - expected) < 1e-9


# ================================================================== #
#  图片元数据
# ================================================================== #


class TestImageMetadata:
    """测试图片元数据查询。"""

    @pytest.mark.asyncio
    async def test_get_image_metadata_found(
        self, quote_read_service: QuoteReadService, mock_image_repo: AsyncMock,
    ) -> None:
        img = _make_image()
        mock_image_repo.get_by_uuid.return_value = img

        result = await quote_read_service.get_image_metadata("img-001")

        assert result == img

    @pytest.mark.asyncio
    async def test_get_image_metadata_not_found(
        self, quote_read_service: QuoteReadService, mock_image_repo: AsyncMock,
    ) -> None:
        mock_image_repo.get_by_uuid.return_value = None

        result = await quote_read_service.get_image_metadata("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_image_metadata_or_raise_found(
        self, quote_read_service: QuoteReadService, mock_image_repo: AsyncMock,
    ) -> None:
        img = _make_image()
        mock_image_repo.get_by_uuid.return_value = img

        result = await quote_read_service.get_image_metadata_or_raise("img-001")

        assert result == img

    @pytest.mark.asyncio
    async def test_get_image_metadata_or_raise_not_found(
        self, quote_read_service: QuoteReadService, mock_image_repo: AsyncMock,
    ) -> None:
        mock_image_repo.get_by_uuid.return_value = None

        with pytest.raises(ImageNotFoundError):
            await quote_read_service.get_image_metadata_or_raise("nonexistent")


# ================================================================== #
#  作者显示名称
# ================================================================== #


class TestGetQuoteAuthorDisplayName:
    """测试 get_quote_author_display_name。"""

    @pytest.mark.asyncio
    async def test_returns_display_name(
        self, quote_read_service: QuoteReadService,
        mock_quote_repo: AsyncMock,
        mock_group_nickname_repo: AsyncMock,
    ) -> None:
        quote = _make_quote(author_id="12345")
        mock_quote_repo.get_quote_by_id.return_value = quote
        # UserService.get_display_name 会查群名片 → 昵称 → QQ号
        # 这里 mock group_nickname_repo 返回群名片
        mock_group_nickname_repo.get_current_group_nickname.return_value = "测试昵称"

        result = await quote_read_service.get_quote_author_display_name(
            "10000000001", "99999",
        )

        assert result == "测试昵称"

    @pytest.mark.asyncio
    async def test_quote_not_found_raises(
        self, quote_read_service: QuoteReadService, mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quote_by_id.return_value = None

        with pytest.raises(QuoteNotFoundError):
            await quote_read_service.get_quote_author_display_name(
                "nonexistent", "99999",
            )
