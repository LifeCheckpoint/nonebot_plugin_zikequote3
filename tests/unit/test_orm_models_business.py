"""
业务实体 ORM 模型单元测试。

覆盖 7 个业务实体：ImageModel, QuoteModel, ReviewModel,
MsgQueueModel, QueueGroupMessageCountModel, MsgIdQuoteIdMapModel, GroupConfigModel。

测试内容：DDL 验证、CRUD 基础、DTO 转换、from_create_dto、外键约束、relationship 加载。
"""

import pytest
from sqlalchemy import select

from nonebot_plugin_zikequote3.database.sa.base import Base
from nonebot_plugin_zikequote3.database.sa.models import (
    GroupModel,
    UserModel,
    ImageModel,
    QuoteModel,
    ReviewModel,
    MsgQueueModel,
    QueueGroupMessageCountModel,
    MsgIdQuoteIdMapModel,
    GroupConfigModel,
)
from nonebot_plugin_zikequote3.database.models.images import Image, ImageCreate
from nonebot_plugin_zikequote3.database.models.quotes import Quote, QuoteCreate
from nonebot_plugin_zikequote3.database.models.reviews import Review, ReviewCreate
from nonebot_plugin_zikequote3.database.models.msgs_queue import MsgQueue, MsgQueueCreate
from nonebot_plugin_zikequote3.database.models.queue_group_message_counts import (
    QueueGroupMessageCount,
    QueueGroupMessageCountCreate,
)
from nonebot_plugin_zikequote3.database.models.msgid_quoteid_map import (
    MsgQuoteID,
    MsgQuoteIDCreate,
)
from nonebot_plugin_zikequote3.database.models.group_configs import (
    GroupConfigs,
    GroupConfigsCreate,
)


# ============================================================================
# DDL 验证
# ============================================================================


class TestBusinessDDL:
    """验证业务实体 ORM 模型生成的表结构与预期一致。"""

    def test_images_table_columns(self, async_engine):
        table = Base.metadata.tables["images"]
        col_names = {c.name for c in table.columns}
        assert col_names == {
            "uuid", "original_filename", "stored_filename",
            "file_path", "time_stamp", "checksum_sha256",
        }
        assert table.c.uuid.primary_key

    def test_quotes_table_columns(self, async_engine):
        table = Base.metadata.tables["quotes"]
        col_names = {c.name for c in table.columns}
        assert col_names == {
            "quote_id", "time_stamp", "author_id", "group_id",
            "content", "image_content_uuid", "total_show_time",
        }
        assert table.c.quote_id.primary_key

    def test_reviews_table_columns(self, async_engine):
        table = Base.metadata.tables["reviews"]
        col_names = {c.name for c in table.columns}
        assert col_names == {
            "review_id", "time_stamp", "author_id", "quote_id", "content",
        }
        assert table.c.review_id.primary_key

    def test_msgs_queue_table_columns(self, async_engine):
        table = Base.metadata.tables["msgs_queue"]
        col_names = {c.name for c in table.columns}
        assert col_names == {
            "msg_id", "group_id", "qq_id", "time_stamp", "content",
        }
        assert table.c.msg_id.primary_key

    def test_queue_group_message_counts_table_columns(self, async_engine):
        table = Base.metadata.tables["queue_group_message_counts"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"group_id", "message_count"}
        assert table.c.group_id.primary_key

    def test_msgid_quoteid_map_table_columns(self, async_engine):
        table = Base.metadata.tables["msgid_quoteid_map"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"msg_id", "quote_id"}
        assert table.c.msg_id.primary_key

    def test_group_configs_table_columns(self, async_engine):
        table = Base.metadata.tables["group_configs"]
        col_names = {c.name for c in table.columns}
        assert col_names == {"group_id", "toml_config"}
        assert table.c.group_id.primary_key


# ============================================================================
# 辅助方法
# ============================================================================


async def _ensure_user(session, uid="50001"):
    existing = await session.get(UserModel, uid)
    if existing is None:
        session.add(UserModel(qq_id=uid))
        await session.flush()
    return uid


async def _ensure_group(session, gid="60001"):
    existing = await session.get(GroupModel, gid)
    if existing is None:
        session.add(GroupModel(group_id=gid, name=f"群{gid}"))
        await session.flush()
    return gid


async def _ensure_image(session, uuid="img-001"):
    existing = await session.get(ImageModel, uuid)
    if existing is None:
        session.add(ImageModel(
            uuid=uuid, stored_filename="test.png",
            file_path="/images/test.png", checksum_sha256="abc123",
        ))
        await session.flush()
    return uuid


async def _ensure_quote(session, qid="q-001", uid="50001", gid="60001"):
    await _ensure_user(session, uid)
    await _ensure_group(session, gid)
    existing = await session.get(QuoteModel, qid)
    if existing is None:
        session.add(QuoteModel(
            quote_id=qid, author_id=uid, group_id=gid,
            content="测试语录内容", total_show_time=0,
        ))
        await session.flush()
    return qid


# ============================================================================
# ImageModel CRUD + DTO
# ============================================================================


class TestImageModel:

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        img = ImageModel(
            uuid="img-100", original_filename="photo.jpg",
            stored_filename="stored_photo.jpg",
            file_path="/images/stored_photo.jpg",
            checksum_sha256="sha256hash100",
        )
        async_session.add(img)
        await async_session.flush()
        result = await async_session.get(ImageModel, "img-100")
        assert result is not None
        assert result.original_filename == "photo.jpg"

    @pytest.mark.anyio
    async def test_nullable_original_filename(self, async_session):
        img = ImageModel(
            uuid="img-101", stored_filename="no_orig.png",
            file_path="/images/no_orig.png", checksum_sha256="sha256hash101",
        )
        async_session.add(img)
        await async_session.flush()
        result = await async_session.get(ImageModel, "img-101")
        assert result is not None
        assert result.original_filename is None

    @pytest.mark.anyio
    async def test_update(self, async_session):
        img = ImageModel(
            uuid="img-102", stored_filename="old.png",
            file_path="/images/old.png", checksum_sha256="sha256hash102",
        )
        async_session.add(img)
        await async_session.flush()
        img.stored_filename = "new.png"
        await async_session.flush()
        refreshed = await async_session.get(ImageModel, "img-102")
        assert refreshed is not None
        assert refreshed.stored_filename == "new.png"

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        img = ImageModel(
            uuid="img-103", stored_filename="del.png",
            file_path="/images/del.png", checksum_sha256="sha256hash103",
        )
        async_session.add(img)
        await async_session.flush()
        await async_session.delete(img)
        await async_session.flush()
        assert await async_session.get(ImageModel, "img-103") is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        img = ImageModel(
            uuid="img-104", original_filename="dto.jpg",
            stored_filename="dto_stored.jpg",
            file_path="/images/dto_stored.jpg",
            checksum_sha256="sha256hash104",
        )
        async_session.add(img)
        await async_session.flush()
        dto = img.to_dto()
        assert isinstance(dto, Image)
        assert dto.uuid == "img-104"
        assert dto.checksum_sha256 == "sha256hash104"

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        create_dto = ImageCreate(
            uuid="img-105", original_filename="create.jpg",
            stored_filename="create_stored.jpg",
            file_path="/images/create_stored.jpg",
            checksum_sha256="sha256hash105",
        )
        img = ImageModel.from_create_dto(create_dto)
        assert isinstance(img, ImageModel)
        async_session.add(img)
        await async_session.flush()
        assert await async_session.get(ImageModel, "img-105") is not None


# ============================================================================
# QuoteModel CRUD + DTO + relationship
# ============================================================================


class TestQuoteModel:

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        await _ensure_user(async_session, "50010")
        await _ensure_group(async_session, "60010")
        quote = QuoteModel(
            quote_id="q-100", author_id="50010", group_id="60010",
            content="这是一条测试语录", total_show_time=0,
        )
        async_session.add(quote)
        await async_session.flush()
        result = await async_session.get(QuoteModel, "q-100")
        assert result is not None
        assert result.content == "这是一条测试语录"

    @pytest.mark.anyio
    async def test_create_with_image(self, async_session):
        await _ensure_user(async_session, "50011")
        await _ensure_group(async_session, "60011")
        await _ensure_image(async_session, "img-q-200")
        quote = QuoteModel(
            quote_id="q-200", author_id="50011", group_id="60011",
            content="带图语录", image_content_uuid="img-q-200",
            total_show_time=0,
        )
        async_session.add(quote)
        await async_session.flush()
        result = await async_session.get(QuoteModel, "q-200")
        assert result is not None
        assert result.image_content_uuid == "img-q-200"

    @pytest.mark.anyio
    async def test_update(self, async_session):
        await _ensure_user(async_session, "50012")
        await _ensure_group(async_session, "60012")
        quote = QuoteModel(
            quote_id="q-101", author_id="50012", group_id="60012",
            content="旧内容", total_show_time=0,
        )
        async_session.add(quote)
        await async_session.flush()
        quote.content = "新内容"
        quote.total_show_time = 5
        await async_session.flush()
        refreshed = await async_session.get(QuoteModel, "q-101")
        assert refreshed is not None
        assert refreshed.content == "新内容"
        assert refreshed.total_show_time == 5

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        await _ensure_user(async_session, "50013")
        await _ensure_group(async_session, "60013")
        quote = QuoteModel(
            quote_id="q-102", author_id="50013", group_id="60013",
            content="待删除", total_show_time=0,
        )
        async_session.add(quote)
        await async_session.flush()
        await async_session.delete(quote)
        await async_session.flush()
        assert await async_session.get(QuoteModel, "q-102") is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        await _ensure_user(async_session, "50014")
        await _ensure_group(async_session, "60014")
        quote = QuoteModel(
            quote_id="q-103", author_id="50014", group_id="60014",
            content="DTO语录", total_show_time=3,
        )
        async_session.add(quote)
        await async_session.flush()
        dto = quote.to_dto()
        assert isinstance(dto, Quote)
        assert dto.quote_id == "q-103"
        assert dto.content == "DTO语录"
        assert dto.total_show_time == 3

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        await _ensure_user(async_session, "50015")
        await _ensure_group(async_session, "60015")
        create_dto = QuoteCreate(
            quote_id="q-104", author_id="50015", group_id="60015",
            content="从DTO创建", image_content_uuid=None, total_show_time=0,
        )
        quote = QuoteModel.from_create_dto(create_dto)
        assert isinstance(quote, QuoteModel)
        async_session.add(quote)
        await async_session.flush()
        assert await async_session.get(QuoteModel, "q-104") is not None

    @pytest.mark.anyio
    async def test_relationship_author(self, async_session):
        await _ensure_user(async_session, "50016")
        await _ensure_group(async_session, "60016")
        quote = QuoteModel(
            quote_id="q-105", author_id="50016", group_id="60016",
            content="关联测试", total_show_time=0,
        )
        async_session.add(quote)
        await async_session.flush()
        await async_session.refresh(quote, ["author"])
        assert quote.author.qq_id == "50016"

    @pytest.mark.anyio
    async def test_relationship_group(self, async_session):
        await _ensure_user(async_session, "50017")
        await _ensure_group(async_session, "60017")
        quote = QuoteModel(
            quote_id="q-106", author_id="50017", group_id="60017",
            content="群关联测试", total_show_time=0,
        )
        async_session.add(quote)
        await async_session.flush()
        await async_session.refresh(quote, ["group"])
        assert quote.group.group_id == "60017"

    @pytest.mark.anyio
    async def test_relationship_reviews(self, async_session):
        await _ensure_user(async_session, "50018")
        await _ensure_group(async_session, "60018")
        quote = QuoteModel(
            quote_id="q-107", author_id="50018", group_id="60018",
            content="评论关联测试", total_show_time=0,
        )
        async_session.add(quote)
        await async_session.flush()
        review = ReviewModel(
            review_id="r-rel-1", author_id="50018",
            quote_id="q-107", content="测试评论",
        )
        async_session.add(review)
        await async_session.flush()
        await async_session.refresh(quote, ["reviews"])
        assert len(quote.reviews) == 1
        assert quote.reviews[0].review_id == "r-rel-1"


# ============================================================================
# ReviewModel CRUD + DTO + relationship
# ============================================================================


class TestReviewModel:

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        await _ensure_quote(async_session, "q-r-001", "50020", "60020")
        review = ReviewModel(
            review_id="r-100", author_id="50020",
            quote_id="q-r-001", content="好语录！",
        )
        async_session.add(review)
        await async_session.flush()
        result = await async_session.get(ReviewModel, "r-100")
        assert result is not None
        assert result.content == "好语录！"

    @pytest.mark.anyio
    async def test_update(self, async_session):
        await _ensure_quote(async_session, "q-r-002", "50021", "60021")
        review = ReviewModel(
            review_id="r-101", author_id="50021",
            quote_id="q-r-002", content="旧评论",
        )
        async_session.add(review)
        await async_session.flush()
        review.content = "新评论"
        await async_session.flush()
        refreshed = await async_session.get(ReviewModel, "r-101")
        assert refreshed is not None
        assert refreshed.content == "新评论"

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        await _ensure_quote(async_session, "q-r-003", "50022", "60022")
        review = ReviewModel(
            review_id="r-102", author_id="50022",
            quote_id="q-r-003", content="待删除评论",
        )
        async_session.add(review)
        await async_session.flush()
        await async_session.delete(review)
        await async_session.flush()
        assert await async_session.get(ReviewModel, "r-102") is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        await _ensure_quote(async_session, "q-r-004", "50023", "60023")
        review = ReviewModel(
            review_id="r-103", author_id="50023",
            quote_id="q-r-004", content="DTO评论",
        )
        async_session.add(review)
        await async_session.flush()
        dto = review.to_dto()
        assert isinstance(dto, Review)
        assert dto.review_id == "r-103"
        assert dto.content == "DTO评论"

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        await _ensure_quote(async_session, "q-r-005", "50024", "60024")
        create_dto = ReviewCreate(
            review_id="r-104", author_id="50024",
            quote_id="q-r-005", content="从DTO创建评论",
        )
        review = ReviewModel.from_create_dto(create_dto)
        assert isinstance(review, ReviewModel)
        async_session.add(review)
        await async_session.flush()
        assert await async_session.get(ReviewModel, "r-104") is not None

    @pytest.mark.anyio
    async def test_relationship_quote(self, async_session):
        await _ensure_quote(async_session, "q-r-006", "50025", "60025")
        review = ReviewModel(
            review_id="r-105", author_id="50025",
            quote_id="q-r-006", content="关联测试评论",
        )
        async_session.add(review)
        await async_session.flush()
        await async_session.refresh(review, ["quote"])
        assert review.quote.quote_id == "q-r-006"


# ============================================================================
# MsgQueueModel CRUD + DTO
# ============================================================================


class TestMsgQueueModel:

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        await _ensure_user(async_session, "50030")
        await _ensure_group(async_session, "60030")
        msg = MsgQueueModel(
            msg_id="mq-100", group_id="60030",
            qq_id="50030", content="暂存消息内容",
        )
        async_session.add(msg)
        await async_session.flush()
        result = await async_session.get(MsgQueueModel, "mq-100")
        assert result is not None
        assert result.content == "暂存消息内容"

    @pytest.mark.anyio
    async def test_update(self, async_session):
        await _ensure_user(async_session, "50031")
        await _ensure_group(async_session, "60031")
        msg = MsgQueueModel(
            msg_id="mq-101", group_id="60031",
            qq_id="50031", content="旧消息",
        )
        async_session.add(msg)
        await async_session.flush()
        msg.content = "新消息"
        await async_session.flush()
        refreshed = await async_session.get(MsgQueueModel, "mq-101")
        assert refreshed is not None
        assert refreshed.content == "新消息"

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        await _ensure_user(async_session, "50032")
        await _ensure_group(async_session, "60032")
        msg = MsgQueueModel(
            msg_id="mq-102", group_id="60032",
            qq_id="50032", content="待删除消息",
        )
        async_session.add(msg)
        await async_session.flush()
        await async_session.delete(msg)
        await async_session.flush()
        assert await async_session.get(MsgQueueModel, "mq-102") is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        await _ensure_user(async_session, "50033")
        await _ensure_group(async_session, "60033")
        msg = MsgQueueModel(
            msg_id="mq-103", group_id="60033",
            qq_id="50033", content="DTO消息",
        )
        async_session.add(msg)
        await async_session.flush()
        dto = msg.to_dto()
        assert isinstance(dto, MsgQueue)
        assert dto.msg_id == "mq-103"
        assert dto.content == "DTO消息"

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        await _ensure_user(async_session, "50034")
        await _ensure_group(async_session, "60034")
        create_dto = MsgQueueCreate(
            msg_id="mq-104", group_id="60034",
            qq_id="50034", content="从DTO创建消息",
        )
        msg = MsgQueueModel.from_create_dto(create_dto)
        assert isinstance(msg, MsgQueueModel)
        async_session.add(msg)
        await async_session.flush()
        assert await async_session.get(MsgQueueModel, "mq-104") is not None


# ============================================================================
# QueueGroupMessageCountModel CRUD + DTO
# ============================================================================


class TestQueueGroupMessageCountModel:

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        await _ensure_group(async_session, "60040")
        count = QueueGroupMessageCountModel(
            group_id="60040", message_count=0,
        )
        async_session.add(count)
        await async_session.flush()
        result = await async_session.get(
            QueueGroupMessageCountModel, "60040"
        )
        assert result is not None
        assert result.message_count == 0

    @pytest.mark.anyio
    async def test_update(self, async_session):
        await _ensure_group(async_session, "60041")
        count = QueueGroupMessageCountModel(
            group_id="60041", message_count=0,
        )
        async_session.add(count)
        await async_session.flush()
        count.message_count = 42
        await async_session.flush()
        refreshed = await async_session.get(
            QueueGroupMessageCountModel, "60041"
        )
        assert refreshed is not None
        assert refreshed.message_count == 42

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        await _ensure_group(async_session, "60042")
        count = QueueGroupMessageCountModel(
            group_id="60042", message_count=10,
        )
        async_session.add(count)
        await async_session.flush()
        await async_session.delete(count)
        await async_session.flush()
        assert (
            await async_session.get(QueueGroupMessageCountModel, "60042")
            is None
        )

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        await _ensure_group(async_session, "60043")
        count = QueueGroupMessageCountModel(
            group_id="60043", message_count=7,
        )
        async_session.add(count)
        await async_session.flush()
        dto = count.to_dto()
        assert isinstance(dto, QueueGroupMessageCount)
        assert dto.group_id == "60043"
        assert dto.message_count == 7

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        await _ensure_group(async_session, "60044")
        create_dto = QueueGroupMessageCountCreate(
            group_id="60044", message_count=0,
        )
        count = QueueGroupMessageCountModel.from_create_dto(create_dto)
        assert isinstance(count, QueueGroupMessageCountModel)
        async_session.add(count)
        await async_session.flush()
        assert (
            await async_session.get(QueueGroupMessageCountModel, "60044")
            is not None
        )


# ============================================================================
# MsgIdQuoteIdMapModel CRUD + DTO
# ============================================================================


class TestMsgIdQuoteIdMapModel:

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        await _ensure_quote(async_session, "q-map-001", "50050", "60050")
        mapping = MsgIdQuoteIdMapModel(
            msg_id="map-100", quote_id="q-map-001",
        )
        async_session.add(mapping)
        await async_session.flush()
        result = await async_session.get(MsgIdQuoteIdMapModel, "map-100")
        assert result is not None
        assert result.quote_id == "q-map-001"

    @pytest.mark.anyio
    async def test_update(self, async_session):
        await _ensure_quote(async_session, "q-map-002", "50051", "60051")
        await _ensure_quote(async_session, "q-map-003", "50051", "60051")
        mapping = MsgIdQuoteIdMapModel(
            msg_id="map-101", quote_id="q-map-002",
        )
        async_session.add(mapping)
        await async_session.flush()
        mapping.quote_id = "q-map-003"
        await async_session.flush()
        refreshed = await async_session.get(MsgIdQuoteIdMapModel, "map-101")
        assert refreshed is not None
        assert refreshed.quote_id == "q-map-003"

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        await _ensure_quote(async_session, "q-map-004", "50052", "60052")
        mapping = MsgIdQuoteIdMapModel(
            msg_id="map-102", quote_id="q-map-004",
        )
        async_session.add(mapping)
        await async_session.flush()
        await async_session.delete(mapping)
        await async_session.flush()
        assert await async_session.get(MsgIdQuoteIdMapModel, "map-102") is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        await _ensure_quote(async_session, "q-map-005", "50053", "60053")
        mapping = MsgIdQuoteIdMapModel(
            msg_id="map-103", quote_id="q-map-005",
        )
        async_session.add(mapping)
        await async_session.flush()
        dto = mapping.to_dto()
        assert isinstance(dto, MsgQuoteID)
        assert dto.msg_id == "map-103"
        assert dto.quote_id == "q-map-005"

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        await _ensure_quote(async_session, "q-map-006", "50054", "60054")
        create_dto = MsgQuoteIDCreate(
            msg_id="map-104", quote_id="q-map-006",
        )
        mapping = MsgIdQuoteIdMapModel.from_create_dto(create_dto)
        assert isinstance(mapping, MsgIdQuoteIdMapModel)
        async_session.add(mapping)
        await async_session.flush()
        assert await async_session.get(MsgIdQuoteIdMapModel, "map-104") is not None


# ============================================================================
# GroupConfigModel CRUD + DTO
# ============================================================================


class TestGroupConfigModel:

    @pytest.mark.anyio
    async def test_create_and_query(self, async_session):
        await _ensure_group(async_session, "60060")
        cfg = GroupConfigModel(
            group_id="60060",
            toml_config='[settings]\nthreshold = 50',
        )
        async_session.add(cfg)
        await async_session.flush()
        result = await async_session.get(GroupConfigModel, "60060")
        assert result is not None
        assert "threshold" in result.toml_config

    @pytest.mark.anyio
    async def test_update(self, async_session):
        await _ensure_group(async_session, "60061")
        cfg = GroupConfigModel(
            group_id="60061",
            toml_config='[old]\nkey = "val"',
        )
        async_session.add(cfg)
        await async_session.flush()
        cfg.toml_config = '[new]\nkey = "updated"'
        await async_session.flush()
        refreshed = await async_session.get(GroupConfigModel, "60061")
        assert refreshed is not None
        assert "updated" in refreshed.toml_config

    @pytest.mark.anyio
    async def test_delete(self, async_session):
        await _ensure_group(async_session, "60062")
        cfg = GroupConfigModel(
            group_id="60062",
            toml_config='[del]\nkey = "val"',
        )
        async_session.add(cfg)
        await async_session.flush()
        await async_session.delete(cfg)
        await async_session.flush()
        assert await async_session.get(GroupConfigModel, "60062") is None

    @pytest.mark.anyio
    async def test_to_dto(self, async_session):
        await _ensure_group(async_session, "60063")
        cfg = GroupConfigModel(
            group_id="60063",
            toml_config='[dto]\nkey = "val"',
        )
        async_session.add(cfg)
        await async_session.flush()
        dto = cfg.to_dto()
        assert isinstance(dto, GroupConfigs)
        assert dto.group_id == "60063"
        assert "dto" in dto.toml_config

    @pytest.mark.anyio
    async def test_from_create_dto(self, async_session):
        await _ensure_group(async_session, "60064")
        create_dto = GroupConfigsCreate(
            group_id="60064",
            toml_config='[create]\nkey = "val"',
        )
        cfg = GroupConfigModel.from_create_dto(create_dto)
        assert isinstance(cfg, GroupConfigModel)
        async_session.add(cfg)
        await async_session.flush()
        assert await async_session.get(GroupConfigModel, "60064") is not None
