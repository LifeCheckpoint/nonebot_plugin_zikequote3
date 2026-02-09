"""
ReviewRepository —— 评论数据仓储，对应原 ``ReviewDAO``。

覆盖原 DAO 的所有公开方法，返回 Pydantic DTO。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from sqlalchemy import delete, func, select, update

from ..models.reviews import Review, ReviewCreate
from ..sa.models.review import ReviewModel
from .base import BaseRepository


class ReviewRepository(BaseRepository[ReviewModel, ReviewCreate, Review]):
    """评论 Repository。"""

    model_class = ReviewModel

    # ---- 创建 ----

    async def create_review(
        self, review_id: str, author_id: str, quote_id: str, content: str
    ) -> Review:
        """创建新评论并返回 DTO。"""
        dto = ReviewCreate(
            review_id=review_id, author_id=author_id,
            quote_id=quote_id, content=content,
        )
        return await self.create(dto)

    async def batch_create_reviews(self, reviews: list[dict[str, str]]) -> bool:
        """批量创建评论。每个 dict 包含 review_id / author_id / quote_id / content。"""
        if not reviews:
            return True
        instances = [
            ReviewModel.from_create_dto(
                ReviewCreate(
                    review_id=r["review_id"],
                    author_id=r["author_id"],
                    quote_id=r["quote_id"],
                    content=r["content"],
                )
            )
            for r in reviews
        ]
        self._session.add_all(instances)
        await self._session.flush()
        return True

    # ---- 查询 ----

    async def get_review_by_id(self, review_id: str) -> Optional[Review]:
        """按评论 ID 查询。"""
        return await self.get_by_id(review_id)

    async def get_reviews_by_quote(
        self, quote_id: str, *, limit: Optional[int] = None, offset: int = 0
    ) -> Sequence[Review]:
        """获取语录的所有评论（按时间升序）。"""
        stmt = (
            select(ReviewModel)
            .where(ReviewModel.quote_id == quote_id)
            .order_by(ReviewModel.time_stamp.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_reviews_by_author(
        self, author_id: str, *, limit: Optional[int] = None, offset: int = 0
    ) -> Sequence[Review]:
        """获取作者的所有评论（按时间升序）。"""
        stmt = (
            select(ReviewModel)
            .where(ReviewModel.author_id == author_id)
            .order_by(ReviewModel.time_stamp.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def get_recent_reviews(
        self, *, limit: Optional[int] = None, offset: int = 0
    ) -> Sequence[Review]:
        """获取最近的评论（按时间降序）。"""
        stmt = select(ReviewModel).order_by(ReviewModel.time_stamp.desc())
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def search_reviews_by_content(
        self, keyword: str, *, limit: Optional[int] = None, offset: int = 0
    ) -> Sequence[Review]:
        """按内容关键词搜索评论（LIKE 匹配，按时间降序）。"""
        pattern = f"%{keyword}%"
        stmt = (
            select(ReviewModel)
            .where(ReviewModel.content.like(pattern))
            .order_by(ReviewModel.time_stamp.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [row.to_dto() for row in result.scalars().all()]

    async def count_reviews_by_quote(self, quote_id: str) -> int:
        """统计语录的评论数量。"""
        stmt = (
            select(func.count())
            .select_from(ReviewModel)
            .where(ReviewModel.quote_id == quote_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_reviews_by_author(self, author_id: str) -> int:
        """统计作者的评论数量。"""
        stmt = (
            select(func.count())
            .select_from(ReviewModel)
            .where(ReviewModel.author_id == author_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_review_statistics(self) -> Dict[str, Any]:
        """获取评论统计信息。"""
        stmt = select(
            func.count().label("total_reviews"),
            func.count(func.distinct(ReviewModel.author_id)).label("unique_reviewers"),
            func.count(func.distinct(ReviewModel.quote_id)).label("reviewed_quotes"),
        ).select_from(ReviewModel)
        result = await self._session.execute(stmt)
        row = result.one()
        return {
            "total_reviews": row.total_reviews,
            "unique_reviewers": row.unique_reviewers,
            "reviewed_quotes": row.reviewed_quotes,
        }

    # ---- 更新 ----

    async def update_review(self, review_id: str, content: str) -> bool:
        """更新评论内容。"""
        stmt = (
            update(ReviewModel)
            .where(ReviewModel.review_id == review_id)
            .values(content=content)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    # ---- 删除 ----

    async def delete_review(self, review_id: str) -> bool:
        """删除评论。"""
        return await self.delete_by_id(review_id)

    async def delete_reviews_by_quote(self, quote_id: str) -> bool:
        """删除指定语录的所有评论。"""
        stmt = delete(ReviewModel).where(ReviewModel.quote_id == quote_id)
        await self._session.execute(stmt)
        await self._session.flush()
        return True

    async def delete_reviews_by_author(self, author_id: str) -> bool:
        """删除指定作者的所有评论。"""
        stmt = delete(ReviewModel).where(ReviewModel.author_id == author_id)
        await self._session.execute(stmt)
        await self._session.flush()
        return True
