"""
QuoteWriteService 单元测试。

覆盖：添加语录、更新语录、删除语录、消息映射操作。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from nonebot_plugin_zikequote3.database.models.quotes import Quote
from nonebot_plugin_zikequote3.exceptions import (
    DatabaseOperationError,
    ImageNotFoundError,
    QuoteNotFoundError,
    ValidationException,
)
from nonebot_plugin_zikequote3.services.quote_write_service import (
    QuoteWriteService,
    _generate_quote_id,
)


# ------------------------------------------------------------------ #
#  辅助工厂
# ------------------------------------------------------------------ #

def _make_quote(**overrides) -> Quote:
    """创建测试用 Quote DTO。"""
    from datetime import datetime, timezone

    defaults = {
        "quote_id": "10000000001",
        "author_id": "12345",
        "group_id": "99999",
        "content": "测试语录内容",
        "image_content_uuid": None,
        "total_show_time": 0,
        "time_stamp": datetime.now(tz=timezone.utc),
    }
    defaults.update(overrides)
    return Quote(**defaults)


# ================================================================== #
#  添加语录
# ================================================================== #


class TestAddQuote:
    """测试 add_quote 方法。"""

    @pytest.mark.asyncio
    async def test_add_quote_text_only(
        self, quote_write_service: QuoteWriteService, mock_quote_repo: AsyncMock,
        mock_image_repo: AsyncMock,
    ) -> None:
        """纯文本语录添加成功。"""
        mock_quote_repo.create_quote.return_value = _make_quote()

        quote_id = await quote_write_service.add_quote(
            group_id="99999", author_id="12345", content="你好世界",
        )

        assert isinstance(quote_id, str)
        assert len(quote_id) == 11
        mock_quote_repo.create_quote.assert_awaited_once()
        # 没有图片，不应检查图片存在性
        mock_image_repo.image_exists.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_add_quote_with_image(
        self, quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock, mock_image_repo: AsyncMock,
    ) -> None:
        """带图片的语录添加成功。"""
        mock_image_repo.image_exists.return_value = True
        mock_quote_repo.create_quote.return_value = _make_quote()

        quote_id = await quote_write_service.add_quote(
            group_id="99999", author_id="12345",
            content="带图", image_content_uuid="img-uuid-001",
        )

        assert isinstance(quote_id, str)
        mock_image_repo.image_exists.assert_awaited_once_with("img-uuid-001")

    @pytest.mark.asyncio
    async def test_add_quote_image_only(
        self, quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock, mock_image_repo: AsyncMock,
    ) -> None:
        """纯图片语录添加成功。"""
        mock_image_repo.image_exists.return_value = True
        mock_quote_repo.create_quote.return_value = _make_quote(
            content=None,
            image_content_uuid="img-uuid-002",
        )

        quote_id = await quote_write_service.add_quote(
            group_id="99999", author_id="12345",
            content=None, image_content_uuid="img-uuid-002",
        )

        assert isinstance(quote_id, str)
        mock_image_repo.image_exists.assert_awaited_once_with("img-uuid-002")
        mock_quote_repo.create_quote.assert_awaited_once_with(
            quote_id=quote_id,
            author_id="12345",
            group_id="99999",
            content=None,
            image_content_uuid="img-uuid-002",
        )

    @pytest.mark.asyncio
    async def test_add_quote_empty_content_and_image_raises(
        self, quote_write_service: QuoteWriteService,
    ) -> None:
        """内容和图片均为空时抛出 ValidationException。"""
        with pytest.raises(ValidationException, match="不能同时为空"):
            await quote_write_service.add_quote(
                group_id="99999", author_id="12345",
                content=None, image_content_uuid=None,
            )

    @pytest.mark.asyncio
    async def test_add_quote_image_not_found_raises(
        self, quote_write_service: QuoteWriteService,
        mock_image_repo: AsyncMock,
    ) -> None:
        """图片 UUID 不存在时抛出 ImageNotFoundError。"""
        mock_image_repo.image_exists.return_value = False

        with pytest.raises(ImageNotFoundError):
            await quote_write_service.add_quote(
                group_id="99999", author_id="12345",
                content=None, image_content_uuid="nonexistent-uuid",
            )


# ================================================================== #
#  添加语录 + 图片元数据
# ================================================================== #


class TestAddQuoteWithImageData:
    """测试 add_quote_with_image_data 方法。"""

    @pytest.mark.asyncio
    async def test_creates_image_then_quote(
        self, quote_write_service: QuoteWriteService,
        mock_image_repo: AsyncMock, mock_quote_repo: AsyncMock,
    ) -> None:
        """先创建图片记录，再创建语录。"""
        mock_image_repo.image_exists.return_value = True
        mock_quote_repo.create_quote.return_value = _make_quote()

        quote_id = await quote_write_service.add_quote_with_image_data(
            group_id="99999", author_id="12345", content="带图语录",
            image_uuid="img-001", original_filename="test.png",
            stored_filename="img-001.png", file_path="/images/img-001.png",
            checksum_sha256="abc123",
        )

        assert isinstance(quote_id, str)
        mock_image_repo.create_image.assert_awaited_once()


# ================================================================== #
#  更新语录
# ================================================================== #


class TestUpdateQuote:
    """测试 update_quote 方法。"""

    @pytest.mark.asyncio
    async def test_update_content(
        self, quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock,
    ) -> None:
        """更新语录内容成功。"""
        mock_quote_repo.get_quote_by_id.return_value = _make_quote()
        mock_quote_repo.update_quote.return_value = True

        await quote_write_service.update_quote(
            quote_id="10000000001", content="新内容",
        )

        mock_quote_repo.update_quote.assert_awaited_once_with(
            quote_id="10000000001", content="新内容", image_content_uuid=None,
        )

    @pytest.mark.asyncio
    async def test_update_nonexistent_quote_raises(
        self, quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock,
    ) -> None:
        """更新不存在的语录抛出 QuoteNotFoundError。"""
        mock_quote_repo.get_quote_by_id.return_value = None

        with pytest.raises(QuoteNotFoundError):
            await quote_write_service.update_quote(
                quote_id="nonexistent", content="新内容",
            )

    @pytest.mark.asyncio
    async def test_update_with_invalid_image_raises(
        self, quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock, mock_image_repo: AsyncMock,
    ) -> None:
        """更新时指定不存在的图片 UUID 抛出 ImageNotFoundError。"""
        mock_quote_repo.get_quote_by_id.return_value = _make_quote()
        mock_image_repo.image_exists.return_value = False

        with pytest.raises(ImageNotFoundError):
            await quote_write_service.update_quote(
                quote_id="10000000001", image_content_uuid="bad-uuid",
            )

    @pytest.mark.asyncio
    async def test_update_repo_failure_raises(
        self, quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock,
    ) -> None:
        """Repository 更新返回 False 时抛出 DatabaseOperationError。"""
        mock_quote_repo.get_quote_by_id.return_value = _make_quote()
        mock_quote_repo.update_quote.return_value = False

        with pytest.raises(DatabaseOperationError):
            await quote_write_service.update_quote(
                quote_id="10000000001", content="新内容",
            )


# ================================================================== #
#  删除语录
# ================================================================== #


class TestDeleteQuote:
    """测试 delete_quote 方法。"""

    @pytest.mark.asyncio
    async def test_delete_success(
        self, quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock, mock_mapping_repo: AsyncMock,
    ) -> None:
        """删除语录成功，同时清理映射。"""
        mock_quote_repo.get_quote_by_id.return_value = _make_quote()
        mock_quote_repo.delete_quote.return_value = True

        await quote_write_service.delete_quote("10000000001")

        mock_quote_repo.delete_quote.assert_awaited_once_with("10000000001")
        mock_mapping_repo.delete_mappings_by_quote_id.assert_awaited_once_with(
            "10000000001",
        )

    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises(
        self, quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock,
    ) -> None:
        """删除不存在的语录抛出 QuoteNotFoundError。"""
        mock_quote_repo.get_quote_by_id.return_value = None

        with pytest.raises(QuoteNotFoundError):
            await quote_write_service.delete_quote("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_repo_failure_raises(
        self, quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock,
    ) -> None:
        """Repository 删除返回 False 时抛出 DatabaseOperationError。"""
        mock_quote_repo.get_quote_by_id.return_value = _make_quote()
        mock_quote_repo.delete_quote.return_value = False

        with pytest.raises(DatabaseOperationError):
            await quote_write_service.delete_quote("10000000001")


# ================================================================== #
#  消息映射
# ================================================================== #


class TestMsgQuoteMapping:
    """测试消息 ID → 语录 ID 映射操作。"""

    @pytest.mark.asyncio
    async def test_create_mapping(
        self, quote_write_service: QuoteWriteService,
        mock_mapping_repo: AsyncMock,
    ) -> None:
        """创建映射成功。"""
        await quote_write_service.create_msg_quote_mapping("msg-001", "q-001")

        mock_mapping_repo.create_mapping.assert_awaited_once_with("msg-001", "q-001")

    @pytest.mark.asyncio
    async def test_get_quote_id_by_msg_id_found(
        self, quote_write_service: QuoteWriteService,
        mock_mapping_repo: AsyncMock,
    ) -> None:
        """通过消息 ID 获取语录 ID 成功。"""
        mock_mapping_repo.get_quote_id_by_msg_id.return_value = "q-001"

        result = await quote_write_service.get_quote_id_by_msg_id("msg-001")

        assert result == "q-001"

    @pytest.mark.asyncio
    async def test_get_quote_id_by_msg_id_not_found(
        self, quote_write_service: QuoteWriteService,
        mock_mapping_repo: AsyncMock,
    ) -> None:
        """消息 ID 无映射时返回 None。"""
        mock_mapping_repo.get_quote_id_by_msg_id.return_value = None

        result = await quote_write_service.get_quote_id_by_msg_id("unknown")

        assert result is None


# ================================================================== #
#  去重检查
# ================================================================== #


class TestCheckQuoteExists:
    """测试 check_quote_exists 方法。"""

    @pytest.mark.asyncio
    async def test_returns_true_when_exists(
        self,
        quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock,
    ) -> None:
        """当语录已存在时返回 True。"""
        mock_quote_repo.check_quote_exists_by_author_content.return_value = True

        result = await quote_write_service.check_quote_exists("12345", "测试内容")

        assert result is True
        mock_quote_repo.check_quote_exists_by_author_content.assert_awaited_once_with(
            "12345", "测试内容"
        )

    @pytest.mark.asyncio
    async def test_returns_false_when_not_exists(
        self,
        quote_write_service: QuoteWriteService,
        mock_quote_repo: AsyncMock,
    ) -> None:
        """当语录不存在时返回 False。"""
        mock_quote_repo.check_quote_exists_by_author_content.return_value = False

        result = await quote_write_service.check_quote_exists("12345", "新内容")

        assert result is False


# ================================================================== #
#  辅助函数
# ================================================================== #


class TestGenerateQuoteId:
    """测试 _generate_quote_id 辅助函数。"""

    def test_generates_11_digit_string(self) -> None:
        """生成的 ID 为 11 位数字字符串。"""
        for _ in range(50):
            qid = _generate_quote_id()
            assert len(qid) == 11
            assert qid.isdigit()
