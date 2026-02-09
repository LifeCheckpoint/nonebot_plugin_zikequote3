"""ReviewRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.reviews import Review
from nonebot_plugin_zikequote3.database.repositories.group_repository import GroupRepository
from nonebot_plugin_zikequote3.database.repositories.review_repository import ReviewRepository
from nonebot_plugin_zikequote3.database.repositories.user_repository import UserRepository
from nonebot_plugin_zikequote3.database.sa.models.quote import QuoteModel


pytestmark = pytest.mark.anyio


# ---- helpers ----

async def _seed_user_and_group(user_repo, group_repo, qq_id, group_id):
    """创建前置 user 和 group 记录。"""
    if not await user_repo.user_exists(qq_id):
        await user_repo.create_user(qq_id)
    if not await group_repo.group_exists(group_id):
        await group_repo.create_group(group_id, f"group_{group_id}")


async def _seed_quote(session, quote_id, author_id, group_id, content="test quote"):
    """直接通过 session 创建 quote 记录（Review 外键依赖）。"""
    instance = QuoteModel(
        quote_id=quote_id, author_id=author_id,
        group_id=group_id, content=content,
    )
    session.add(instance)
    await session.flush()


class TestReviewCreate:
    """创建相关测试。"""

    async def test_create_review(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u1", "rv_g1")
        await _seed_quote(async_session, "rv_q1", "rv_u1", "rv_g1")
        result = await review_repo.create_review("rv_r1", "rv_u1", "rv_q1", "好评论")
        assert isinstance(result, Review)
        assert result.review_id == "rv_r1"
        assert result.author_id == "rv_u1"
        assert result.quote_id == "rv_q1"
        assert result.content == "好评论"

    async def test_batch_create_reviews(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u2", "rv_g2")
        await _seed_quote(async_session, "rv_q2", "rv_u2", "rv_g2")
        reviews = [
            {"review_id": "rv_r2a", "author_id": "rv_u2", "quote_id": "rv_q2", "content": "评论A"},
            {"review_id": "rv_r2b", "author_id": "rv_u2", "quote_id": "rv_q2", "content": "评论B"},
        ]
        ok = await review_repo.batch_create_reviews(reviews)
        assert ok is True

    async def test_batch_create_reviews_empty(self, review_repo: ReviewRepository):
        ok = await review_repo.batch_create_reviews([])
        assert ok is True


class TestReviewRead:
    """查询相关测试。"""

    async def test_get_review_by_id(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u10", "rv_g10")
        await _seed_quote(async_session, "rv_q10", "rv_u10", "rv_g10")
        await review_repo.create_review("rv_r10", "rv_u10", "rv_q10", "内容")
        result = await review_repo.get_review_by_id("rv_r10")
        assert result is not None
        assert result.review_id == "rv_r10"

    async def test_get_review_by_id_not_found(self, review_repo: ReviewRepository):
        result = await review_repo.get_review_by_id("nonexistent")
        assert result is None

    async def test_get_reviews_by_quote(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u11", "rv_g11")
        await _seed_quote(async_session, "rv_q11", "rv_u11", "rv_g11")
        await review_repo.create_review("rv_r11a", "rv_u11", "rv_q11", "评论1")
        await review_repo.create_review("rv_r11b", "rv_u11", "rv_q11", "评论2")
        results = await review_repo.get_reviews_by_quote("rv_q11")
        assert len(results) == 2

    async def test_get_reviews_by_quote_with_limit(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u12", "rv_g12")
        await _seed_quote(async_session, "rv_q12", "rv_u12", "rv_g12")
        await review_repo.create_review("rv_r12a", "rv_u12", "rv_q12", "A")
        await review_repo.create_review("rv_r12b", "rv_u12", "rv_q12", "B")
        results = await review_repo.get_reviews_by_quote("rv_q12", limit=1)
        assert len(results) == 1

    async def test_get_reviews_by_author(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u13", "rv_g13")
        await _seed_quote(async_session, "rv_q13", "rv_u13", "rv_g13")
        await review_repo.create_review("rv_r13", "rv_u13", "rv_q13", "作者评论")
        results = await review_repo.get_reviews_by_author("rv_u13")
        assert len(results) >= 1

    async def test_get_recent_reviews(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u14", "rv_g14")
        await _seed_quote(async_session, "rv_q14", "rv_u14", "rv_g14")
        await review_repo.create_review("rv_r14", "rv_u14", "rv_q14", "最近评论")
        results = await review_repo.get_recent_reviews(limit=10)
        assert len(results) >= 1

    async def test_search_reviews_by_content(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u15", "rv_g15")
        await _seed_quote(async_session, "rv_q15", "rv_u15", "rv_g15")
        await review_repo.create_review("rv_r15", "rv_u15", "rv_q15", "独特关键词XYZ")
        results = await review_repo.search_reviews_by_content("独特关键词")
        assert len(results) >= 1
        assert any(r.review_id == "rv_r15" for r in results)

    async def test_search_reviews_no_match(self, review_repo: ReviewRepository):
        results = await review_repo.search_reviews_by_content("完全不存在的内容999")
        assert len(results) == 0


class TestReviewCount:
    """统计相关测试。"""

    async def test_count_reviews_by_quote(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u20", "rv_g20")
        await _seed_quote(async_session, "rv_q20", "rv_u20", "rv_g20")
        await review_repo.create_review("rv_r20a", "rv_u20", "rv_q20", "C1")
        await review_repo.create_review("rv_r20b", "rv_u20", "rv_q20", "C2")
        count = await review_repo.count_reviews_by_quote("rv_q20")
        assert count == 2

    async def test_count_reviews_by_quote_zero(self, review_repo: ReviewRepository):
        count = await review_repo.count_reviews_by_quote("nonexistent_quote")
        assert count == 0

    async def test_count_reviews_by_author(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u21", "rv_g21")
        await _seed_quote(async_session, "rv_q21", "rv_u21", "rv_g21")
        await review_repo.create_review("rv_r21", "rv_u21", "rv_q21", "内容")
        count = await review_repo.count_reviews_by_author("rv_u21")
        assert count >= 1

    async def test_get_review_statistics(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u22", "rv_g22")
        await _seed_quote(async_session, "rv_q22", "rv_u22", "rv_g22")
        await review_repo.create_review("rv_r22", "rv_u22", "rv_q22", "统计测试")
        stats = await review_repo.get_review_statistics()
        assert stats["total_reviews"] >= 1
        assert stats["unique_reviewers"] >= 1
        assert stats["reviewed_quotes"] >= 1


class TestReviewUpdate:
    """更新相关测试。"""

    async def test_update_review(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u30", "rv_g30")
        await _seed_quote(async_session, "rv_q30", "rv_u30", "rv_g30")
        await review_repo.create_review("rv_r30", "rv_u30", "rv_q30", "原始内容")
        ok = await review_repo.update_review("rv_r30", "更新后内容")
        assert ok is True
        updated = await review_repo.get_review_by_id("rv_r30")
        assert updated is not None
        assert updated.content == "更新后内容"

    async def test_update_nonexistent_review(self, review_repo: ReviewRepository):
        ok = await review_repo.update_review("nonexistent", "内容")
        assert ok is False


class TestReviewDelete:
    """删除相关测试。"""

    async def test_delete_review(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u40", "rv_g40")
        await _seed_quote(async_session, "rv_q40", "rv_u40", "rv_g40")
        await review_repo.create_review("rv_r40", "rv_u40", "rv_q40", "待删除")
        ok = await review_repo.delete_review("rv_r40")
        assert ok is True
        assert await review_repo.get_review_by_id("rv_r40") is None

    async def test_delete_nonexistent_review(self, review_repo: ReviewRepository):
        ok = await review_repo.delete_review("nonexistent")
        assert ok is False

    async def test_delete_reviews_by_quote(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u41", "rv_g41")
        await _seed_quote(async_session, "rv_q41", "rv_u41", "rv_g41")
        await review_repo.create_review("rv_r41a", "rv_u41", "rv_q41", "A")
        await review_repo.create_review("rv_r41b", "rv_u41", "rv_q41", "B")
        ok = await review_repo.delete_reviews_by_quote("rv_q41")
        assert ok is True
        results = await review_repo.get_reviews_by_quote("rv_q41")
        assert len(results) == 0

    async def test_delete_reviews_by_author(
        self, review_repo: ReviewRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
        async_session,
    ):
        await _seed_user_and_group(user_repo, group_repo, "rv_u42", "rv_g42")
        await _seed_quote(async_session, "rv_q42", "rv_u42", "rv_g42")
        await review_repo.create_review("rv_r42", "rv_u42", "rv_q42", "作者评论")
        ok = await review_repo.delete_reviews_by_author("rv_u42")
        assert ok is True
        count = await review_repo.count_reviews_by_author("rv_u42")
        assert count == 0
