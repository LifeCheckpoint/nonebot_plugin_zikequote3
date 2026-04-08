"""SQLite 连接/事务边界回归测试。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from nonebot_plugin_zikequote3.database.sa import (
    Base,
    create_async_engine_factory,
    create_async_session_factory,
)
from nonebot_plugin_zikequote3.database.sa.models import *  # noqa: F401, F403
from nonebot_plugin_zikequote3.di.container import create_container


async def _get_driver_connection_id(session: AsyncSession) -> int:
    async_conn = await session.connection()
    pool_proxy = async_conn.sync_connection.connection
    driver_connection = getattr(pool_proxy, "driver_connection", None)
    if driver_connection is not None:
        return id(driver_connection)

    dbapi_connection = getattr(pool_proxy, "dbapi_connection")
    driver_connection = getattr(dbapi_connection, "driver_connection", dbapi_connection)
    return id(driver_connection)


class TestSQLiteEngineSessionBoundaries:
    """验证 SQLite 引擎与 session 工厂的连接边界。"""

    async def test_file_sqlite_sessions_have_distinct_connections_and_isolated_transactions(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "file_session_boundaries.db"
        engine = create_async_engine_factory(db_path)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            session_factory = create_async_session_factory(engine)

            async with session_factory() as write_session, session_factory() as read_session:
                write_conn_id = await _get_driver_connection_id(write_session)
                read_conn_id = await _get_driver_connection_id(read_session)
                assert write_conn_id != read_conn_id

                await write_session.execute(
                    text("INSERT INTO users (qq_id, avatar) VALUES ('file_user', NULL)")
                )

                count_before_commit = (
                    await read_session.execute(
                        text("SELECT COUNT(*) FROM users WHERE qq_id = 'file_user'")
                    )
                ).scalar_one()
                assert count_before_commit == 0

                await write_session.commit()

            async with session_factory() as verify_session:
                count_after_commit = (
                    await verify_session.execute(
                        text("SELECT COUNT(*) FROM users WHERE qq_id = 'file_user'")
                    )
                ).scalar_one()

            assert count_after_commit == 1
        finally:
            await engine.dispose()

    async def test_memory_sqlite_sessions_share_same_in_memory_database_within_engine(
        self,
    ) -> None:
        engine = create_async_engine_factory(":memory:")

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            session_factory = create_async_session_factory(engine)

            async with session_factory() as first_session:
                await first_session.execute(
                    text("INSERT INTO users (qq_id, avatar) VALUES ('memory_user', NULL)")
                )
                await first_session.commit()

            async with session_factory() as second_session:
                count = (
                    await second_session.execute(
                        text("SELECT COUNT(*) FROM users WHERE qq_id = 'memory_user'")
                    )
                ).scalar_one()

            assert count == 1
        finally:
            await engine.dispose()


class TestDatabaseProviderRequestBoundaries:
    """验证 dishka REQUEST 作用域下的 SQLite 会话边界。"""

    async def test_request_scoped_sessions_use_distinct_connections_for_file_sqlite(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "provider_request_boundaries.db"
        container = create_container(
            db_path=db_path,
            image_store_path=tmp_path / "images",
        )

        try:
            async with container() as bootstrap_scope:
                engine = await bootstrap_scope.get(AsyncEngine)
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

            async with container() as read_scope:
                read_session = await read_scope.get(AsyncSession)

                async with container() as write_scope:
                    write_session = await write_scope.get(AsyncSession)

                    write_conn_id = await _get_driver_connection_id(write_session)
                    read_conn_id = await _get_driver_connection_id(read_session)
                    assert write_conn_id != read_conn_id

                    await write_session.execute(
                        text("INSERT INTO users (qq_id, avatar) VALUES ('provider_user', NULL)")
                    )

                    count_before_scope_exit = (
                        await read_session.execute(
                            text("SELECT COUNT(*) FROM users WHERE qq_id = 'provider_user'")
                        )
                    ).scalar_one()
                    assert count_before_scope_exit == 0

                await read_session.rollback()

                count_after_scope_exit = (
                    await read_session.execute(
                        text("SELECT COUNT(*) FROM users WHERE qq_id = 'provider_user'")
                    )
                ).scalar_one()
                assert count_after_scope_exit == 1
        finally:
            await container.close()
