from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from nonebot import logger
from pathlib import Path
from typing import Optional
import re
import shutil
import sqlite3

from .dao import DAOFactory

class ConnectionManager:
    """
    管理 SQLite 数据库连接和事务，并负责数据库 Schema 的初始化与迁移。
    """
    db_path: Path
    _conn: Optional[sqlite3.Connection]
    dao: DAOFactory

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = None
        self.dao = DAOFactory(self)

    def _get_connection(self):
        """获取或创建数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    @contextmanager
    def cursor(self):
        """
        提供一个上下文管理器，用于获取数据库游标。
        在 `with` 块结束时自动提交或回滚事务。
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
            raise

    def close_connection(self):
        """显式关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed.")

    # Schema 初始化与迁移相关方法

    def _get_user_version(self) -> int:
        conn = self._get_connection()
        return conn.execute("PRAGMA user_version").fetchone()[0]

    def _set_user_version(self, version: int) -> None:
        with self.cursor() as cursor:
            cursor.execute(f"PRAGMA user_version = {int(version)}")

    def _run_sql_script(self, file_path: Path) -> None:
        if not file_path.exists():
            raise FileNotFoundError(f"找不到 SQL 脚本: {file_path}")
        script = file_path.read_text(encoding="utf-8")
        with self.cursor() as cursor:
            cursor.executescript(script)
        logger.info(f"执行 SQL 脚本完成: {file_path.name}")

    def _backup_database(self) -> Optional[Path]:
        """
        数据库创建备份。
        """
        if not self.db_path.exists():
            logger.warning(f"数据库文件不存在，跳过备份: {self.db_path}")
            return None

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_filename = f"zikequote3.{timestamp}.db.bak"
        backup_path = self.db_path.parent / backup_filename
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"数据库备份已创建: {backup_path}")
        return backup_path

    def backup_database(self) -> Optional[Path]:
        """
        手动触发数据库备份
        """
        return self._backup_database()

    def _collect_sequential_migrations(self, migrations_dir: Path):
        """
        读取迁移目录中形如 vX_to_vY.sql 的文件，
        仅接受 Y = X + 1 的连续迁移。
        返回 {from_version: (to_version, Path)} 字典。
        """
        migrations = {}
        if not migrations_dir.exists():
            return migrations

        pattern = re.compile(r"v(\d+)_to_v(\d+)\.sql$")
        for path in sorted(migrations_dir.glob("*.sql")):
            match = pattern.match(path.name)
            if not match:
                logger.debug(f"忽略无法解析的迁移文件: {path.name}")
                continue
            start, end = map(int, match.groups())
            if end != start + 1:
                logger.warning(f"忽略非连续迁移文件 ({path.name}): 仅支持 vN_to_vN+1")
                continue
            if start in migrations:
                logger.warning(f"检测到重复的起始版本迁移文件，将忽略: {path.name}")
                continue
            migrations[start] = (end, path)
        return migrations

    # 对外初始化入口

    def initialize_db(
        self,
        schema_file: Optional[Path] = None,
        migrations_dir: Optional[Path] = None
    ):
        """
        初始化数据库。如果是首次运行，执行 schema.sql；
        否则根据 PRAGMA user_version 自动执行增量迁移脚本。
        """
        if not schema_file:
            from ..imports import PluginPath
        else:
            module_database_root = schema_file.parent

        schema_file = (
            schema_file
            if schema_file is not None
            else PluginPath.module_database_root / "schema.sql"
        )
        migrations_dir = (
            migrations_dir
            if migrations_dir is not None
            else PluginPath.module_database_root / "migrations"
        )

        if not schema_file.exists():
            raise FileNotFoundError("无法找到数据库 schema 文件")

        current_version = self._get_user_version()
        logger.info(f"当前数据库版本: {current_version}")

        # 首次安装：执行 schema.sql
        if current_version == 0:
            logger.info("未检测到数据库版本，执行初始 Schema...")
            self._run_sql_script(schema_file)
            current_version = self._get_user_version()
            if current_version == 0:
                logger.warning("schema.sql 未设置 PRAGMA user_version，自动设为 1")
                self._set_user_version(1)
                current_version = 1
            logger.info(f"数据库初始化完成，版本: {current_version}")

        # 若有迁移，逐步执行
        migrations = self._collect_sequential_migrations(migrations_dir)
        target_version = current_version
        for end, _ in migrations.values():
            target_version = max(target_version, end)

        if current_version < target_version:
            logger.info("检测到数据库迁移需求，开始执行备份...")
            self._backup_database()

        while current_version < target_version:
            next_info = migrations.get(current_version)
            if not next_info:
                raise RuntimeError(
                    f"缺少从版本 {current_version} 升级到 {current_version + 1} 的迁移脚本"
                )
            next_version, migration_file = next_info
            logger.info(f"执行迁移: {current_version} -> {next_version} ({migration_file.name})")
            self._run_sql_script(migration_file)
            applied_version = self._get_user_version()
            if applied_version != next_version:
                logger.warning(f"迁移脚本未更新 user_version，自动设为 {next_version}")
                self._set_user_version(next_version)
                applied_version = next_version
            current_version = applied_version

        logger.info(f"数据库 Schema 已更新至最新版本: {current_version}")
