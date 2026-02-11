"""LanceDB 异步封装，管理向量存储的连接和表生命周期。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import lancedb
import pyarrow as pa


class VectorStore:
    """LanceDB 向量存储封装。"""

    QUOTE_TABLE = "quote_vectors"
    META_TABLE = "vector_meta"

    def __init__(self) -> None:
        self._db: Optional[lancedb.AsyncConnection] = None

    async def connect(self, db_path: str) -> None:
        """连接到 LanceDB 数据库。"""
        self._db = await lancedb.connect_async(db_path)

    def _get_db(self) -> lancedb.AsyncConnection:
        if self._db is None:
            raise RuntimeError("VectorStore 未连接，请先调用 connect()")
        return self._db

    async def ensure_table(self, dimensions: int) -> None:
        """确保 quote_vectors 表存在，不存在则创建。"""
        db = self._get_db()
        existing = await db.table_names()
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
        existing = await db.table_names()
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
        """
        if not records:
            return
        db = self._get_db()
        table = await db.open_table(self.QUOTE_TABLE)
        # 先删除已存在的记录
        quote_ids = [r["quote_id"] for r in records]
        id_list = ", ".join(f"'{qid}'" for qid in quote_ids)
        try:
            await table.delete(f"quote_id IN ({id_list})")
        except Exception:
            # 表为空时 delete 可能抛异常，忽略即可
            pass
        await table.add(records)

    async def delete(self, quote_ids: List[str]) -> None:
        """删除指定语录的向量记录。"""
        if not quote_ids:
            return
        db = self._get_db()
        table = await db.open_table(self.QUOTE_TABLE)
        id_list = ", ".join(f"'{qid}'" for qid in quote_ids)
        await table.delete(f"quote_id IN ({id_list})")

    async def search(
        self,
        query_vector: List[float],
        *,
        group_id: str,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """向量检索，返回 [{quote_id, group_id, content, similarity}, ...]。

        使用余弦距离（cosine distance），_distance 范围 [0, 2]，
        相似度 = 1 - distance。
        """
        db = self._get_db()
        table = await db.open_table(self.QUOTE_TABLE)

        # vector_search() 是同步方法，返回 AsyncVectorQuery；
        # to_list() 才是异步方法，await 必须作用于整个链的末端。
        results = await (
            table.vector_search(query_vector)
            .distance_type("cosine")
            .where(f"group_id = '{group_id}'")
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
        existing = await db.table_names()
        if self.QUOTE_TABLE in existing:
            await db.drop_table(self.QUOTE_TABLE)
        if self.META_TABLE in existing:
            await db.drop_table(self.META_TABLE)

    async def get_meta(self) -> Dict[str, str]:
        """获取元信息，返回 {key: value} 字典。"""
        db = self._get_db()
        existing = await db.table_names()
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
        """更新元信息（model_name / dimensions / last_reindex_time）。"""
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
        """返回 quote_vectors 表的记录总数。"""
        db = self._get_db()
        existing = await db.table_names()
        if self.QUOTE_TABLE not in existing:
            return 0
        table = await db.open_table(self.QUOTE_TABLE)
        return await table.count_rows()
