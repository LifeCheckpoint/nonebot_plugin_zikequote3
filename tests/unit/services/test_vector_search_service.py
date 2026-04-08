"""VectorSearchService 单元测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from nonebot_plugin_zikequote3.database.models.quotes import Quote
from nonebot_plugin_zikequote3.exceptions import OperationError
from nonebot_plugin_zikequote3.vector_search.capability import UnavailableVectorSearchService
from nonebot_plugin_zikequote3.vector_search.search_service import VectorSearchService


# ---- helpers ---- #


def _make_quote(**overrides) -> Quote:
    defaults = {
        "quote_id": "q1",
        "author_id": "user1",
        "group_id": "group1",
        "content": "测试语录内容",
        "image_content_uuid": None,
        "total_show_time": 0,
        "time_stamp": datetime(2025, 1, 1),
    }
    defaults.update(overrides)
    return Quote(**defaults)


# ================================================================
# semantic_search
# ================================================================


class TestSemanticSearch:
    """semantic_search 测试。"""

    async def test_normal_search(
        self,
        vector_search_service: VectorSearchService,
        mock_embedding_client: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_quote_repo: AsyncMock,
    ):
        """正常搜索：embed → store.search → 获取 Quote → 返回列表。"""
        mock_vector_store.get_meta.return_value = {
            "model_name": "test-model",
            "dimensions": "128",
        }
        mock_embedding_client.embed_query.return_value = [0.1] * 128
        mock_vector_store.search.return_value = [
            {"quote_id": "q1", "similarity": 0.95},
            {"quote_id": "q2", "similarity": 0.80},
        ]
        q1 = _make_quote(quote_id="q1", content="语录一")
        q2 = _make_quote(quote_id="q2", content="语录二")
        mock_quote_repo.get_quote_by_id.side_effect = lambda qid: {
            "q1": q1, "q2": q2,
        }.get(qid)

        result = await vector_search_service.semantic_search("测试", "group1")

        assert len(result) == 2
        assert result[0] == (q1, 0.95)
        assert result[1] == (q2, 0.80)
        mock_embedding_client.embed_query.assert_awaited_once_with("测试")

    async def test_empty_results(
        self,
        vector_search_service: VectorSearchService,
        mock_embedding_client: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """store.search 返回空列表 → 结果为空。"""
        mock_vector_store.get_meta.return_value = {
            "model_name": "test-model",
            "dimensions": "128",
        }
        mock_embedding_client.embed_query.return_value = [0.1] * 128
        mock_vector_store.search.return_value = []

        result = await vector_search_service.semantic_search("无结果", "group1")

        assert result == []

    async def test_skip_missing_quotes(
        self,
        vector_search_service: VectorSearchService,
        mock_embedding_client: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_quote_repo: AsyncMock,
    ):
        """部分 quote_id 在数据库中不存在 → 跳过。"""
        mock_vector_store.get_meta.return_value = {
            "model_name": "test-model",
            "dimensions": "128",
        }
        mock_embedding_client.embed_query.return_value = [0.1] * 128
        mock_vector_store.search.return_value = [
            {"quote_id": "q1", "similarity": 0.9},
            {"quote_id": "q_gone", "similarity": 0.8},
        ]
        q1 = _make_quote(quote_id="q1")
        mock_quote_repo.get_quote_by_id.side_effect = lambda qid: (
            q1 if qid == "q1" else None
        )

        result = await vector_search_service.semantic_search("测试", "group1")

        assert len(result) == 1
        assert result[0][0].quote_id == "q1"

    async def test_model_inconsistency_raises(
        self,
        vector_search_service: VectorSearchService,
        mock_vector_store: AsyncMock,
    ):
        """模型不一致时抛出 ValueError。"""
        mock_vector_store.get_meta.return_value = {
            "model_name": "old-model",
            "dimensions": "128",
        }

        with pytest.raises(ValueError, match="向量索引模型不一致"):
            await vector_search_service.semantic_search("测试", "group1")


# ================================================================
# index_quote
# ================================================================


class TestIndexQuote:
    """index_quote 测试。"""

    async def test_normal_index(
        self,
        vector_search_service: VectorSearchService,
        mock_embedding_client: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """有 content 的语录 → embed → upsert。"""
        mock_embedding_client.embed_query.return_value = [0.5] * 128
        quote = _make_quote(quote_id="q1", content="好语录")

        await vector_search_service.index_quote(quote)

        mock_embedding_client.embed_query.assert_awaited_once_with("好语录")
        mock_vector_store.upsert.assert_awaited_once()
        upserted = mock_vector_store.upsert.call_args[0][0]
        assert upserted[0]["quote_id"] == "q1"
        assert upserted[0]["vector"] == [0.5] * 128

    async def test_skip_empty_content(
        self,
        vector_search_service: VectorSearchService,
        mock_embedding_client: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """content 为 None → 不调用 embed/upsert。"""
        quote = _make_quote(content=None)

        await vector_search_service.index_quote(quote)

        mock_embedding_client.embed_query.assert_not_awaited()
        mock_vector_store.upsert.assert_not_awaited()


# ================================================================
# remove_quote
# ================================================================


class TestRemoveQuote:
    """remove_quote 测试。"""

    async def test_normal_remove(
        self,
        vector_search_service: VectorSearchService,
        mock_vector_store: AsyncMock,
    ):
        """正常删除：调用 store.delete。"""
        await vector_search_service.remove_quote("q1")

        mock_vector_store.delete.assert_awaited_once_with(["q1"])


# ================================================================
# reindex_all
# ================================================================


class TestReindexAll:
    """reindex_all 测试。"""

    async def test_with_group_id(
        self,
        vector_search_service: VectorSearchService,
        mock_embedding_client: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_quote_repo: AsyncMock,
    ):
        """指定 group_id：获取该群语录 → 分批 embed → upsert。"""
        quotes = [
            _make_quote(quote_id=f"q{i}", content=f"内容{i}")
            for i in range(3)
        ]
        mock_quote_repo.get_quotes_by_group.return_value = quotes
        mock_embedding_client.embed_texts.return_value = [[0.1] * 128] * 2

        # batch_size=2, 3 quotes → 2 batches
        result = await vector_search_service.reindex_all(group_id="group1")

        assert result == 3
        mock_quote_repo.get_quotes_by_group.assert_awaited_once_with("group1")
        mock_quote_repo.get_all_quotes.assert_not_awaited()
        # 指定 group_id 时只删除该群数据，不 drop_all
        mock_vector_store.delete_by_group.assert_awaited_once_with("group1")
        mock_vector_store.drop_all.assert_not_awaited()

    async def test_without_group_id(
        self,
        vector_search_service: VectorSearchService,
        mock_embedding_client: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_quote_repo: AsyncMock,
    ):
        """不指定 group_id：获取全部语录。"""
        quotes = [_make_quote(quote_id="q1", content="内容")]
        mock_quote_repo.get_all_quotes.return_value = quotes
        mock_embedding_client.embed_texts.return_value = [[0.1] * 128]

        result = await vector_search_service.reindex_all()

        assert result == 1
        mock_quote_repo.get_all_quotes.assert_awaited_once()
        mock_quote_repo.get_quotes_by_group.assert_not_awaited()

    async def test_no_text_quotes_returns_zero(
        self,
        vector_search_service: VectorSearchService,
        mock_quote_repo: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """无文本语录全部跳过 → 返回 0。"""
        quotes = [
            _make_quote(quote_id="q1", content=None),
            _make_quote(quote_id="q2", content=None),
        ]
        mock_quote_repo.get_all_quotes.return_value = quotes

        result = await vector_search_service.reindex_all()

        assert result == 0
        mock_vector_store.upsert.assert_not_awaited()

    async def test_batch_processing(
        self,
        vector_search_service: VectorSearchService,
        mock_embedding_client: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_quote_repo: AsyncMock,
    ):
        """分批处理验证：batch_size=2，5 条语录 → 3 批。"""
        quotes = [
            _make_quote(quote_id=f"q{i}", content=f"内容{i}")
            for i in range(5)
        ]
        mock_quote_repo.get_all_quotes.return_value = quotes
        # 每批返回对应数量的向量
        mock_embedding_client.embed_texts.side_effect = [
            [[0.1] * 128] * 2,  # batch 1: 2 条
            [[0.1] * 128] * 2,  # batch 2: 2 条
            [[0.1] * 128] * 1,  # batch 3: 1 条
        ]

        result = await vector_search_service.reindex_all()

        assert result == 5
        assert mock_embedding_client.embed_texts.await_count == 3
        assert mock_vector_store.upsert.await_count == 3


# ================================================================
# check_model_consistency
# ================================================================


class TestCheckModelConsistency:
    """check_model_consistency 测试。"""

    async def test_consistent(
        self,
        vector_search_service: VectorSearchService,
        mock_vector_store: AsyncMock,
    ):
        """一致：meta 中 model_name 和 dimensions 与 client 匹配 → True。"""
        mock_vector_store.get_meta.return_value = {
            "model_name": "test-model",
            "dimensions": "128",
        }

        assert await vector_search_service.check_model_consistency() is True

    async def test_model_name_mismatch(
        self,
        vector_search_service: VectorSearchService,
        mock_vector_store: AsyncMock,
    ):
        """不一致：model_name 不同 → False。"""
        mock_vector_store.get_meta.return_value = {
            "model_name": "different-model",
            "dimensions": "128",
        }

        assert await vector_search_service.check_model_consistency() is False

    async def test_dimensions_mismatch(
        self,
        vector_search_service: VectorSearchService,
        mock_vector_store: AsyncMock,
    ):
        """不一致：dimensions 不同 → False。"""
        mock_vector_store.get_meta.return_value = {
            "model_name": "test-model",
            "dimensions": "256",
        }

        assert await vector_search_service.check_model_consistency() is False

    async def test_no_meta_first_use(
        self,
        vector_search_service: VectorSearchService,
        mock_vector_store: AsyncMock,
    ):
        """无元信息（首次使用）→ True。"""
        mock_vector_store.get_meta.return_value = None

        assert await vector_search_service.check_model_consistency() is True


# ================================================================
# is_available
# ================================================================


class TestIsAvailable:
    """is_available 测试（M4: 只检查基础设施是否就绪）。"""

    async def test_available_with_data(
        self,
        vector_search_service: VectorSearchService,
        mock_vector_store: AsyncMock,
    ):
        """store 连接正常且有数据 → True。"""
        mock_vector_store.count.return_value = 10

        assert await vector_search_service.is_available() is True

    async def test_available_empty_index(
        self,
        vector_search_service: VectorSearchService,
        mock_vector_store: AsyncMock,
    ):
        """M4: store 连接正常但索引为空 → 仍然返回 True（基础设施可用）。"""
        mock_vector_store.count.return_value = 0

        assert await vector_search_service.is_available() is True

    async def test_unavailable_on_exception(
        self,
        vector_search_service: VectorSearchService,
        mock_vector_store: AsyncMock,
    ):
        """store 连接异常 → False。"""
        mock_vector_store.count.side_effect = RuntimeError("连接失败")

        assert await vector_search_service.is_available() is False


# ================================================================
# unavailable capability
# ================================================================


class TestUnavailableVectorSearchService:
    """UnavailableVectorSearchService 测试。"""

    async def test_reports_unavailable_status(self):
        svc = UnavailableVectorSearchService("基础设施未就绪")

        assert svc.get_status().available is False
        assert svc.get_unavailable_reason() == "基础设施未就绪"
        assert await svc.is_available() is False

    async def test_operation_raises_operation_error(self):
        svc = UnavailableVectorSearchService("基础设施未就绪")

        with pytest.raises(OperationError, match="基础设施未就绪"):
            await svc.reindex_all("group1")
