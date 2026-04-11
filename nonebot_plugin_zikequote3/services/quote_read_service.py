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

from nonebot import logger
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

class QuoteReadService:
    """
    语录读取领域服务，通过构造函数注入 Repository 依赖。

    :param quote_repo: 语录仓储实例
    :type quote_repo: QuoteRepository
    :param review_repo: 评论仓储实例
    :type review_repo: ReviewRepository
    :param image_repo: 图片仓储实例
    :type image_repo: ImageRepository
    :param user_service: 用户服务实例
    :type user_service: UserService
    """

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
        """
        按 ID 获取语录，不存在返回 ``None``。

        :param quote_id: 语录 ID
        :type quote_id: str
        :returns: 语录对象，不存在返回 ``None``
        :rtype: Optional[Quote]
        """
        return await self._quote_repo.get_quote_by_id(quote_id)

    async def get_quote_or_raise(self, quote_id: str) -> Quote:
        """
        按 ID 获取语录，不存在则抛出异常。

        :param quote_id: 语录 ID
        :type quote_id: str
        :returns: 语录对象
        :rtype: Quote
        :raises QuoteNotFoundError: 语录不存在
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
        """
        按群获取语录列表。

        :param group_id: 群组 ID
        :type group_id: str
        :param limit: 最大返回条数，``None`` 表示不限
        :type limit: Optional[int]
        :param offset: 偏移量
        :type offset: int
        :returns: 语录列表
        :rtype: Sequence[Quote]
        """
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
        """
        按作者获取语录列表。

        :param author_id: 作者 QQ 号
        :type author_id: str
        :param limit: 最大返回条数，``None`` 表示不限
        :type limit: Optional[int]
        :param offset: 偏移量
        :type offset: int
        :returns: 语录列表
        :rtype: Sequence[Quote]
        """
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
        """
        按群 + 作者获取语录列表。

        :param group_id: 群组 ID
        :type group_id: str
        :param author_id: 作者 QQ 号
        :type author_id: str
        :param limit: 最大返回条数，``None`` 表示不限
        :type limit: Optional[int]
        :param offset: 偏移量
        :type offset: int
        :returns: 语录列表
        :rtype: Sequence[Quote]
        """
        return await self._quote_repo.get_quotes_by_group_and_author(
            group_id, author_id, limit=limit, offset=offset,
        )

    async def get_recent_quotes_by_group(
        self,
        group_id: str,
        *,
        limit: Optional[int] = None,
    ) -> Sequence[Quote]:
        """
        获取当前群最近语录（按创建时间倒序）。

        :param group_id: 群组 ID
        :type group_id: str
        :param limit: 最大返回条数，``None`` 表示不限
        :type limit: Optional[int]
        :returns: 最近语录列表
        :rtype: Sequence[Quote]
        """
        return await self._quote_repo.get_recent_quotes(
            group_id=group_id,
            limit=limit,
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
        """
        按关键词搜索语录（LIKE 匹配）。

        :param keyword: 搜索关键词
        :type keyword: str
        :param group_id: 群组 ID，``None`` 表示不限群组
        :type group_id: Optional[str]
        :param limit: 最大返回条数
        :type limit: Optional[int]
        :param offset: 偏移量
        :type offset: int
        :returns: 匹配的语录列表
        :rtype: Sequence[Quote]
        """
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
        """
        按群 + 作者搜索语录。

        :param group_id: 群组 ID
        :type group_id: str
        :param author_id: 作者 QQ 号
        :type author_id: str
        :param limit: 最大返回条数
        :type limit: Optional[int]
        :returns: 语录列表
        :rtype: Sequence[Quote]
        """
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

        :param quote_id: 语录 ID
        :type quote_id: str
        :returns: ``(quote, reviews)`` 元组，语录不存在时返回 ``None``
        :rtype: Optional[Tuple[Quote, Sequence[Review]]]
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

        :param quote_id: 语录 ID
        :type quote_id: str
        :raises QuoteNotFoundError: 语录不存在
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
        获取群内随机语录。

        可选按作者或关键词过滤。如果同时指定 author_id 和 keyword，
        先按作者过滤，再在结果中按关键词筛选。

        :param group_id: 群号
        :type group_id: str
        :param author_id: 可选作者过滤
        :type author_id: Optional[str]
        :param keyword: 可选关键词过滤
        :type keyword: Optional[str]
        :returns: 随机语录，池为空时返回 ``None``
        :rtype: Optional[Quote]
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

        :param group_id: 群号
        :type group_id: str
        :param author_id: 可选作者过滤
        :type author_id: Optional[str]
        :param keyword: 可选关键词过滤
        :type keyword: Optional[str]
        :param algorithm: 算法名称，``"ifw"`` 或 ``"logifw"``
        :type algorithm: str
        :param lambda_: 正则化幂变换系数
        :type lambda_: float
        :param a_: 冷启动平滑参数
        :type a_: float
        :param log_a_: 对数平滑参数（仅 logifw）
        :type log_a_: float
        :returns: 选中的语录，池为空时返回 ``None``
        :rtype: Optional[Quote]
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
            logger.warning("未知算法 '{}'，回退到均匀随机", algorithm)
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

        公式：``w_i0 = (1 / (c_i - min(c) + a))^λ``，然后归一化。

        :param quotes: 候选语录列表
        :type quotes: list[Quote]
        :param lambda_: 正则化幂变换系数
        :type lambda_: float
        :param a_: 冷启动平滑参数
        :type a_: float
        :returns: 语录 ID 到归一化权重的映射
        :rtype: dict[str, float]
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

        公式：``w_i0 = (1 / (log(c_i - min(c) + log_a) + a))^λ``，然后归一化。

        :param quotes: 候选语录列表
        :type quotes: list[Quote]
        :param lambda_: 正则化幂变换系数
        :type lambda_: float
        :param a_: 冷启动平滑参数
        :type a_: float
        :param log_a_: 对数平滑参数
        :type log_a_: float
        :returns: 语录 ID 到归一化权重的映射
        :rtype: dict[str, float]
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

        :param image_uuid: 图片 UUID
        :type image_uuid: str
        :returns: 图片 DTO，不存在返回 ``None``
        :rtype: Optional[Image]
        """
        return await self._image_repo.get_by_uuid(image_uuid)

    async def get_image_metadata_or_raise(self, image_uuid: str) -> Image:
        """
        获取图片元数据，不存在则抛出异常。

        :param image_uuid: 图片 UUID
        :type image_uuid: str
        :returns: 图片 DTO
        :rtype: Image
        :raises ImageNotFoundError: 图片不存在
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

        :param quote_id: 语录 ID
        :type quote_id: str
        :param group_id: 群组 ID
        :type group_id: str
        :returns: 作者显示名称
        :rtype: str
        :raises QuoteNotFoundError: 语录不存在
        """
        quote = await self.get_quote_or_raise(quote_id)
        return await self._user_service.get_display_name(
            quote.author_id, group_id,
        )
