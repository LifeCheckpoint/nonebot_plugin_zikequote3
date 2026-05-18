"""
StatisticsService —— 统计与搜索领域服务。

合并原模块：
- ``group_ranking_service.py``     群组排行榜
- ``personal_listing_service.py``  个人语录列表
- ``quote_searching_service.py``   语录搜索

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

from nonebot import logger
import re
from typing import Any, Dict, Optional, Sequence, Tuple

from ..database.models.quotes import Quote
from ..database.repositories.group_member_repository import GroupMemberRepository
from ..database.repositories.quote_repository import QuoteRepository
from ..exceptions import ResourceNotFoundError, ValidationException

class StatisticsService:
    """
    统计与搜索领域服务，通过构造函数注入 Repository 依赖。

    职责：

    1. 群组语录排行榜
    2. 个人语录列表
    3. 语录搜索
    4. 群组统计信息

    :param quote_repo: 语录仓储实例
    :type quote_repo: QuoteRepository
    :param group_member_repo: 群成员仓储实例
    :type group_member_repo: GroupMemberRepository
    """

    def __init__(
        self,
        quote_repo: QuoteRepository,
        group_member_repo: GroupMemberRepository,
    ) -> None:
        self._quote_repo = quote_repo
        self._group_member_repo = group_member_repo

    # ------------------------------------------------------------------ #
    #  群组排行榜
    # ------------------------------------------------------------------ #

    async def get_group_ranking(
        self,
        group_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        获取群组语录排行榜。

        返回按语录数降序排列的作者列表，每项包含
        ``author_id`` 和 ``quote_count``。

        :param group_id: 群组 ID
        :type group_id: str
        :param limit: 返回条数上限，默认 10
        :type limit: int
        :returns: 排行榜列表，每项为 ``{"author_id": str, "quote_count": int}``
        :rtype: list[dict[str, Any]]
        :raises ResourceNotFoundError: 群组无语录数据
        """
        ranking = await self._quote_repo.get_author_ranking(group_id, limit=limit)
        if not ranking:
            raise ResourceNotFoundError(f"群组 {group_id} 暂无语录排行数据")

        return [
            {"author_id": author_id, "quote_count": count}
            for author_id, count in ranking
        ]

    async def get_group_statistics(self, group_id: str) -> Dict[str, Any]:
        """
        获取群组语录统计信息。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 包含 ``total_quotes``, ``unique_authors``,
            ``total_shows``, ``avg_shows`` 的字典
        :rtype: Dict[str, Any]
        """
        return await self._quote_repo.get_quote_statistics_by_group(group_id)

    # ------------------------------------------------------------------ #
    #  个人语录列表
    # ------------------------------------------------------------------ #

    async def get_personal_quotes(
        self,
        qq_id: str,
        group_id: str,
        *,
        from_index: Optional[int] = None,
        to_index: Optional[int] = None,
        max_count: int = 50,
    ) -> Tuple[Sequence[Quote], int, int, int]:
        """
        获取个人语录列表（分页）。

        :param qq_id: 用户 QQ 号
        :type qq_id: str
        :param group_id: 群组 ID
        :type group_id: str
        :param from_index: 起始索引（1-based，包含），``None`` 表示自动
        :type from_index: Optional[int]
        :param to_index: 结束索引（1-based，包含），``None`` 表示自动
        :type to_index: Optional[int]
        :param max_count: 单次最大返回条数
        :type max_count: int
        :returns: ``(quotes, total_count, real_from, real_to)`` —
            quotes: 语录列表,
            total_count: 该用户在该群的语录总数,
            real_from: 实际起始索引（0-based）,
            real_to: 实际结束索引（0-based）
        :rtype: Tuple[Sequence[Quote], int, int, int]
        :raises ResourceNotFoundError: 用户在该群无语录
        """
        all_quotes = await self._quote_repo.get_quotes_by_group_and_author(
            group_id, qq_id
        )
        total_count = len(all_quotes)

        if total_count == 0:
            raise ResourceNotFoundError(
                f"用户 {qq_id} 在群组 {group_id} 中没有语录"
            )

        # 计算分页范围
        if from_index is None and to_index is None:
            # 默认：取最后 max_count 条
            if total_count > max_count:
                real_from = total_count - max_count
                real_to = total_count - 1
            else:
                real_from = 0
                real_to = total_count - 1
        elif from_index is not None and to_index is None:
            real_from = max(0, from_index - 1)
            real_to = min(total_count - 1, real_from + max_count - 1)
        elif from_index is not None and to_index is not None:
            real_from = max(0, from_index - 1)
            real_to = min(total_count - 1, to_index - 1)
        else:
            raise ValidationException("语录范围参数不正确：不能只指定 to_index")

        sliced = all_quotes[real_from : real_to + 1]
        return sliced, total_count, real_from, real_to

    # ------------------------------------------------------------------ #
    #  语录搜索
    # ------------------------------------------------------------------ #

    async def search_quotes(
        self,
        keyword: str,
        group_id: str,
        *,
        author_id: Optional[str] = None,
        include_image_only: bool = True,
        max_results: Optional[int] = None,
        use_regex: bool = False,
    ) -> Tuple[Sequence[Quote], int]:
        """
        搜索语录。

        :param keyword: 搜索关键词或正则表达式
        :type keyword: str
        :param group_id: 群组 ID
        :type group_id: str
        :param author_id: 可选，按作者过滤
        :type author_id: Optional[str]
        :param include_image_only: 是否包含纯图片语录，默认 ``True``
        :type include_image_only: bool
        :param max_results: 最大返回条数，``None`` 表示不限
        :type max_results: Optional[int]
        :param use_regex: 是否使用正则表达式匹配
        :type use_regex: bool
        :returns: ``(quotes, total_found)`` —
            quotes: 匹配的语录列表（可能被 max_results 截断）,
            total_found: 匹配总数（截断前）
        :rtype: Tuple[Sequence[Quote], int]
        """
        if use_regex:
            all_quotes = await self._quote_repo.get_quotes_by_group(group_id)
            quotes = [q for q in all_quotes if q.content]
            try:
                pattern = re.compile(keyword)
            except re.error as e:
                raise ValidationException(f"无效的正则表达式: {e}") from e
            quotes = [q for q in quotes if q.content and pattern.search(q.content)]
            if author_id:
                quotes = [q for q in quotes if q.author_id == author_id]
        else:
            quotes = list(
                await self._quote_repo.search_quotes_ilike(
                    keyword=keyword, group_id=group_id, author_id=author_id
                )
            )

        if not include_image_only:
            quotes = [q for q in quotes if not q.image_content_uuid]

        total_found = len(quotes)

        if max_results is not None:
            quotes = quotes[:max_results]

        return quotes, total_found

    # ------------------------------------------------------------------ #
    #  作者语录计数
    # ------------------------------------------------------------------ #

    async def count_author_quotes_in_group(
        self, group_id: str, author_id: str
    ) -> int:
        """
        统计指定作者在群组中的语录数量。

        :param group_id: 群组 ID
        :type group_id: str
        :param author_id: 作者 QQ 号
        :type author_id: str
        :returns: 语录数量
        :rtype: int
        """
        return await self._quote_repo.count_quotes_by_group_and_author(
            group_id, author_id
        )

    async def get_group_member_quote_counts(
        self, group_id: str
    ) -> list[dict[str, Any]]:
        """
        获取群组所有成员的语录计数。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 列表，每项为 ``{"qq_id": str, "quote_count": int}``，
            按语录数降序排列，排除计数为 0 的成员
        :rtype: list[dict[str, Any]]
        """
        members = await self._group_member_repo.get_members_by_group(group_id)
        counts_by_author = await self._quote_repo.count_quotes_group_by_author(group_id)
        result: list[dict[str, Any]] = []

        for member in members:
            qq_id = member.qq_id
            count = counts_by_author.get(qq_id, 0)
            if count > 0:
                result.append({"qq_id": qq_id, "quote_count": count})

        result.sort(key=lambda x: x["quote_count"], reverse=True)
        return result
