"""
QuoteRepository —— 语录数据仓储，对应原 ``QuoteDAO``。

覆盖原 DAO 的所有公开方法，用 SQLAlchemy ORM 重写。
返回 Pydantic DTO，ORM 模型不泄露到 Repository 外部。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import Integer, delete, func, select, update

from ..models.quotes import Quote, QuoteCreate, QuoteUpdate
from ..sa.models.quote import QuoteModel
from .base import BaseRepository


class QuoteRepository(BaseRepository[QuoteModel, QuoteCreate, Quote]):
    """语录 Repository，覆盖 ``QuoteDAO`` 全部公开方法。

    提供语录的 CRUD、统计、排行等操作，返回 Pydantic DTO。
    """

    model_class = QuoteModel

    # ---- 创建 ----

    async def create_quote(
        self,
        quote_id: str,
        author_id: str,
        group_id: str,
        content: Optional[str] = None,
        image_content_uuid: Optional[str] = None,
        total_show_time: int = 0,
    ) -> Quote:
        """创建新语录并返回 DTO。

        :param quote_id: 语录 ID。
        :type quote_id: str
        :param author_id: 作者 ID。
        :type author_id: str
        :param group_id: 群组 ID。
        :type group_id: str
        :param content: 语录文本内容。
        :type content: Optional[str]
        :param image_content_uuid: 关联图片的 UUID。
        :type image_content_uuid: Optional[str]
        :param total_show_time: 初始展示次数。
        :type total_show_time: int
        :returns: 创建后的语录 DTO。
        :rtype: Quote
        """
        dto = QuoteCreate(
            quote_id=quote_id,
            author_id=author_id,
            group_id=group_id,
            content=content,
            image_content_uuid=image_content_uuid,
            total_show_time=total_show_time,
        )
        return await self.create(dto)

    async def batch_create_quotes(self, quotes: List[QuoteCreate]) -> bool:
        """批量创建语录。

        :param quotes: 语录创建 DTO 列表。
        :type quotes: List[QuoteCreate]
        :returns: 操作是否成功。
        :rtype: bool
        """
        if not quotes:
            return True
        instances = [QuoteModel.from_create_dto(q) for q in quotes]
        self._session.add_all(instances)
        await self._session.flush()
        return True

    async def batch_clone_quotes(self, quotes: Sequence[Quote]) -> bool:
        """批量克隆已有语录并保留原始时间戳。

        :param quotes: 待克隆的语录 DTO 列表。
        :type quotes: Sequence[Quote]
        :returns: 操作是否成功。
        :rtype: bool
        """
        if not quotes:
            return True

        instances = [
            QuoteModel(
                quote_id=quote.quote_id,
                author_id=quote.author_id,
                group_id=quote.group_id,
                content=quote.content,
                image_content_uuid=quote.image_content_uuid,
                total_show_time=quote.total_show_time,
                time_stamp=quote.time_stamp,
            )
            for quote in quotes
        ]
        self._session.add_all(instances)
        await self._session.flush()
        return True

    # ---- 查询（单条） ----

    async def get_quote_by_id(self, quote_id: str) -> Optional[Quote]:
        """按语录 ID 查询。

        :param quote_id: 语录 ID。
        :type quote_id: str
        :returns: 语录 DTO，不存在时返回 ``None``。
        :rtype: Optional[Quote]
        """
        return await self.get_by_id(quote_id)

    async def get_random_quote(
        self, group_id: Optional[str] = None
    ) -> Optional[Quote]:
        """随机获取一条语录，可按群过滤。

        :param group_id: 群组 ID，``None`` 表示不限群。
        :type group_id: Optional[str]
        :returns: 随机语录 DTO，无数据时返回 ``None``。
        :rtype: Optional[Quote]
        """
        stmt = select(QuoteModel)
        if group_id is not None:
            stmt = stmt.where(QuoteModel.group_id == group_id)
        stmt = stmt.order_by(func.random()).limit(1)
        result = await self._session.execute(stmt)
        instance = result.scalars().first()
        return instance.to_dto() if instance else None

    # ---- 查询（列表） ----

    async def get_quotes_by_group(
        self,
        group_id: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """按群查询语录（按时间升序）。

        :param group_id: 群组 ID。
        :type group_id: str
        :param limit: 最大返回数量，``None`` 表示不限制。
        :type limit: Optional[int]
        :param offset: 分页偏移量。
        :type offset: int
        :returns: 语录 DTO 序列。
        :rtype: Sequence[Quote]
        """
        stmt = (
            select(QuoteModel)
            .where(QuoteModel.group_id == group_id)
            .order_by(QuoteModel.time_stamp.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_quotes_by_author(
        self,
        author_id: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """按作者查询语录（按时间升序）。

        :param author_id: 作者 ID。
        :type author_id: str
        :param limit: 最大返回数量，``None`` 表示不限制。
        :type limit: Optional[int]
        :param offset: 分页偏移量。
        :type offset: int
        :returns: 语录 DTO 序列。
        :rtype: Sequence[Quote]
        """
        stmt = (
            select(QuoteModel)
            .where(QuoteModel.author_id == author_id)
            .order_by(QuoteModel.time_stamp.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_quotes_by_group_and_author(
        self,
        group_id: str,
        author_id: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """按群 + 作者查询语录（按时间升序）。

        :param group_id: 群组 ID。
        :type group_id: str
        :param author_id: 作者 ID。
        :type author_id: str
        :param limit: 最大返回数量，``None`` 表示不限制。
        :type limit: Optional[int]
        :param offset: 分页偏移量。
        :type offset: int
        :returns: 语录 DTO 序列。
        :rtype: Sequence[Quote]
        """
        stmt = (
            select(QuoteModel)
            .where(QuoteModel.group_id == group_id, QuoteModel.author_id == author_id)
            .order_by(QuoteModel.time_stamp.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_text_only_quotes_for_dedup(
        self,
        group_id: str,
        *,
        author_id: Optional[str] = None,
    ) -> Sequence[Quote]:
        """获取用于去重的纯文本语录候选集。

        仅返回满足以下条件的语录：
        - 属于指定群组
        - 无关联图片
        - 文本内容非空且去除首尾空白后非空
        - 按创建时间升序排列，以便保留较早语录

        :param group_id: 群组 ID。
        :type group_id: str
        :param author_id: 可选的作者 ID；提供时仅返回该作者的语录。
        :type author_id: Optional[str]
        :returns: 满足条件的语录 DTO 序列。
        :rtype: Sequence[Quote]
        """
        stmt = (
            select(QuoteModel)
            .where(
                QuoteModel.group_id == group_id,
                QuoteModel.image_content_uuid.is_(None),
                QuoteModel.content.is_not(None),
                func.trim(QuoteModel.content) != "",
            )
            .order_by(QuoteModel.time_stamp.asc(), QuoteModel.quote_id.asc())
        )
        if author_id is not None:
            stmt = stmt.where(QuoteModel.author_id == author_id)

        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def search_quotes_by_content(
        self,
        keyword: str,
        group_id: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """按内容关键词搜索语录（LIKE 匹配，按时间降序）。

        :param keyword: 搜索关键词，内部自动添加 ``%`` 通配符。
        :type keyword: str
        :param group_id: 群组 ID，``None`` 表示不限群。
        :type group_id: Optional[str]
        :param limit: 最大返回数量，``None`` 表示不限制。
        :type limit: Optional[int]
        :param offset: 分页偏移量。
        :type offset: int
        :returns: 匹配的语录 DTO 序列。
        :rtype: Sequence[Quote]
        """
        pattern = f"%{keyword}%"
        stmt = (
            select(QuoteModel)
            .where(QuoteModel.content.like(pattern))
            .order_by(QuoteModel.time_stamp.desc())
        )
        if group_id is not None:
            stmt = stmt.where(QuoteModel.group_id == group_id)
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_popular_quotes(
        self,
        group_id: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """获取热门语录（按展示次数降序）。

        :param group_id: 群组 ID，``None`` 表示不限群。
        :type group_id: Optional[str]
        :param limit: 最大返回数量，``None`` 表示不限制。
        :type limit: Optional[int]
        :param offset: 分页偏移量。
        :type offset: int
        :returns: 语录 DTO 序列。
        :rtype: Sequence[Quote]
        """
        stmt = select(QuoteModel).order_by(QuoteModel.total_show_time.desc())
        if group_id is not None:
            stmt = stmt.where(QuoteModel.group_id == group_id)
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_recent_quotes(
        self,
        group_id: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """获取最近的语录（按时间降序）。

        :param group_id: 群组 ID，``None`` 表示不限群。
        :type group_id: Optional[str]
        :param limit: 最大返回数量，``None`` 表示不限制。
        :type limit: Optional[int]
        :param offset: 分页偏移量。
        :type offset: int
        :returns: 语录 DTO 序列。
        :rtype: Sequence[Quote]
        """
        stmt = select(QuoteModel).order_by(QuoteModel.time_stamp.desc())
        if group_id is not None:
            stmt = stmt.where(QuoteModel.group_id == group_id)
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_all_quotes(self) -> Sequence[Quote]:
        """获取所有语录（按时间升序）。

        :returns: 全部语录 DTO 序列。
        :rtype: Sequence[Quote]
        """
        stmt = select(QuoteModel).order_by(QuoteModel.time_stamp.asc())
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    # ---- 存在性检查 ----

    async def check_quote_exists_by_author_content(
        self, author_id: str, content: str
    ) -> bool:
        """检查指定作者和内容的语录是否存在。

        :param author_id: 作者 ID。
        :type author_id: str
        :param content: 语录文本内容。
        :type content: str
        :returns: 是否存在。
        :rtype: bool
        """
        stmt = (
            select(func.count())
            .select_from(QuoteModel)
            .where(QuoteModel.author_id == author_id, QuoteModel.content == content)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    # ---- 统计 ----

    async def count_quotes_by_group(self, group_id: str) -> int:
        """统计群组语录数量。

        :param group_id: 群组 ID。
        :type group_id: str
        :returns: 语录数量。
        :rtype: int
        """
        stmt = (
            select(func.count())
            .select_from(QuoteModel)
            .where(QuoteModel.group_id == group_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_quotes_by_author(self, author_id: str) -> int:
        """统计作者语录数量。

        :param author_id: 作者 ID。
        :type author_id: str
        :returns: 语录数量。
        :rtype: int
        """
        stmt = (
            select(func.count())
            .select_from(QuoteModel)
            .where(QuoteModel.author_id == author_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_quotes_by_group_and_author(
        self, group_id: str, author_id: str
    ) -> int:
        """统计群组内指定作者的语录数量。

        :param group_id: 群组 ID。
        :type group_id: str
        :param author_id: 作者 ID。
        :type author_id: str
        :returns: 语录数量。
        :rtype: int
        """
        stmt = (
            select(func.count())
            .select_from(QuoteModel)
            .where(QuoteModel.group_id == group_id, QuoteModel.author_id == author_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_max_quote_id(self) -> int:
        """获取当前数据库中最大的语录 ID（转为整数）。

        :returns: 最大语录 ID，无数据时返回 ``0``。
        :rtype: int
        """
        stmt = select(func.max(func.cast(QuoteModel.quote_id, Integer)))
        result = await self._session.execute(stmt)
        value = result.scalar_one_or_none()
        return value if value is not None else 0

    async def get_quote_statistics_by_group(
        self, group_id: str
    ) -> Dict[str, Any]:
        """获取群组语录统计信息。

        :param group_id: 群组 ID。
        :type group_id: str
        :returns: 包含 ``total_quotes`` / ``unique_authors`` /
            ``total_shows`` / ``avg_shows`` 的字典。
        :rtype: Dict[str, Any]
        """
        stmt = (
            select(
                func.count().label("total_quotes"),
                func.count(func.distinct(QuoteModel.author_id)).label("unique_authors"),
                func.coalesce(func.sum(QuoteModel.total_show_time), 0).label("total_shows"),
                func.coalesce(func.avg(QuoteModel.total_show_time), 0).label("avg_shows"),
            )
            .select_from(QuoteModel)
            .where(QuoteModel.group_id == group_id)
        )
        result = await self._session.execute(stmt)
        row = result.one()
        return {
            "total_quotes": row.total_quotes,
            "unique_authors": row.unique_authors,
            "total_shows": row.total_shows,
            "avg_shows": round(float(row.avg_shows), 2),
        }

    async def get_author_ranking(
        self, group_id: str, *, limit: int = 10
    ) -> Sequence[Tuple[str, int]]:
        """获取群组内作者排行榜（按语录数降序）。

        :param group_id: 群组 ID。
        :type group_id: str
        :param limit: 排行榜最大条目数。
        :type limit: int
        :returns: ``[(author_id, quote_count), ...]`` 元组序列。
        :rtype: Sequence[Tuple[str, int]]
        """
        stmt = (
            select(
                QuoteModel.author_id,
                func.count().label("quote_count"),
            )
            .where(QuoteModel.group_id == group_id)
            .group_by(QuoteModel.author_id)
            .order_by(func.count().desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(row.author_id, row.quote_count) for row in result.all()]

    # ---- 更新 ----

    async def update_quote(
        self,
        quote_id: str,
        content: Optional[str] = None,
        image_content_uuid: Optional[str] = None,
        total_show_time: Optional[int] = None,
    ) -> bool:
        """更新语录信息（仅更新非 ``None`` 字段）。

        :param quote_id: 语录 ID。
        :type quote_id: str
        :param content: 新的文本内容。
        :type content: Optional[str]
        :param image_content_uuid: 新的图片 UUID。
        :type image_content_uuid: Optional[str]
        :param total_show_time: 新的展示次数。
        :type total_show_time: Optional[int]
        :returns: 是否成功更新（找到记录）。
        :rtype: bool
        """
        values: Dict[str, Any] = {}
        if content is not None:
            values["content"] = content
        if image_content_uuid is not None:
            values["image_content_uuid"] = image_content_uuid
        if total_show_time is not None:
            values["total_show_time"] = total_show_time
        if not values:
            return True
        stmt = (
            update(QuoteModel)
            .where(QuoteModel.quote_id == quote_id)
            .values(**values)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    async def update_quote_migration_state(
        self,
        quote_id: str,
        *,
        group_id: Optional[str] = None,
        total_show_time: Optional[int] = None,
    ) -> bool:
        """更新群迁移过程中需要调整的语录状态。

        :param quote_id: 语录 ID。
        :type quote_id: str
        :param group_id: 目标群组 ID。
        :type group_id: Optional[str]
        :param total_show_time: 更新后的展示次数。
        :type total_show_time: Optional[int]
        :returns: 是否成功更新（找到记录）。
        :rtype: bool
        """
        values: Dict[str, Any] = {}
        if group_id is not None:
            values["group_id"] = group_id
        if total_show_time is not None:
            values["total_show_time"] = total_show_time
        if not values:
            return True

        stmt = update(QuoteModel).where(QuoteModel.quote_id == quote_id).values(**values)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    async def increment_show_time(self, quote_id: str) -> bool:
        """增加语录展示次数 +1。

        :param quote_id: 语录 ID。
        :type quote_id: str
        :returns: 是否成功更新（找到记录）。
        :rtype: bool
        """
        stmt = (
            update(QuoteModel)
            .where(QuoteModel.quote_id == quote_id)
            .values(total_show_time=QuoteModel.total_show_time + 1)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    # ---- 删除 ----

    async def delete_quote(self, quote_id: str) -> bool:
        """删除语录。

        :param quote_id: 语录 ID。
        :type quote_id: str
        :returns: 是否成功删除。
        :rtype: bool
        """
        return await self.delete_by_id(quote_id)

    async def delete_quotes_by_group(self, group_id: str) -> bool:
        """删除群组的所有语录。

        :param group_id: 群组 ID。
        :type group_id: str
        :returns: 始终返回 ``True``。
        :rtype: bool
        """
        stmt = delete(QuoteModel).where(QuoteModel.group_id == group_id)
        await self._session.execute(stmt)
        await self._session.flush()
        return True
