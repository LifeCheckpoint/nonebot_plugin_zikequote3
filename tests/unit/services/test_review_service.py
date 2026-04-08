"""ReviewService 单元测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from nonebot_plugin_zikequote3.database.models.quotes import Quote
from nonebot_plugin_zikequote3.database.models.reviews import Review
from nonebot_plugin_zikequote3.exceptions import (
    PermissionDeniedError,
    QuoteNotFoundError,
    ResourceNotFoundError,
)
from nonebot_plugin_zikequote3.services.review_service import (
    AUTHOR_AI,
    AUTHOR_AI_NICKNAME,
    ReviewService,
)


# ------------------------------------------------------------------ #
#  辅助工厂
# ------------------------------------------------------------------ #

def _make_quote(quote_id: str = "q_001") -> Quote:
    return Quote(
        quote_id=quote_id,
        author_id="10001",
        group_id="12345",
        content="名言名句",
        image_content_uuid=None,
        total_show_time=0,
        time_stamp=datetime.now(),
    )


def _make_review(
    review_id: str = "r_001",
    quote_id: str = "q_001",
    author_id: str = "20001",
    content: str = "好评",
) -> Review:
    return Review(
        review_id=review_id,
        author_id=author_id,
        quote_id=quote_id,
        content=content,
        time_stamp=datetime.now(),
    )


# ------------------------------------------------------------------ #
#  添加评论
# ------------------------------------------------------------------ #

class TestAddReview:
    """测试 add_review 方法。"""

    @pytest.mark.asyncio
    async def test_add_review_success(
        self,
        review_service: ReviewService,
        mock_quote_repo: AsyncMock,
        mock_review_repo: AsyncMock,
        mock_user_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quote_by_id.return_value = _make_quote("q_001")
        mock_review_repo.create_review.return_value = _make_review()
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None

        review_id = await review_service.add_review(
            quote_id="q_001",
            author_id="20001",
            content="  好评  ",
        )

        assert isinstance(review_id, str)
        assert len(review_id) == 11
        mock_user_repo.get_by_qq_id.assert_awaited_once_with("20001")
        mock_user_repo.create_user.assert_awaited_once_with("20001")
        mock_review_repo.create_review.assert_awaited_once()
        # 验证 content 被 strip
        call_kwargs = mock_review_repo.create_review.call_args.kwargs
        assert call_kwargs["content"] == "好评"

    @pytest.mark.asyncio
    async def test_add_review_creates_ai_author_and_stable_nickname(
        self,
        review_service: ReviewService,
        mock_quote_repo: AsyncMock,
        mock_review_repo: AsyncMock,
        mock_user_repo: AsyncMock,
        mock_user_nickname_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quote_by_id.return_value = _make_quote("q_ai")
        mock_review_repo.create_review.return_value = _make_review(
            review_id="r_ai",
            quote_id="q_ai",
            author_id=AUTHOR_AI,
            content="AI 评论",
        )
        mock_user_repo.get_by_qq_id.return_value = None
        mock_user_repo.create_user.return_value = None
        mock_user_nickname_repo.get_current_nickname.return_value = None
        mock_user_nickname_repo.set_current_nickname.return_value = True

        review_id = await review_service.add_review(
            quote_id="q_ai",
            author_id=AUTHOR_AI,
            content="AI 评论",
        )

        assert isinstance(review_id, str)
        mock_user_repo.get_by_qq_id.assert_awaited_once_with(AUTHOR_AI)
        mock_user_repo.create_user.assert_awaited_once_with(AUTHOR_AI)
        mock_user_nickname_repo.set_current_nickname.assert_awaited_once_with(
            AUTHOR_AI,
            AUTHOR_AI_NICKNAME,
        )
        call_kwargs = mock_review_repo.create_review.call_args.kwargs
        assert call_kwargs["author_id"] == AUTHOR_AI

    @pytest.mark.asyncio
    async def test_add_review_quote_not_found(
        self,
        review_service: ReviewService,
        mock_quote_repo: AsyncMock,
    ) -> None:
        mock_quote_repo.get_quote_by_id.return_value = None

        with pytest.raises(QuoteNotFoundError, match="q_999"):
            await review_service.add_review(
                quote_id="q_999",
                author_id="20001",
                content="评论",
            )


# ------------------------------------------------------------------ #
#  获取评论列表
# ------------------------------------------------------------------ #

class TestGetReviewsByQuote:
    """测试 get_reviews_by_quote 方法。"""

    @pytest.mark.asyncio
    async def test_returns_reviews(
        self,
        review_service: ReviewService,
        mock_review_repo: AsyncMock,
    ) -> None:
        reviews = [_make_review("r_001"), _make_review("r_002")]
        mock_review_repo.get_reviews_by_quote.return_value = reviews

        result = await review_service.get_reviews_by_quote("q_001")

        assert len(result) == 2
        mock_review_repo.get_reviews_by_quote.assert_awaited_once_with("q_001")

    @pytest.mark.asyncio
    async def test_returns_empty_list(
        self,
        review_service: ReviewService,
        mock_review_repo: AsyncMock,
    ) -> None:
        mock_review_repo.get_reviews_by_quote.return_value = []

        result = await review_service.get_reviews_by_quote("q_empty")

        assert result == []


# ------------------------------------------------------------------ #
#  删除评论
# ------------------------------------------------------------------ #

class TestDeleteReview:
    """测试 delete_review 方法。"""

    @pytest.mark.asyncio
    async def test_delete_self_success(
        self,
        review_service: ReviewService,
        mock_review_repo: AsyncMock,
    ) -> None:
        mock_review_repo.get_review_by_id.return_value = _make_review(
            "r_001",
            author_id="20001",
        )
        mock_review_repo.delete_review.return_value = True

        await review_service.delete_review(
            "r_001",
            operator_id="20001",
            allow_delete_others=False,
        )

        mock_review_repo.delete_review.assert_awaited_once_with("r_001")

    @pytest.mark.asyncio
    async def test_delete_others_success_when_allowed(
        self,
        review_service: ReviewService,
        mock_review_repo: AsyncMock,
    ) -> None:
        mock_review_repo.get_review_by_id.return_value = _make_review(
            "r_002",
            author_id="99999",
        )
        mock_review_repo.delete_review.return_value = True

        await review_service.delete_review(
            "r_002",
            operator_id="20001",
            allow_delete_others=True,
        )

        mock_review_repo.delete_review.assert_awaited_once_with("r_002")

    @pytest.mark.asyncio
    async def test_delete_other_author_without_permission_raises(
        self,
        review_service: ReviewService,
        mock_review_repo: AsyncMock,
    ) -> None:
        mock_review_repo.get_review_by_id.return_value = _make_review(
            "r_003",
            author_id="99999",
        )

        with pytest.raises(PermissionDeniedError, match="仅可删除自己的评论"):
            await review_service.delete_review(
                "r_003",
                operator_id="20001",
                allow_delete_others=False,
            )

        mock_review_repo.delete_review.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_missing_operator_context_raises(
        self,
        review_service: ReviewService,
        mock_review_repo: AsyncMock,
    ) -> None:
        mock_review_repo.get_review_by_id.return_value = _make_review(
            "r_004",
            author_id="20001",
        )

        with pytest.raises(PermissionDeniedError, match="缺少操作者上下文"):
            await review_service.delete_review(
                "r_004",
                operator_id="",
                allow_delete_others=False,
            )

        mock_review_repo.delete_review.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        review_service: ReviewService,
        mock_review_repo: AsyncMock,
    ) -> None:
        mock_review_repo.get_review_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError, match="评论不存在"):
            await review_service.delete_review(
                "r_999",
                operator_id="20001",
                allow_delete_others=False,
            )


# ------------------------------------------------------------------ #
#  评论计数
# ------------------------------------------------------------------ #

class TestCountReviews:
    """测试 count_reviews 方法。"""

    @pytest.mark.asyncio
    async def test_count_reviews(
        self,
        review_service: ReviewService,
        mock_review_repo: AsyncMock,
    ) -> None:
        mock_review_repo.count_reviews_by_quote.return_value = 5

        result = await review_service.count_reviews("q_001")

        assert result == 5
        mock_review_repo.count_reviews_by_quote.assert_awaited_once_with("q_001")

    @pytest.mark.asyncio
    async def test_count_zero(
        self,
        review_service: ReviewService,
        mock_review_repo: AsyncMock,
    ) -> None:
        mock_review_repo.count_reviews_by_quote.return_value = 0

        result = await review_service.count_reviews("q_empty")

        assert result == 0
