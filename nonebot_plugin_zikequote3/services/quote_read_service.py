"""
QuoteReadService —— 语录读取领域服务。

合并原模块：
- ``basic_quote_service.py``       基础语录查询
- ``rand_quote_service.py``        随机语录 & 搜索
- ``rand_quote_algo_function.py``  加权随机算法（IFW / LogIFW）
- ``quote_image_service.py``       图片元数据查询

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

import logging
import math
import random
from typing import Optional, Sequence, Tuple

from ..database.models.images import Image
from ..database.models.quotes import Quote
from ..database.models.reviews import Review
from ..database.repositories.image_repository import ImageRepository
from ..database.repositories.quote_repository import QuoteRepository
from ..database.repositories.review_repository import ReviewRepository
from ..exceptions import (
    ImageNotFoundError,
    QuoteNotFoundError,
)
from .user_service import UserService

logger = logging.getLogger(__name__)


class QuoteReadService:
    """语录读取领域服务，通过构造函数注入 Repository 依赖。"""

    def __init__(
        self,
        quote_repo: QuoteRepository,
        review_repo: ReviewRepository,
        image_repo: ImageRepository,
        user_service: UserService,
    ) -> None:
        self._quote_repo = quote_repo
        self._review_repo = review_repo
        self._image_repo = image_repo
        self._user_service = user_service

    # ------------------------------------------------------------------ #
    #  单条查询
    # ------------------------------------------------------------------ #

    async def get_quote(self, quote_id: str) -> Optional[Quote]:
        """按 ID 获取语录，不存在返回 ``None``。"""
        return await self._quote_repo.get_quote_by_id(quote_id)

    async def get_quote_or_raise(self, quote_id: str) -> Quote:
        """
        按 ID 获取语录，不存在则抛出异常。

        Raises:
            QuoteNotFoundError: 语录不存在。
        """
        quote = await self._quote_repo.get_quote_by_id(quote_id)
        if quote is None:
            raise QuoteNotFoundError(f"语录不存在: {quote_id}")
        return quote

    # ------------------------------------------------------------------ #
    #  列表查询
    # ------------------------------------------------------------------ #

    async def get_quotes_by_group(
        self,
        group_id: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """按群获取语录列表。"""
        return await self._quote_repo.get_quotes_by_group(
            group_id, limit=limit, offset=offset,
        )

    async def get_quotes_by_author(
        self,
        author_id: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """按作者获取语录列表。"""
        return await self._quote_repo.get_quotes_by_author(
            author_id, limit=limit, offset=offset,
        )

    async def get_quotes_by_group_and_author(
        self,
        group_id: str,
        author_id: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """按群 + 作者获取语录列表。"""
        return await self._quote_repo.get_quotes_by_group_and_author(
            group_id, author_id, limit=limit, offset=offset,
        )

    # ------------------------------------------------------------------ #
    #  搜索
    # ------------------------------------------------------------------ #

    async def search_quotes(
        self,
        keyword: str,
        group_id: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Sequence[Quote]:
        """按关键词搜索语录（LIKE 匹配）。"""
        return await self._quote_repo.search_quotes_by_content(
            keyword, group_id, limit=limit, offset=offset,
        )

    async def search_quotes_by_author(
        self,
        group_id: str,
        author_id: str,
        *,
        limit: Optional[int] = None,
    ) -> Sequence[Quote]:
        """按群 + 作者搜索语录。"""
        return await self._quote_repo.get_quotes_by_group_and_author(
            group_id, author_id, limit=limit,
        )

    # ------------------------------------------------------------------ #
    #  语录 + 评论
    # ------------------------------------------------------------------ #

    async def get_quote_with_reviews(
        self, quote_id: str,
    ) -> Optional[Tuple[Quote, Sequence[Review]]]:
        """
        获取语录及其所有评论。

        Returns:
            ``(quote, reviews)`` 元组，语录不存在时返回 ``None``。
        """
        quote = await self._quote_repo.get_quote_by_id(quote_id)
        if quote is None:
            return None
        reviews = await self._review_repo.get_reviews_by_quote(quote_id)
        return quote, reviews

    # ------------------------------------------------------------------ #
    #  展示次数
    # ------------------------------------------------------------------ #

    async def increment_show_time(self, quote_id: str) -> None:
        """
        增加语录展示次数 +1。

        Raises:
            QuoteNotFoundError: 语录不存在。
        """
        updated = await self._quote_repo.increment_show_time(quote_id)
        if not updated:
            raise QuoteNotFoundError(f"语录不存在: {quote_id}")

    # ------------------------------------------------------------------ #
    #  随机语录（含加权算法）
    # ------------------------------------------------------------------ #

    async def get_random_quote(
        self,
        group_id: str,
        *,
        author_id: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Optional[Quote]:
        """
        获取群内随机语录（数据库级 ``ORDER BY RANDOM()``）。

        可选按作者或关键词过滤。如果同时指定 author_id 和 keyword，
        先按作者过滤，再在结果中按关键词筛选。
        """
        if author_id is not None:
            pool = list(
                await self._quote_repo.get_quotes_by_group_and_author(
                    group_id, author_id,
                )
            )
        else:
            pool = list(
                await self._quote_repo.get_quotes_by_group(group_id)
            )

        if keyword:
            pool = [q for q in pool if q.content and keyword in q.content]

        if not pool:
            return None

        return random.choice(pool)

    async def get_random_quote_weighted(
        self,
        group_id: str,
        *,
        author_id: Optional[str] = None,
        keyword: Optional[str] = None,
        algorithm: str = "ifw",
        lambda_: float = 1.0,
        a_: float = 1.0,
        log_a_: float = 2.0,
    ) -> Optional[Quote]:
        """
        使用加权随机算法获取语录。

        Args:
            group_id: 群号。
            author_id: 可选作者过滤。
            keyword: 可选关键词过滤。
            algorithm: 算法名称，``"ifw"`` 或 ``"logifw"``。
            lambda_: 正则化幂变换系数。
            a_: 冷启动平滑参数。
            log_a_: 对数平滑参数（仅 logifw）。

        Returns:
            选中的语录，池为空时返回 ``None``。
        """
        # 构建候选池
        if author_id is not None:
            pool = list(
                await self._quote_repo.get_quotes_by_group_and_author(
                    group_id, author_id,
                )
            )
        else:
            pool = list(
                await self._quote_repo.get_quotes_by_group(group_id)
            )

        if keyword:
            pool = [q for q in pool if q.content and keyword in q.content]

        if not pool:
            return None
        if len(pool) == 1:
            return pool[0]

        # 计算权重
        algo = algorithm.lower()
        if algo == "ifw":
            weights = self._calc_ifw_weights(pool, lambda_=lambda_, a_=a_)
        elif algo == "logifw":
            weights = self._calc_logifw_weights(
                pool, lambda_=lambda_, a_=a_, log_a_=log_a_,
            )
        else:
            # 未知算法回退到均匀随机
            logger.warning("未知算法 '%s'，回退到均匀随机", algorithm)
            return random.choice(pool)

        ids = list(weights.keys())
        w = list(weights.values())
        chosen_id = random.choices(ids, weights=w, k=1)[0]
        return next((q for q in pool if q.quote_id == chosen_id), None)

    # ------------------------------------------------------------------ #
    #  加权随机算法（原 rand_quote_algo_function.py）
    # ------------------------------------------------------------------ #

    @staticmethod
    def _calc_ifw_weights(
        quotes: list[Quote],
        *,
        lambda_: float = 1.0,
        a_: float = 1.0,
    ) -> dict[str, float]:
        """
        逆频率加权（Inverse Frequency Weighting）。

        ``w_i0 = (1 / (c_i - min(c) + a))^λ``，然后归一化。
        """
        min_c = min(q.total_show_time for q in quotes)
        wi0 = {
            q.quote_id: (1.0 / (q.total_show_time - min_c + a_)) ** lambda_
            for q in quotes
        }
        total = sum(wi0.values())
        return {qid: w / total for qid, w in wi0.items()}

    @staticmethod
    def _calc_logifw_weights(
        quotes: list[Quote],
        *,
        lambda_: float = 1.0,
        a_: float = 1.0,
        log_a_: float = 2.0,
    ) -> dict[str, float]:
        """
        对数逆频率加权（Log Inverse Frequency Weighting）。

        ``w_i0 = (1 / (log(c_i - min(c) + log_a) + a))^λ``，然后归一化。
        """
        min_c = min(q.total_show_time for q in quotes)
        wi0 = {
            q.quote_id: (
                1.0 / (math.log(q.total_show_time - min_c + log_a_) + a_)
            ) ** lambda_
            for q in quotes
        }
        total = sum(wi0.values())
        return {qid: w / total for qid, w in wi0.items()}

    # ------------------------------------------------------------------ #
    #  图片元数据查询（原 quote_image_service.py 元数据部分）
    # ------------------------------------------------------------------ #

    async def get_image_metadata(self, image_uuid: str) -> Optional[Image]:
        """
        获取图片元数据。

        Returns:
            图片 DTO，不存在返回 ``None``。
        """
        return await self._image_repo.get_by_uuid(image_uuid)

    async def get_image_metadata_or_raise(self, image_uuid: str) -> Image:
        """
        获取图片元数据，不存在则抛出异常。

        Raises:
            ImageNotFoundError: 图片不存在。
        """
        image = await self._image_repo.get_by_uuid(image_uuid)
        if image is None:
            raise ImageNotFoundError(f"图片不存在: {image_uuid}")
        return image

    # ------------------------------------------------------------------ #
    #  作者显示名称辅助
    # ------------------------------------------------------------------ #

    async def get_quote_author_display_name(
        self, quote_id: str, group_id: str,
    ) -> str:
        """
        获取语录作者的显示名称。

        Raises:
            QuoteNotFoundError: 语录不存在。
        """
        quote = await self.get_quote_or_raise(quote_id)
        return await self._user_service.get_display_name(
            quote.author_id, group_id,
        )
