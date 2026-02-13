"""
ReviewService —— 评论领域服务。

迁移自 ``review_management/review_service.py``。

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

from nonebot import logger
import random
from typing import Optional, Sequence

from ..database.models.reviews import Review
from ..database.repositories.quote_repository import QuoteRepository
from ..database.repositories.review_repository import ReviewRepository
from ..exceptions import QuoteNotFoundError, ResourceNotFoundError

AUTHOR_AI = "-1"

def _generate_review_id() -> str:
    """生成 11 位随机数字评论 ID。"""
    return str(random.randint(10**10, 10**11 - 1))

class ReviewService:
    """
    评论领域服务，通过构造函数注入 Repository 依赖。

    职责：

    1. 添加评论（校验语录存在性）
    2. 查询评论列表
    3. 删除评论
    4. 统计评论数

    :param review_repo: 评论仓储实例
    :type review_repo: ReviewRepository
    :param quote_repo: 语录仓储实例
    :type quote_repo: QuoteRepository
    """

    def __init__(
        self,
        review_repo: ReviewRepository,
        quote_repo: QuoteRepository,
    ) -> None:
        self._review_repo = review_repo
        self._quote_repo = quote_repo

    # ------------------------------------------------------------------ #
    #  添加评论
    # ------------------------------------------------------------------ #

    async def add_review(
        self,
        quote_id: str,
        author_id: str,
        content: str,
    ) -> str:
        """
        为语录添加评论。

        :param quote_id: 语录 ID
        :type quote_id: str
        :param author_id: 评论者 QQ 号（``"-1"`` 表示 AI 生成）
        :type author_id: str
        :param content: 评论内容
        :type content: str
        :returns: 新创建的评论 ID
        :rtype: str
        :raises QuoteNotFoundError: 语录不存在
        """
        # 验证语录存在
        quote = await self._quote_repo.get_quote_by_id(quote_id)
        if quote is None:
            raise QuoteNotFoundError(f"语录 {quote_id} 不存在")

        review_id = _generate_review_id()
        await self._review_repo.create_review(
            review_id=review_id,
            author_id=author_id,
            quote_id=quote_id,
            content=content.strip(),
        )
        logger.info(
            "评论已添加: review_id=%s, quote_id=%s, author=%s",
            review_id, quote_id, author_id,
        )
        return review_id

    # ------------------------------------------------------------------ #
    #  查询评论
    # ------------------------------------------------------------------ #

    async def get_reviews_by_quote(self, quote_id: str) -> Sequence[Review]:
        """
        获取语录的所有评论（按时间升序）。

        :param quote_id: 语录 ID
        :type quote_id: str
        :returns: 评论列表
        :rtype: Sequence[Review]
        """
        return await self._review_repo.get_reviews_by_quote(quote_id)

    async def get_review_by_id(self, review_id: str) -> Optional[Review]:
        """
        按评论 ID 查询。

        :param review_id: 评论 ID
        :type review_id: str
        :returns: 评论对象，不存在返回 ``None``
        :rtype: Optional[Review]
        """
        return await self._review_repo.get_review_by_id(review_id)

    # ------------------------------------------------------------------ #
    #  删除评论
    # ------------------------------------------------------------------ #

    async def delete_review(self, review_id: str) -> None:
        """
        删除评论。

        :param review_id: 评论 ID
        :type review_id: str
        :raises ResourceNotFoundError: 评论不存在
        """
        existing = await self._review_repo.get_review_by_id(review_id)
        if existing is None:
            raise ResourceNotFoundError(f"评论不存在: {review_id}")

        deleted = await self._review_repo.delete_review(review_id)
        if not deleted:
            raise ResourceNotFoundError(f"删除评论失败: {review_id}")

        logger.info("评论已删除: review_id={}", review_id)

    # ------------------------------------------------------------------ #
    #  统计
    # ------------------------------------------------------------------ #

    async def count_reviews(self, quote_id: str) -> int:
        """
        统计语录的评论数。

        :param quote_id: 语录 ID
        :type quote_id: str
        :returns: 评论数量
        :rtype: int
        """
        return await self._review_repo.count_reviews_by_quote(quote_id)
