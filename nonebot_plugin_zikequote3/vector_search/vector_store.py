"""LanceDB 异步封装，管理向量存储的连接和表生命周期。

提供对 LanceDB 的异步连接管理、表创建、向量记录的增删查，
以及元信息（模型名称、维度、重建时间）的读写功能。
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import lancedb
import pyarrow as pa

# quote_id 允许的字符：数字、字母、下划线、连字符
_SAFE_ID_RE = re.compile(r"^[\w-]+$")


class VectorStore:
    """LanceDB 向量存储封装。

    管理向量数据库的连接、表生命周期和向量记录的 CRUD 操作，
    同时维护模型元信息以支持一致性检查。
    """

    QUOTE_TABLE = "quote_vectors"
    META_TABLE = "vector_meta"

    def __init__(self) -> None:
        self._db: Optional[lancedb.AsyncConnection] = None
        self.reindex_lock: asyncio.Lock = asyncio.Lock()

    # ---- 输入校验 / 安全过滤 ----

    @staticmethod
    def _sanitize_quote_id(quote_id: str) -> str:
        """校验 quote_id 只含安全字符（字母、数字、下划线、连字符）。

        :param quote_id: 待校验的语录 ID。
        :type quote_id: str
        :returns: 校验通过的语录 ID。
        :rtype: str
        :raises ValueError: 当 quote_id 包含非法字符时抛出。
        """
        if not isinstance(quote_id, str) or not _SAFE_ID_RE.match(quote_id):
            raise ValueError(f"非法 quote_id: {quote_id!r}")
        return quote_id

    @staticmethod
    def _sanitize_group_id(group_id: str) -> str:
        """校验 group_id 只含数字字符。

        :param group_id: 待校验的群组 ID。
        :type group_id: str
        :returns: 校验通过的群组 ID。
        :rtype: str
        :raises ValueError: 当 group_id 包含非数字字符时抛出。
        """
        if not isinstance(group_id, str) or not group_id.isdigit():
            raise ValueError(f"非法 group_id: {group_id!r}")
        return group_id

    @classmethod
    def _safe_quote_filter(cls, quote_ids: List[str]) -> str:
        """构建安全的 quote_id IN (...) 过滤子句。

        :param quote_ids: 语录 ID 列表。
        :type quote_ids: List[str]
        :returns: SQL 过滤子句字符串。
        :rtype: str
        :raises ValueError: 当任一 quote_id 包含非法字符时抛出。
        """
        safe_ids = [cls._sanitize_quote_id(qid) for qid in quote_ids]
        id_list = ", ".join(f"'{qid}'" for qid in safe_ids)
        return f"quote_id IN ({id_list})"

    @classmethod
    def _safe_group_filter(cls, group_id: str) -> str:
        """构建安全的 group_id = '...' 过滤子句。

        :param group_id: 群组 ID。
        :type group_id: str
        :returns: SQL 过滤子句字符串。
        :rtype: str
        :raises ValueError: 当 group_id 包含非数字字符时抛出。
        """
        safe_id = cls._sanitize_group_id(group_id)
        return f"group_id = '{safe_id}'"

    async def connect(self, db_path: str) -> None:
        """连接到 LanceDB 数据库。

        :param db_path: 数据库文件路径。
        :type db_path: str
        """
        self._db = await lancedb.connect_async(db_path)

    def _get_db(self) -> lancedb.AsyncConnection:
        """获取数据库连接，未连接时抛出异常。

        :returns: 异步数据库连接对象。
        :rtype: lancedb.AsyncConnection
        :raises RuntimeError: 当未调用 :meth:`connect` 时抛出。
        """
        if self._db is None:
            raise RuntimeError("VectorStore 未连接，请先调用 connect()")
        return self._db

    async def ensure_table(self, dimensions: int) -> None:
        """确保 quote_vectors 表存在，不存在则创建。

        :param dimensions: 向量维度。
        :type dimensions: int
        """
        db = self._get_db()
        existing = list(await db.list_tables())
        if self.QUOTE_TABLE not in existing:
            schema = pa.schema(
                [
                    pa.field("quote_id", pa.utf8()),
                    pa.field("group_id", pa.utf8()),
                    pa.field("content", pa.utf8()),
                    pa.field("vector", pa.list_(pa.float32(), dimensions)),
                ]
            )
            await db.create_table(self.QUOTE_TABLE, schema=schema)

    async def _ensure_meta_table(self) -> None:
        """确保 vector_meta 表存在。"""
        db = self._get_db()
        existing = list(await db.list_tables())
        if self.META_TABLE not in existing:
            schema = pa.schema(
                [
                    pa.field("key", pa.utf8()),
                    pa.field("value", pa.utf8()),
                ]
            )
            await db.create_table(self.META_TABLE, schema=schema)

    async def upsert(self, records: List[Dict[str, Any]]) -> None:
        """插入或更新向量记录。

        每条记录需包含 quote_id, group_id, content, vector。
        使用 delete + add 模拟 upsert（LanceDB 无原生 upsert）。

        :param records: 向量记录列表，每条包含 quote_id、group_id、content、vector。
        :type records: List[Dict[str, Any]]
        """
        if not records:
            return
        db = self._get_db()
        table = await db.open_table(self.QUOTE_TABLE)
        # 先删除已存在的记录
        quote_ids = [r["quote_id"] for r in records]
        try:
            await table.delete(self._safe_quote_filter(quote_ids))
        except Exception:
            # 表为空时 delete 可能抛异常，忽略即可
            pass
        await table.add(records)

    async def delete(self, quote_ids: List[str]) -> None:
        """删除指定语录的向量记录。

        :param quote_ids: 待删除的语录 ID 列表。
        :type quote_ids: List[str]
        """
        if not quote_ids:
            return
        db = self._get_db()
        table = await db.open_table(self.QUOTE_TABLE)
        await table.delete(self._safe_quote_filter(quote_ids))

    async def delete_by_group(self, group_id: str) -> None:
        """删除指定群组的所有向量记录。

        :param group_id: 群组 ID。
        :type group_id: str
        """
        db = self._get_db()
        existing = list(await db.list_tables())
        if self.QUOTE_TABLE not in existing:
            return
        table = await db.open_table(self.QUOTE_TABLE)
        await table.delete(self._safe_group_filter(group_id))

    async def search(
        self,
        query_vector: List[float],
        *,
        group_id: str,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """向量检索，返回相似语录列表。

        使用余弦距离（cosine distance），_distance 范围 [0, 2]，
        相似度 = 1 - distance。

        :param query_vector: 查询向量。
        :type query_vector: List[float]
        :param group_id: 群组 ID，用于过滤结果。
        :type group_id: str
        :param limit: 最大返回结果数量，默认为 10。
        :type limit: int
        :param threshold: 相似度阈值，低于此值的结果将被过滤，默认为 0.0。
        :type threshold: float
        :returns: 结果列表，每项包含 quote_id、group_id、content、similarity。
        :rtype: List[Dict[str, Any]]
        """
        db = self._get_db()
        table = await db.open_table(self.QUOTE_TABLE)

        # vector_search() 是同步方法，返回 AsyncVectorQuery；
        # to_list() 才是异步方法，await 必须作用于整个链的末端。
        results = await (
            table.vector_search(query_vector)
            .distance_type("cosine")
            .where(self._safe_group_filter(group_id))
            .limit(limit)
            .to_list()
        )

        output: List[Dict[str, Any]] = []
        for row in results:
            similarity = 1.0 - row.get("_distance", 0.0)
            if threshold > 0 and similarity < threshold:
                continue
            output.append(
                {
                    "quote_id": row["quote_id"],
                    "group_id": row["group_id"],
                    "content": row["content"],
                    "similarity": similarity,
                }
            )
        return output

    async def drop_all(self) -> None:
        """删除所有向量数据表（重建前调用）。"""
        db = self._get_db()
        existing = list(await db.list_tables())
        if self.QUOTE_TABLE in existing:
            await db.drop_table(self.QUOTE_TABLE)
        if self.META_TABLE in existing:
            await db.drop_table(self.META_TABLE)

    async def get_meta(self) -> Dict[str, str]:
        """获取元信息。

        :returns: 元信息字典，键值对形式。
        :rtype: Dict[str, str]
        """
        db = self._get_db()
        existing = list(await db.list_tables())
        if self.META_TABLE not in existing:
            return {}
        table = await db.open_table(self.META_TABLE)
        rows = await table.to_arrow()
        result: Dict[str, str] = {}
        for i in range(rows.num_rows):
            key = rows.column("key")[i].as_py()
            value = rows.column("value")[i].as_py()
            result[key] = value
        return result

    async def set_meta(self, model_name: str, dimensions: int) -> None:
        """更新元信息（model_name / dimensions / last_reindex_time）。

        :param model_name: 模型名称。
        :type model_name: str
        :param dimensions: 向量维度。
        :type dimensions: int
        """
        await self._ensure_meta_table()
        db = self._get_db()
        table = await db.open_table(self.META_TABLE)
        # 清空后重写
        try:
            await table.delete("key IS NOT NULL")
        except Exception:
            pass
        now = datetime.now(timezone.utc).isoformat()
        await table.add(
            [
                {"key": "model_name", "value": model_name},
                {"key": "dimensions", "value": str(dimensions)},
                {"key": "last_reindex_time", "value": now},
            ]
        )

    async def count(self) -> int:
        """返回 quote_vectors 表的记录总数。

        :returns: 记录总数。
        :rtype: int
        """
        db = self._get_db()
        existing = list(await db.list_tables())
        if self.QUOTE_TABLE not in existing:
            return 0
        table = await db.open_table(self.QUOTE_TABLE)
        return await table.count_rows()
