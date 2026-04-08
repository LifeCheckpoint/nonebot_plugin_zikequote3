"""QuoteRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.quotes import Quote, QuoteCreate
from nonebot_plugin_zikequote3.database.repositories.group_repository import GroupRepository
from nonebot_plugin_zikequote3.database.repositories.quote_repository import QuoteRepository
from nonebot_plugin_zikequote3.database.repositories.user_repository import UserRepository


pytestmark = pytest.mark.anyio


# ---- helpers ----

async def _seed_user_and_group(user_repo, group_repo, qq_id, group_id):
    """创建前置 user 和 group 记录。"""
    if not await user_repo.user_exists(qq_id):
        await user_repo.create_user(qq_id)
    if not await group_repo.group_exists(group_id):
        await group_repo.create_group(group_id, f"group_{group_id}")


# ---- 创建测试 ----

class TestQuoteCreate:
    """创建相关测试。"""

    async def test_create_quote(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u1", "qt_g1")
        result = await quote_repo.create_quote("qt_q1", "qt_u1", "qt_g1", content="测试语录")
        assert isinstance(result, Quote)
        assert result.quote_id == "qt_q1"
        assert result.author_id == "qt_u1"
        assert result.group_id == "qt_g1"
        assert result.content == "测试语录"
        assert result.total_show_time == 0

    async def test_create_quote_with_image(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u2", "qt_g2")
        result = await quote_repo.create_quote(
            "qt_q2", "qt_u2", "qt_g2",
            content="带图语录", image_content_uuid=None,
        )
        assert isinstance(result, Quote)
        assert result.quote_id == "qt_q2"

    async def test_batch_create_quotes(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u3", "qt_g3")
        dtos = [
            QuoteCreate(quote_id="qt_q3a", author_id="qt_u3", group_id="qt_g3", content="批量1"),
            QuoteCreate(quote_id="qt_q3b", author_id="qt_u3", group_id="qt_g3", content="批量2"),
        ]
        ok = await quote_repo.batch_create_quotes(dtos)
        assert ok is True

    async def test_batch_create_quotes_empty(self, quote_repo: QuoteRepository):
        ok = await quote_repo.batch_create_quotes([])
        assert ok is True

    async def test_batch_clone_quotes(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u4", "qt_g4")
        await _seed_user_and_group(user_repo, group_repo, "qt_u4", "qt_g4_target")
        source = await quote_repo.create_quote("qt_q4", "qt_u4", "qt_g4", content="原语录")
        clone = Quote(
            quote_id="qt_q4_clone",
            author_id=source.author_id,
            group_id="qt_g4_target",
            content=source.content,
            image_content_uuid=source.image_content_uuid,
            total_show_time=source.total_show_time,
            time_stamp=source.time_stamp,
        )

        ok = await quote_repo.batch_clone_quotes([clone])
        assert ok is True
        cloned = await quote_repo.get_quote_by_id("qt_q4_clone")
        assert cloned is not None
        assert cloned.group_id == "qt_g4_target"
        assert cloned.time_stamp == source.time_stamp


# ---- 单条查询测试 ----

class TestQuoteReadSingle:
    """单条查询相关测试。"""

    async def test_get_quote_by_id(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u10", "qt_g10")
        await quote_repo.create_quote("qt_q10", "qt_u10", "qt_g10", content="查询测试")
        result = await quote_repo.get_quote_by_id("qt_q10")
        assert result is not None
        assert result.quote_id == "qt_q10"
        assert result.content == "查询测试"

    async def test_get_quote_by_id_not_found(self, quote_repo: QuoteRepository):
        result = await quote_repo.get_quote_by_id("nonexistent")
        assert result is None

    async def test_get_random_quote(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u11", "qt_g11")
        await quote_repo.create_quote("qt_q11", "qt_u11", "qt_g11", content="随机测试")
        result = await quote_repo.get_random_quote(group_id="qt_g11")
        assert result is not None
        assert result.group_id == "qt_g11"

    async def test_get_random_quote_no_filter(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u12", "qt_g12")
        await quote_repo.create_quote("qt_q12", "qt_u12", "qt_g12", content="随机无过滤")
        result = await quote_repo.get_random_quote()
        assert result is not None

    async def test_get_random_quote_empty_group(self, quote_repo: QuoteRepository):
        result = await quote_repo.get_random_quote(group_id="nonexistent_group")
        assert result is None


# ---- 列表查询测试 ----

class TestQuoteReadList:
    """列表查询相关测试。"""

    async def test_get_quotes_by_group(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u20", "qt_g20")
        await quote_repo.create_quote("qt_q20a", "qt_u20", "qt_g20", content="群语录1")
        await quote_repo.create_quote("qt_q20b", "qt_u20", "qt_g20", content="群语录2")
        results = await quote_repo.get_quotes_by_group("qt_g20")
        assert len(results) == 2

    async def test_get_quotes_by_group_with_limit(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u21", "qt_g21")
        await quote_repo.create_quote("qt_q21a", "qt_u21", "qt_g21", content="A")
        await quote_repo.create_quote("qt_q21b", "qt_u21", "qt_g21", content="B")
        results = await quote_repo.get_quotes_by_group("qt_g21", limit=1)
        assert len(results) == 1

    async def test_get_quotes_by_author(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u22", "qt_g22")
        await quote_repo.create_quote("qt_q22", "qt_u22", "qt_g22", content="作者语录")
        results = await quote_repo.get_quotes_by_author("qt_u22")
        assert len(results) >= 1

    async def test_get_quotes_by_group_and_author(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u23", "qt_g23")
        await quote_repo.create_quote("qt_q23", "qt_u23", "qt_g23", content="群+作者")
        results = await quote_repo.get_quotes_by_group_and_author("qt_g23", "qt_u23")
        assert len(results) >= 1

    async def test_get_quotes_by_group_and_author_with_pagination(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u24", "qt_g24")
        await quote_repo.create_quote("qt_q24a", "qt_u24", "qt_g24", content="分页1")
        await quote_repo.create_quote("qt_q24b", "qt_u24", "qt_g24", content="分页2")
        results = await quote_repo.get_quotes_by_group_and_author(
            "qt_g24", "qt_u24", limit=1, offset=1,
        )
        assert len(results) == 1

    async def test_get_quotes_by_group_empty(self, quote_repo: QuoteRepository):
        results = await quote_repo.get_quotes_by_group("nonexistent_group")
        assert len(results) == 0


# ---- 搜索测试 ----

class TestQuoteSearch:
    """搜索相关测试。"""

    async def test_search_quotes_by_content(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u30", "qt_g30")
        await quote_repo.create_quote("qt_q30", "qt_u30", "qt_g30", content="独特搜索关键词ABC")
        results = await quote_repo.search_quotes_by_content("独特搜索关键词")
        assert len(results) >= 1
        assert any(r.quote_id == "qt_q30" for r in results)

    async def test_search_quotes_by_content_with_group(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u31", "qt_g31")
        await quote_repo.create_quote("qt_q31", "qt_u31", "qt_g31", content="群搜索关键词DEF")
        results = await quote_repo.search_quotes_by_content("群搜索关键词", group_id="qt_g31")
        assert len(results) >= 1

    async def test_search_quotes_no_match(self, quote_repo: QuoteRepository):
        results = await quote_repo.search_quotes_by_content("完全不存在的内容XYZ999")
        assert len(results) == 0

    async def test_search_quotes_with_limit(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u32", "qt_g32")
        await quote_repo.create_quote("qt_q32a", "qt_u32", "qt_g32", content="限制搜索1")
        await quote_repo.create_quote("qt_q32b", "qt_u32", "qt_g32", content="限制搜索2")
        results = await quote_repo.search_quotes_by_content("限制搜索", limit=1)
        assert len(results) == 1


# ---- 热门 / 最近 ----

class TestQuotePopularRecent:
    """热门和最近语录测试。"""

    async def test_get_popular_quotes(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u40", "qt_g40")
        await quote_repo.create_quote(
            "qt_q40", "qt_u40", "qt_g40", content="热门", total_show_time=100,
        )
        results = await quote_repo.get_popular_quotes(group_id="qt_g40", limit=5)
        assert len(results) >= 1
        assert results[0].total_show_time == 100

    async def test_get_recent_quotes(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u41", "qt_g41")
        await quote_repo.create_quote("qt_q41", "qt_u41", "qt_g41", content="最近语录")
        results = await quote_repo.get_recent_quotes(group_id="qt_g41", limit=5)
        assert len(results) >= 1

    async def test_get_recent_quotes_no_filter(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u42", "qt_g42")
        await quote_repo.create_quote("qt_q42", "qt_u42", "qt_g42", content="最近无过滤")
        results = await quote_repo.get_recent_quotes(limit=10)
        assert len(results) >= 1


# ---- 存在性检查 ----

class TestQuoteExists:
    """存在性检查测试。"""

    async def test_check_quote_exists_by_author_content_true(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u50", "qt_g50")
        await quote_repo.create_quote("qt_q50", "qt_u50", "qt_g50", content="存在性检查")
        exists = await quote_repo.check_quote_exists_by_author_content("qt_u50", "存在性检查")
        assert exists is True

    async def test_check_quote_exists_by_author_content_false(
        self, quote_repo: QuoteRepository,
    ):
        exists = await quote_repo.check_quote_exists_by_author_content("no_user", "no_content")
        assert exists is False


# ---- 统计测试 ----

class TestQuoteCount:
    """统计相关测试。"""

    async def test_count_quotes_by_group(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u60", "qt_g60")
        await quote_repo.create_quote("qt_q60a", "qt_u60", "qt_g60", content="统计1")
        await quote_repo.create_quote("qt_q60b", "qt_u60", "qt_g60", content="统计2")
        count = await quote_repo.count_quotes_by_group("qt_g60")
        assert count == 2

    async def test_count_quotes_by_group_zero(self, quote_repo: QuoteRepository):
        count = await quote_repo.count_quotes_by_group("nonexistent_group")
        assert count == 0

    async def test_count_quotes_by_author(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u61", "qt_g61")
        await quote_repo.create_quote("qt_q61", "qt_u61", "qt_g61", content="作者统计")
        count = await quote_repo.count_quotes_by_author("qt_u61")
        assert count >= 1

    async def test_count_quotes_by_group_and_author(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u62", "qt_g62")
        await quote_repo.create_quote("qt_q62", "qt_u62", "qt_g62", content="群作者统计")
        count = await quote_repo.count_quotes_by_group_and_author("qt_g62", "qt_u62")
        assert count == 1

    async def test_get_quote_statistics_by_group(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u63", "qt_g63")
        await quote_repo.create_quote(
            "qt_q63", "qt_u63", "qt_g63", content="统计信息", total_show_time=5,
        )
        stats = await quote_repo.get_quote_statistics_by_group("qt_g63")
        assert stats["total_quotes"] == 1
        assert stats["unique_authors"] == 1
        assert stats["total_shows"] == 5
        assert stats["avg_shows"] == 5.0

    async def test_get_quote_statistics_by_group_empty(
        self, quote_repo: QuoteRepository,
    ):
        stats = await quote_repo.get_quote_statistics_by_group("nonexistent_group")
        assert stats["total_quotes"] == 0
        assert stats["unique_authors"] == 0
        assert stats["total_shows"] == 0
        assert stats["avg_shows"] == 0.0

    async def test_get_author_ranking(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u64a", "qt_g64")
        await _seed_user_and_group(user_repo, group_repo, "qt_u64b", "qt_g64")
        await quote_repo.create_quote("qt_q64a", "qt_u64a", "qt_g64", content="排行1")
        await quote_repo.create_quote("qt_q64b", "qt_u64a", "qt_g64", content="排行2")
        await quote_repo.create_quote("qt_q64c", "qt_u64b", "qt_g64", content="排行3")
        ranking = await quote_repo.get_author_ranking("qt_g64", limit=10)
        assert len(ranking) == 2
        # 第一名应该是 qt_u64a（2条）
        assert ranking[0][0] == "qt_u64a"
        assert ranking[0][1] == 2
        assert ranking[1][0] == "qt_u64b"
        assert ranking[1][1] == 1

    async def test_get_author_ranking_empty(self, quote_repo: QuoteRepository):
        ranking = await quote_repo.get_author_ranking("nonexistent_group")
        assert len(ranking) == 0

    async def test_get_max_quote_id(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u65", "qt_g65")
        await quote_repo.create_quote("100", "qt_u65", "qt_g65", content="最大ID")
        max_id = await quote_repo.get_max_quote_id()
        assert max_id >= 100


# ---- 更新测试 ----

class TestQuoteUpdate:
    """更新相关测试。"""

    async def test_update_quote_content(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u70", "qt_g70")
        await quote_repo.create_quote("qt_q70", "qt_u70", "qt_g70", content="原始内容")
        ok = await quote_repo.update_quote("qt_q70", content="更新后内容")
        assert ok is True
        updated = await quote_repo.get_quote_by_id("qt_q70")
        assert updated is not None
        assert updated.content == "更新后内容"

    async def test_update_quote_show_time(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u71", "qt_g71")
        await quote_repo.create_quote("qt_q71", "qt_u71", "qt_g71", content="展示次数")
        ok = await quote_repo.update_quote("qt_q71", total_show_time=42)
        assert ok is True
        updated = await quote_repo.get_quote_by_id("qt_q71")
        assert updated is not None
        assert updated.total_show_time == 42

    async def test_update_quote_no_fields(self, quote_repo: QuoteRepository):
        """不传任何字段时应返回 True（无操作）。"""
        ok = await quote_repo.update_quote("any_id")
        assert ok is True

    async def test_update_quote_migration_state(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u71a", "qt_g71a")
        await _seed_user_and_group(user_repo, group_repo, "qt_u71a", "qt_g71b")
        await quote_repo.create_quote("qt_q71a", "qt_u71a", "qt_g71a", content="迁移态")

        ok = await quote_repo.update_quote_migration_state(
            "qt_q71a",
            group_id="qt_g71b",
            total_show_time=7,
        )
        assert ok is True
        updated = await quote_repo.get_quote_by_id("qt_q71a")
        assert updated is not None
        assert updated.group_id == "qt_g71b"
        assert updated.total_show_time == 7

    async def test_update_nonexistent_quote(self, quote_repo: QuoteRepository):
        ok = await quote_repo.update_quote("nonexistent", content="内容")
        assert ok is False

    async def test_increment_show_time(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u72", "qt_g72")
        await quote_repo.create_quote("qt_q72", "qt_u72", "qt_g72", content="增加展示")
        ok = await quote_repo.increment_show_time("qt_q72")
        assert ok is True
        updated = await quote_repo.get_quote_by_id("qt_q72")
        assert updated is not None
        assert updated.total_show_time == 1

    async def test_increment_show_time_nonexistent(self, quote_repo: QuoteRepository):
        ok = await quote_repo.increment_show_time("nonexistent")
        assert ok is False


# ---- 删除测试 ----

class TestQuoteDelete:
    """删除相关测试。"""

    async def test_delete_quote(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u80", "qt_g80")
        await quote_repo.create_quote("qt_q80", "qt_u80", "qt_g80", content="待删除")
        ok = await quote_repo.delete_quote("qt_q80")
        assert ok is True
        assert await quote_repo.get_quote_by_id("qt_q80") is None

    async def test_delete_nonexistent_quote(self, quote_repo: QuoteRepository):
        ok = await quote_repo.delete_quote("nonexistent")
        assert ok is False

    async def test_delete_quotes_by_group(
        self, quote_repo: QuoteRepository,
        user_repo: UserRepository, group_repo: GroupRepository,
    ):
        await _seed_user_and_group(user_repo, group_repo, "qt_u81", "qt_g81")
        await quote_repo.create_quote("qt_q81a", "qt_u81", "qt_g81", content="群删除1")
        await quote_repo.create_quote("qt_q81b", "qt_u81", "qt_g81", content="群删除2")
        ok = await quote_repo.delete_quotes_by_group("qt_g81")
        assert ok is True
        results = await quote_repo.get_quotes_by_group("qt_g81")
        assert len(results) == 0
