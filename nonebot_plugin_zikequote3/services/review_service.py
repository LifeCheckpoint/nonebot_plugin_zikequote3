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
from ..exceptions import (
    PermissionDeniedError,
    QuoteNotFoundError,
    ResourceNotFoundError,
    ValidationException,
)
from .user_service import UserService

AUTHOR_AI = "-1"
AUTHOR_AI_NICKNAME = "AI"

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
        user_service: UserService,
    ) -> None:
        self._review_repo = review_repo
        self._quote_repo = quote_repo
        self._user_service = user_service

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

        await self._ensure_review_author_exists(author_id)

        review_id = _generate_review_id()
        content_clean = content.strip()
        if not content_clean:
            raise ValidationException("评论内容不能为空")
        await self._review_repo.create_review(
            review_id=review_id,
            author_id=author_id,
            quote_id=quote_id,
            content=content_clean,
        )
        logger.info(
            "评论已添加: review_id={}, quote_id={}, author={}",
            review_id, quote_id, author_id,
        )
        return review_id

    async def _ensure_review_author_exists(self, author_id: str) -> None:
        """确保评论作者用户记录存在；AI 作者额外补稳定昵称。"""
        await self._user_service.get_or_create_user(author_id)
        if author_id == AUTHOR_AI:
            await self._user_service.sync_nickname(author_id, AUTHOR_AI_NICKNAME)

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

    async def delete_review(
        self,
        review_id: str,
        *,
        operator_id: str,
        allow_delete_others: bool = False,
    ) -> None:
        """
        删除评论。

        :param review_id: 评论 ID
        :type review_id: str
        :param operator_id: 执行删除的操作者 ID
        :type operator_id: str
        :param allow_delete_others: 是否允许删除他人评论
        :type allow_delete_others: bool
        :raises ResourceNotFoundError: 评论不存在
        :raises PermissionDeniedError: 操作者无权删除该评论
        """
        existing = await self._review_repo.get_review_by_id(review_id)
        if existing is None:
            raise ResourceNotFoundError(f"评论不存在: {review_id}")

        self._ensure_delete_permission(
            review_id=review_id,
            owner_id=existing.author_id,
            operator_id=operator_id,
            allow_delete_others=allow_delete_others,
        )

        deleted = await self._review_repo.delete_review(review_id)
        if not deleted:
            raise ResourceNotFoundError(f"删除评论失败: {review_id}")

        logger.info("评论已删除: review_id={}", review_id)

    def _ensure_delete_permission(
        self,
        *,
        review_id: str,
        owner_id: str,
        operator_id: str,
        allow_delete_others: bool,
    ) -> None:
        """校验删除评论时的操作者归属约束。"""
        if not operator_id:
            raise PermissionDeniedError(
                f"删除评论缺少操作者上下文（review_id={review_id}）"
            )
        if owner_id == operator_id or allow_delete_others:
            return

        logger.warning(
            "越权删除评论被拒绝: review_id={}, owner={}, operator={}, allow_delete_others={}",
            review_id,
            owner_id,
            operator_id,
            allow_delete_others,
        )
        raise PermissionDeniedError(f"仅可删除自己的评论（review_id={review_id}）")

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
