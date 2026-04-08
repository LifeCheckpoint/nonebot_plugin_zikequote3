"""程序化 Alembic 迁移辅助。

供插件启动阶段调用，统一把数据库升级到 Alembic head，
并为历史上通过 ORM 直接建表、但尚未写入 Alembic 版本号的数据库
提供受控的兼容引导路径。
"""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.engine import Connection

from .sa import create_async_engine_factory

_INITIAL_REVISION: Final[str] = "9a62ce7e5cff"
_QUOTE_SCHEMA_CHECK_NAME: Final[str] = "ck_quotes_content_or_image_present"
_USER_NICKNAME_CURRENT_INDEX_NAME: Final[str] = "uq_user_nicknames_current_using"
_GROUP_NICKNAME_CURRENT_INDEX_NAME: Final[str] = "uq_group_nicknames_current_using"
_ALEMBIC_INI_PATH: Final[Path] = Path(__file__).resolve().parent.parent / "alembic.ini"
_DatabaseState = Literal[
    "empty",
    "versioned",
    "unversioned_head",
    "unversioned_legacy",
]


class DatabaseMigrationError(RuntimeError):
    """启动阶段数据库迁移失败。"""


def _make_alembic_config(connection: Connection) -> Config:
    cfg = Config(str(_ALEMBIC_INI_PATH))
    cfg.attributes["connection"] = connection
    return cfg


def _expected_user_tables() -> set[str]:
    from .sa import models as _models  # noqa: F401
    from .sa.base import Base

    return set(Base.metadata.tables.keys())


def _is_quote_schema_aligned(connection: Connection) -> bool:
    inspector = sa_inspect(connection)
    quote_columns = {
        column["name"]: column
        for column in inspector.get_columns("quotes")
    }
    content_column = quote_columns.get("content")
    if content_column is None or not content_column.get("nullable", False):
        return False

    check_constraints = inspector.get_check_constraints("quotes")
    return any(
        constraint.get("name") == _QUOTE_SCHEMA_CHECK_NAME
        for constraint in check_constraints
    )



def _is_current_nickname_schema_aligned(connection: Connection) -> bool:
    inspector = sa_inspect(connection)
    user_indexes = {
        index.get("name")
        for index in inspector.get_indexes("user_nicknames")
        if index.get("name")
    }
    group_indexes = {
        index.get("name")
        for index in inspector.get_indexes("group_nicknames")
        if index.get("name")
    }
    return (
        _USER_NICKNAME_CURRENT_INDEX_NAME in user_indexes
        and _GROUP_NICKNAME_CURRENT_INDEX_NAME in group_indexes
    )



def _detect_database_state(connection: Connection) -> _DatabaseState:
    inspector = sa_inspect(connection)
    table_names = set(inspector.get_table_names())

    if "alembic_version" in table_names:
        return "versioned"

    user_tables = table_names - {"alembic_version"}
    if not user_tables:
        return "empty"

    expected_tables = _expected_user_tables()
    if user_tables != expected_tables:
        raise DatabaseMigrationError(
            "检测到未受 Alembic 管理的非空数据库，但表集合与插件已知 schema 不一致，"
            f"无法安全自动迁移。当前表集合={sorted(user_tables)}；"
            f"期望表集合={sorted(expected_tables)}"
        )

    if _is_quote_schema_aligned(connection) and _is_current_nickname_schema_aligned(connection):
        return "unversioned_head"

    return "unversioned_legacy"


def _stamp_initial_revision(connection: Connection) -> None:
    command.stamp(_make_alembic_config(connection), _INITIAL_REVISION)


def _upgrade_to_head(connection: Connection) -> None:
    command.upgrade(_make_alembic_config(connection), "head")


async def migrate_database_to_head(db_path: str | Path) -> None:
    """将数据库升级到当前 Alembic head revision。"""
    engine = create_async_engine_factory(db_path)
    db_target = str(db_path)

    try:
        async with engine.connect() as async_conn:
            state = await async_conn.run_sync(_detect_database_state)
            if state == "unversioned_head":
                await async_conn.run_sync(
                    lambda connection: command.stamp(
                        _make_alembic_config(connection),
                        "head",
                    )
                )
                await async_conn.commit()
                return

            if state == "unversioned_legacy":
                await async_conn.run_sync(_stamp_initial_revision)
                await async_conn.commit()

            await async_conn.run_sync(_upgrade_to_head)
            await async_conn.commit()
    except DatabaseMigrationError:
        raise
    except Exception as exc:  # pragma: no cover - 作为启动期兜底边界
        raise DatabaseMigrationError(
            f"数据库迁移到 Alembic head 失败: {db_target}"
        ) from exc
    finally:
        await engine.dispose()
