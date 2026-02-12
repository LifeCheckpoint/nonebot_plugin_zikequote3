"""
SQLAlchemy 基础设施层单元测试。

验证 Base 类、engine 工厂、session 工厂以及 SQLite PRAGMA 配置。
"""

from sqlalchemy import text

from nonebot_plugin_zikequote3.database.sa import (
    Base,
    create_async_engine_factory,
    create_async_session_factory,
)


class TestBaseClass:
    """验证 Base 声明式基类。"""

    def test_base_importable(self):
        """Base 类可以正常导入。"""
        assert Base is not None

    def test_base_has_metadata(self):
        """Base 类具有 metadata 属性。"""
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None

    def test_base_has_registry(self):
        """Base 类具有 registry 属性。"""
        assert hasattr(Base, "registry")
        assert Base.registry is not None


class TestEngineFactory:
    """验证 create_async_engine_factory 工厂函数。"""

    async def test_create_engine_memory(self):
        """使用 :memory: 创建引擎。"""
        engine = create_async_engine_factory(":memory:")
        try:
            assert engine is not None
            assert str(engine.url) == "sqlite+aiosqlite:///:memory:"
        finally:
            await engine.dispose()

    async def test_create_engine_connect(self):
        """引擎能正常连接并执行查询。"""
        engine = create_async_engine_factory(":memory:")
        try:
            async with engine.connect() as conn:
                result = await conn.exec_driver_sql("SELECT 1")
                assert result.scalar() == 1
        finally:
            await engine.dispose()


class TestSessionFactory:
    """验证 create_async_session_factory 工厂函数。"""

    async def test_create_session_factory(self, async_engine):
        """能正常创建 session factory。"""
        factory = create_async_session_factory(async_engine)
        assert factory is not None
        assert callable(factory)

    async def test_session_execute_query(self, async_session_factory):
        """通过 session factory 创建的 session 能执行查询。"""
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 100"))
            assert result.scalar() == 100


class TestPragmaConfiguration:
    """验证 SQLite PRAGMA 配置在连接时生效。"""

    async def test_pragma_journal_mode_memory(self, async_engine):
        """内存数据库的 journal_mode 固定为 'memory'（SQLite 限制）。"""
        async with async_engine.connect() as conn:
            result = await conn.exec_driver_sql("PRAGMA journal_mode")
            value = result.scalar()
            assert value == "memory", f"Expected 'memory' for :memory: db, got '{value}'"

    async def test_pragma_journal_mode_wal(self, tmp_path):
        """文件数据库的 journal_mode 应为 wal。"""
        db_file = tmp_path / "test_wal.db"
        engine = create_async_engine_factory(db_file)
        try:
            async with engine.connect() as conn:
                result = await conn.exec_driver_sql("PRAGMA journal_mode")
                value = result.scalar()
                assert value == "wal", f"Expected 'wal', got '{value}'"
        finally:
            await engine.dispose()

    async def test_pragma_foreign_keys(self, async_engine):
        """PRAGMA foreign_keys 应为 1（启用）。"""
        async with async_engine.connect() as conn:
            result = await conn.exec_driver_sql("PRAGMA foreign_keys")
            value = result.scalar()
            assert value == 1, f"Expected 1, got {value}"

    async def test_pragma_busy_timeout(self, async_engine):
        """PRAGMA busy_timeout 应为 30000。"""
        async with async_engine.connect() as conn:
            result = await conn.exec_driver_sql("PRAGMA busy_timeout")
            value = result.scalar()
            assert value == 30000, f"Expected 30000, got {value}"


class TestMetadataCreateAll:
    """验证 Base.metadata.create_all 可正确创建已注册的 ORM 模型表。"""

    async def test_create_all_creates_registered_tables(self):
        """create_all 应成功创建所有已注册 ORM 模型对应的表。"""
        engine = create_async_engine_factory(":memory:")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with engine.connect() as conn:
                result = await conn.exec_driver_sql(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                tables = set(result.scalars().all())
                expected = {"users", "groups", "group_members", "user_nicknames", "group_nicknames"}
                assert expected.issubset(tables), (
                    f"Expected at least {expected}, got {tables}"
                )
        finally:
            await engine.dispose()
