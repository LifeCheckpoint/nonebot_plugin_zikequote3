from contextlib import contextmanager
from pathlib import Path
from typing import Optional
import logging
import sqlite3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConnectionManager:
    """
    管理 SQLite 数据库连接和事务。
    提供一个上下文管理器来自动处理连接的打开和关闭。
    """
    db_path: Path
    _conn: Optional[sqlite3.Connection]
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = None

    def _get_connection(self):
        """获取或创建数据库连接"""
        if self._conn is None:
            # 连接，自动创建数据库文件
            self._conn = sqlite3.connect(self.db_path)
            # 设置 row_factory 为 sqlite3.Row，使查询结果可以通过列名访问
            self._conn.row_factory = sqlite3.Row
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
            conn.commit() # 默认提交事务
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            conn.rollback()
            raise
        finally:
            # 可在应用程序退出时手动调用 close_connection
            pass

    def close_connection(self):
        """显式关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logging.info("Database connection closed.")

    def initialize_db(self, schema_file: Optional[Path]):
        """
        根据 schema 文件初始化数据库（创建表等）。
        """
        if schema_file is None or not schema_file.exists():
            schema_file = Path(__file__).parent / "schema.sql"
            if not schema_file.exists():
                raise FileNotFoundError("无法找到数据库 schema 文件")            

        schema_sql = schema_file.read_text(encoding="utf-8")
        
        with self.cursor() as cursor:
            try:
                cursor.executescript(schema_sql)
                logging.info("已检查数据库完整性")
            except sqlite3.Error as e:
                logging.error(f"无法初始化数据库: {e}")
                raise
