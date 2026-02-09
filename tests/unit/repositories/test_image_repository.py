"""ImageRepository 单元测试。"""

import pytest

from nonebot_plugin_zikequote3.database.models.images import Image, ImageCreate
from nonebot_plugin_zikequote3.database.repositories.image_repository import ImageRepository


pytestmark = pytest.mark.anyio


class TestImageRepositoryCreate:
    """创建相关测试。"""

    async def test_create_image(self, image_repo: ImageRepository):
        result = await image_repo.create_image(
            uuid="img-001",
            original_filename="photo.png",
            stored_filename="img-001.png",
            file_path="/images/img-001.png",
            checksum_sha256="abc123",
        )
        assert isinstance(result, Image)
        assert result.uuid == "img-001"
        assert result.original_filename == "photo.png"
        assert result.checksum_sha256 == "abc123"

    async def test_batch_create_images(self, image_repo: ImageRepository):
        images = [
            ImageCreate(
                uuid="bi-001", original_filename="a.png",
                stored_filename="bi-001.png", file_path="/img/bi-001.png",
                checksum_sha256="hash1",
            ),
            ImageCreate(
                uuid="bi-002", original_filename="b.png",
                stored_filename="bi-002.png", file_path="/img/bi-002.png",
                checksum_sha256="hash2",
            ),
        ]
        ok = await image_repo.batch_create_images(images)
        assert ok is True
        assert await image_repo.image_exists("bi-001")
        assert await image_repo.image_exists("bi-002")

    async def test_batch_create_images_empty(self, image_repo: ImageRepository):
        ok = await image_repo.batch_create_images([])
        assert ok is True


class TestImageRepositoryRead:
    """查询相关测试。"""

    async def test_get_by_uuid(self, image_repo: ImageRepository):
        await image_repo.create_image(
            uuid="img-100", original_filename="x.png",
            stored_filename="img-100.png", file_path="/img/100.png",
            checksum_sha256="h100",
        )
        result = await image_repo.get_by_uuid("img-100")
        assert result is not None
        assert result.uuid == "img-100"

    async def test_get_by_uuid_not_found(self, image_repo: ImageRepository):
        result = await image_repo.get_by_uuid("nonexistent")
        assert result is None

    async def test_image_exists(self, image_repo: ImageRepository):
        await image_repo.create_image(
            uuid="img-101", original_filename="y.png",
            stored_filename="img-101.png", file_path="/img/101.png",
            checksum_sha256="h101",
        )
        assert await image_repo.image_exists("img-101") is True
        assert await image_repo.image_exists("no_such") is False

    async def test_get_images_by_checksum(self, image_repo: ImageRepository):
        await image_repo.create_image(
            uuid="img-200", original_filename="dup1.png",
            stored_filename="img-200.png", file_path="/img/200.png",
            checksum_sha256="dup_hash",
        )
        await image_repo.create_image(
            uuid="img-201", original_filename="dup2.png",
            stored_filename="img-201.png", file_path="/img/201.png",
            checksum_sha256="dup_hash",
        )
        results = await image_repo.get_images_by_checksum("dup_hash")
        assert len(results) == 2

    async def test_get_recent_images(self, image_repo: ImageRepository):
        await image_repo.create_image(
            uuid="img-300", original_filename="r.png",
            stored_filename="img-300.png", file_path="/img/300.png",
            checksum_sha256="h300",
        )
        results = await image_repo.get_recent_images(limit=5)
        assert any(i.uuid == "img-300" for i in results)

    async def test_get_recent_images_no_limit(self, image_repo: ImageRepository):
        results = await image_repo.get_recent_images()
        assert isinstance(results, (list, tuple))

    async def test_get_images_by_original_filename(self, image_repo: ImageRepository):
        await image_repo.create_image(
            uuid="img-400", original_filename="target.png",
            stored_filename="img-400.png", file_path="/img/400.png",
            checksum_sha256="h400",
        )
        results = await image_repo.get_images_by_original_filename("target.png")
        assert any(i.uuid == "img-400" for i in results)

    async def test_search_images_by_filename(self, image_repo: ImageRepository):
        await image_repo.create_image(
            uuid="img-500", original_filename="searchable_photo.png",
            stored_filename="img-500.png", file_path="/img/500.png",
            checksum_sha256="h500",
        )
        results = await image_repo.search_images_by_filename("searchable")
        assert any(i.uuid == "img-500" for i in results)

    async def test_count_images(self, image_repo: ImageRepository):
        initial = await image_repo.count_images()
        await image_repo.create_image(
            uuid="img-600", original_filename="c.png",
            stored_filename="img-600.png", file_path="/img/600.png",
            checksum_sha256="h600",
        )
        assert await image_repo.count_images() == initial + 1


class TestImageRepositoryUpdate:
    """更新相关测试。"""

    async def test_update_image(self, image_repo: ImageRepository):
        await image_repo.create_image(
            uuid="img-700", original_filename="old.png",
            stored_filename="img-700.png", file_path="/img/700.png",
            checksum_sha256="h700",
        )
        ok = await image_repo.update_image("img-700", original_filename="new.png")
        assert ok is True
        img = await image_repo.get_by_uuid("img-700")
        assert img is not None
        assert img.original_filename == "new.png"

    async def test_update_image_no_change(self, image_repo: ImageRepository):
        await image_repo.create_image(
            uuid="img-701", original_filename="same.png",
            stored_filename="img-701.png", file_path="/img/701.png",
            checksum_sha256="h701",
        )
        ok = await image_repo.update_image("img-701")
        assert ok is True

    async def test_update_nonexistent_image(self, image_repo: ImageRepository):
        ok = await image_repo.update_image("no_such", original_filename="x.png")
        assert ok is False


class TestImageRepositoryDelete:
    """删除相关测试。"""

    async def test_delete_image(self, image_repo: ImageRepository):
        await image_repo.create_image(
            uuid="img-800", original_filename="del.png",
            stored_filename="img-800.png", file_path="/img/800.png",
            checksum_sha256="h800",
        )
        ok = await image_repo.delete_image("img-800")
        assert ok is True
        assert await image_repo.get_by_uuid("img-800") is None

    async def test_delete_nonexistent_image(self, image_repo: ImageRepository):
        ok = await image_repo.delete_image("no_such")
        assert ok is False
