"""
统一查询解析器模块。

将用户的各种输入形式（@提及、QQ号、昵称、关键词、语录ID）
统一解析为 :class:`ResolvedQuery` 结果，供各命令 handler 使用。

各命令通过选择不同的 :class:`ResolveStrategy` 预配置常量来定制解析行为，
无需在 handler 中重复编写解析逻辑。
"""

from __future__ import annotations

from nonebot import logger
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ...services.user_service import UserService

# ------------------------------------------------------------------ #
#  枚举定义
# ------------------------------------------------------------------ #

class QueryIntent(Enum):
    """
    查询解析后识别出的意图类型。

    每种意图对应一种用户输入的语义解释方式，
    命令 handler 根据意图决定后续业务逻辑。
    """

    USER_BY_AT = auto()
    """通过 @提及 确定的用户，无歧义。"""

    USER_BY_QQ = auto()
    """纯数字输入且确认为 QQ 号。"""

    USER_BY_NAME = auto()
    """通过昵称搜索匹配到的用户。"""

    QUOTE_BY_ID = auto()
    """纯数字输入且确认为语录 ID。"""

    KEYWORD = auto()
    """作为语录内容关键词。"""

    SELF = auto()
    """未提供输入，默认为发送者自身。"""

    AMBIGUOUS = auto()
    """存在歧义，需要进一步消解。"""

class NumericDisambiguation(Enum):
    """
    纯数字输入的歧义消解策略。

    当用户输入纯数字时，不同命令对其语义解释不同：
    有的优先视为 QQ 号，有的优先视为语录 ID，有的视为关键词。
    """

    PREFER_QUOTE_ID = auto()
    """优先解释为语录 ID。"""

    PREFER_QQ = auto()
    """优先解释为 QQ 号。"""

    PREFER_KEYWORD = auto()
    """优先解释为关键词。"""

    AS_BOTH = auto()
    """同时作为用户和关键词，合并候选池。"""

# ------------------------------------------------------------------ #
#  策略配置
# ------------------------------------------------------------------ #

class ResolveStrategy(BaseModel, frozen=True):
    """
    查询解析策略配置。

    每个命令通过实例化不同的 ``ResolveStrategy`` 来定制解析行为。
    使用 ``frozen=True`` 确保策略实例不可变，可安全作为模块级常量共享。

    :param support_at: 是否支持 @提及
    :type support_at: bool
    :param support_qq: 是否支持 QQ 号查询
    :type support_qq: bool
    :param support_nickname: 是否支持昵称查询
    :type support_nickname: bool
    :param support_keyword: 是否支持语录内容关键词
    :type support_keyword: bool
    :param support_quote_id: 是否支持语录 ID 查询
    :type support_quote_id: bool
    :param numeric_disambiguation: 纯数字输入的歧义消解策略
    :type numeric_disambiguation: NumericDisambiguation
    :param nickname_exact: 昵称是否精确匹配（``False`` 为片段匹配）
    :type nickname_exact: bool
    :param merge_candidates: 是否合并昵称和关键词候选（语录卡模式）
    :type merge_candidates: bool
    :param fallback_to_self: 无输入时是否回退到发送者自身
    :type fallback_to_self: bool
    :param fallback_to_keyword: 昵称搜索无结果时是否回退为关键词
    :type fallback_to_keyword: bool
    """

    # ---- 支持的查询维度 ----
    support_at: bool = True
    support_qq: bool = True
    support_nickname: bool = True
    support_keyword: bool = True
    support_quote_id: bool = False

    # ---- 歧义消解 ----
    numeric_disambiguation: NumericDisambiguation = (
        NumericDisambiguation.PREFER_QUOTE_ID
    )

    # ---- 昵称搜索行为 ----
    nickname_exact: bool = False

    # ---- 多维度合并行为 ----
    merge_candidates: bool = False

    # ---- 回退行为 ----
    fallback_to_self: bool = True
    fallback_to_keyword: bool = False

# ------------------------------------------------------------------ #
#  解析结果
# ------------------------------------------------------------------ #

class ResolvedQuery(BaseModel):
    """
    统一查询解析结果。

    :param intent: 识别出的主要意图
    :type intent: QueryIntent
    :param user_candidates: 匹配到的用户 QQ 号列表
    :type user_candidates: list[str]
    :param keyword: 语录内容关键词
    :type keyword: Optional[str]
    :param quote_id: 语录 ID
    :type quote_id: Optional[str]
    :param raw_input: 原始输入文本
    :type raw_input: str
    :param ambiguous_alternatives: 歧义时的备选意图列表
    :type ambiguous_alternatives: list[QueryIntent]
    """

    intent: QueryIntent
    user_candidates: list[str] = Field(default_factory=list)
    keyword: Optional[str] = None
    quote_id: Optional[str] = None
    raw_input: str = ""
    ambiguous_alternatives: list[QueryIntent] = Field(default_factory=list)

    @property
    def has_user(self) -> bool:
        """是否解析出了目标用户。"""
        return len(self.user_candidates) > 0

    @property
    def single_user(self) -> Optional[str]:
        """唯一匹配的用户 QQ 号，多个匹配时返回 ``None``。"""
        if len(self.user_candidates) == 1:
            return self.user_candidates[0]
        return None

    @property
    def has_keyword(self) -> bool:
        """是否包含关键词。"""
        return self.keyword is not None and self.keyword.strip() != ""

# ------------------------------------------------------------------ #
#  预配置策略常量
# ------------------------------------------------------------------ #

STRATEGY_USER_LOOKUP = ResolveStrategy(
    support_at=True,
    support_qq=True,
    support_nickname=True,
    support_keyword=False,
    support_quote_id=False,
    numeric_disambiguation=NumericDisambiguation.PREFER_QQ,
    nickname_exact=False,
    merge_candidates=False,
    fallback_to_self=True,
    fallback_to_keyword=False,
)
"""``/语录列表``、``/用户信息`` 使用的策略：定位唯一用户。"""

STRATEGY_SEARCH_QUOTE = ResolveStrategy(
    support_at=True,
    support_qq=True,
    support_nickname=True,
    support_keyword=True,
    support_quote_id=False,
    numeric_disambiguation=NumericDisambiguation.PREFER_KEYWORD,
    nickname_exact=False,
    merge_candidates=False,
    fallback_to_self=False,
    fallback_to_keyword=True,
)
"""``/搜索语录`` 使用的策略：按关键词搜索语录内容，可选按用户筛选。"""

STRATEGY_RANDOM_QUOTE = ResolveStrategy(
    support_at=True,
    support_qq=True,
    support_nickname=True,
    support_keyword=True,
    support_quote_id=True,
    numeric_disambiguation=NumericDisambiguation.PREFER_QUOTE_ID,
    nickname_exact=False,
    merge_candidates=True,
    fallback_to_self=False,
    fallback_to_keyword=True,
)
"""``/语录卡``、``/随机语录``、``/随机图片语录`` 使用的策略：合并候选池。"""

STRATEGY_RANKING = ResolveStrategy(
    support_at=False,
    support_qq=False,
    support_nickname=False,
    support_keyword=False,
    support_quote_id=False,
    numeric_disambiguation=NumericDisambiguation.PREFER_KEYWORD,
    merge_candidates=False,
    fallback_to_self=False,
    fallback_to_keyword=True,
)
"""``/排行榜`` 使用的策略：参数仅为数量，不涉及用户解析。"""

# ------------------------------------------------------------------ #
#  核心解析器
# ------------------------------------------------------------------ #

class QueryResolver:
    """
    统一查询解析器。

    将用户的各种输入形式（@提及、QQ号、昵称、关键词）
    统一解析为 :class:`ResolvedQuery` 结果。

    :param user_svc: 用户服务实例，用于昵称搜索
    :type user_svc: UserService
    """

    def __init__(self, user_svc: UserService) -> None:
        self._user_svc = user_svc

    async def resolve(
        self,
        *,
        strategy: ResolveStrategy,
        group_id: str,
        sender_id: str,
        at_target: Optional[str] = None,
        raw_text: str = "",
    ) -> ResolvedQuery:
        """
        统一查询解析入口。

        按以下优先级依次尝试解析：

        1. @提及（最高优先级，无歧义）
        2. 空输入判断（回退到发送者或返回空关键词）
        3. 纯数字歧义消解（根据策略决定语义）
        4. 文本输入（昵称搜索 vs 关键词）

        :param strategy: 解析策略配置
        :type strategy: ResolveStrategy
        :param group_id: 当前群组 ID
        :type group_id: str
        :param sender_id: 消息发送者 QQ 号
        :type sender_id: str
        :param at_target: @提及的目标 QQ 号（从消息段提取），``None`` 表示无 @
        :type at_target: Optional[str]
        :param raw_text: 用户输入的纯文本部分（去除命令前缀和 @ 段后的文本）
        :type raw_text: str
        :returns: 解析结果
        :rtype: ResolvedQuery
        """
        # Step 1: @提及（无歧义，最高优先级）
        if at_target is not None and strategy.support_at:
            logger.debug("解析为 @提及: at_target=%s", at_target)
            return ResolvedQuery(
                intent=QueryIntent.USER_BY_AT,
                user_candidates=[at_target],
                raw_input=raw_text,
            )

        # Step 2: 空输入判断
        text = raw_text.strip()
        if not text:
            if strategy.fallback_to_self:
                logger.debug("空输入，回退到发送者: sender_id=%s", sender_id)
                return ResolvedQuery(
                    intent=QueryIntent.SELF,
                    user_candidates=[sender_id],
                    raw_input=raw_text,
                )
            logger.debug("空输入，返回空关键词")
            return ResolvedQuery(
                intent=QueryIntent.KEYWORD,
                keyword="",
                raw_input=raw_text,
            )

        is_numeric = text.isdigit()

        # Step 3: 纯数字输入的歧义消解
        if is_numeric:
            return self._resolve_numeric(text, strategy, raw_text)

        # Step 4: 文本输入（昵称 vs 关键词）
        return await self._resolve_text(text, strategy, group_id, raw_text)

    def _resolve_numeric(
        self,
        text: str,
        strategy: ResolveStrategy,
        raw_text: str,
    ) -> ResolvedQuery:
        """
        纯数字输入的歧义消解。

        根据策略的 ``numeric_disambiguation`` 配置决定数字的语义解释。

        :param text: 去除空白后的纯数字文本
        :type text: str
        :param strategy: 解析策略配置
        :type strategy: ResolveStrategy
        :param raw_text: 原始输入文本
        :type raw_text: str
        :returns: 解析结果
        :rtype: ResolvedQuery
        """
        disambiguation = strategy.numeric_disambiguation

        if disambiguation == NumericDisambiguation.PREFER_QUOTE_ID:
            return self._resolve_numeric_prefer_quote_id(
                text, strategy, raw_text,
            )

        if disambiguation == NumericDisambiguation.PREFER_QQ:
            return self._resolve_numeric_prefer_qq(text, strategy, raw_text)

        if disambiguation == NumericDisambiguation.PREFER_KEYWORD:
            logger.debug("纯数字 PREFER_KEYWORD: 解析为关键词=%s", text)
            return ResolvedQuery(
                intent=QueryIntent.KEYWORD,
                keyword=text,
                raw_input=raw_text,
            )

        # AS_BOTH: 同时填充 user_candidates 和 keyword
        logger.debug("纯数字 AS_BOTH: 同时作为QQ号和关键词=%s", text)
        candidates = [text] if strategy.support_qq else []
        return ResolvedQuery(
            intent=QueryIntent.KEYWORD,
            user_candidates=candidates,
            keyword=text,
            raw_input=raw_text,
        )

    def _resolve_numeric_prefer_quote_id(
        self,
        text: str,
        strategy: ResolveStrategy,
        raw_text: str,
    ) -> ResolvedQuery:
        """
        ``PREFER_QUOTE_ID`` 策略下的纯数字解析。

        :param text: 纯数字文本
        :type text: str
        :param strategy: 解析策略配置
        :type strategy: ResolveStrategy
        :param raw_text: 原始输入文本
        :type raw_text: str
        :returns: 解析结果
        :rtype: ResolvedQuery
        """
        if strategy.support_quote_id:
            logger.debug("纯数字 PREFER_QUOTE_ID: 解析为语录ID=%s", text)
            return ResolvedQuery(
                intent=QueryIntent.QUOTE_BY_ID,
                quote_id=text,
                raw_input=raw_text,
            )
        if strategy.support_qq:
            logger.debug(
                "纯数字 PREFER_QUOTE_ID 回退: 解析为QQ号=%s", text,
            )
            return ResolvedQuery(
                intent=QueryIntent.USER_BY_QQ,
                user_candidates=[text],
                raw_input=raw_text,
            )
        return ResolvedQuery(
            intent=QueryIntent.KEYWORD,
            keyword=text,
            raw_input=raw_text,
        )

    def _resolve_numeric_prefer_qq(
        self,
        text: str,
        strategy: ResolveStrategy,
        raw_text: str,
    ) -> ResolvedQuery:
        """
        ``PREFER_QQ`` 策略下的纯数字解析。

        :param text: 纯数字文本
        :type text: str
        :param strategy: 解析策略配置
        :type strategy: ResolveStrategy
        :param raw_text: 原始输入文本
        :type raw_text: str
        :returns: 解析结果
        :rtype: ResolvedQuery
        """
        if strategy.support_qq:
            logger.debug("纯数字 PREFER_QQ: 解析为QQ号=%s", text)
            return ResolvedQuery(
                intent=QueryIntent.USER_BY_QQ,
                user_candidates=[text],
                raw_input=raw_text,
            )
        if strategy.support_quote_id:
            logger.debug(
                "纯数字 PREFER_QQ 回退: 解析为语录ID=%s", text,
            )
            return ResolvedQuery(
                intent=QueryIntent.QUOTE_BY_ID,
                quote_id=text,
                raw_input=raw_text,
            )
        return ResolvedQuery(
            intent=QueryIntent.KEYWORD,
            keyword=text,
            raw_input=raw_text,
        )

    async def _resolve_text(
        self,
        text: str,
        strategy: ResolveStrategy,
        group_id: str,
        raw_text: str,
    ) -> ResolvedQuery:
        """
        非数字文本输入的解析。

        根据策略配置决定是进行昵称搜索、关键词匹配还是两者合并。

        :param text: 去除空白后的文本
        :type text: str
        :param strategy: 解析策略配置
        :type strategy: ResolveStrategy
        :param group_id: 当前群组 ID
        :type group_id: str
        :param raw_text: 原始输入文本
        :type raw_text: str
        :returns: 解析结果
        :rtype: ResolvedQuery
        """
        # merge_candidates 模式：同时搜索用户和作为关键词
        if strategy.merge_candidates:
            users: list[str] = []
            if strategy.support_nickname:
                users = await self._user_svc.search_users_by_name(
                    text, group_id, exact=strategy.nickname_exact,
                )
            logger.debug(
                "merge_candidates 模式: text=%s, users=%s", text, users,
            )
            return ResolvedQuery(
                intent=QueryIntent.KEYWORD,
                user_candidates=users,
                keyword=text,
                raw_input=raw_text,
            )

        # 优先级短路模式
        if strategy.support_nickname:
            users = await self._user_svc.search_users_by_name(
                text, group_id, exact=strategy.nickname_exact,
            )
            if users:
                logger.debug(
                    "昵称匹配成功: text=%s, users=%s", text, users,
                )
                return ResolvedQuery(
                    intent=QueryIntent.USER_BY_NAME,
                    user_candidates=users,
                    raw_input=raw_text,
                )

        # 昵称无匹配，尝试回退为关键词
        if strategy.support_keyword or strategy.fallback_to_keyword:
            logger.debug("回退为关键词: text=%s", text)
            return ResolvedQuery(
                intent=QueryIntent.KEYWORD,
                keyword=text,
                raw_input=raw_text,
            )

        # 无法解析
        logger.debug("无法解析文本输入: text=%s", text)
        return ResolvedQuery(
            intent=QueryIntent.KEYWORD,
            keyword=text,
            raw_input=raw_text,
        )

# ------------------------------------------------------------------ #
#  辅助提取函数
# ------------------------------------------------------------------ #

def extract_at_qq(at_match: Any) -> Optional[str]:
    """
    从 Alconna 的 ``Match[At]`` 中提取 QQ 号。

    :param at_match: Alconna 匹配结果对象
    :type at_match: Match[At]
    :returns: 提取到的 QQ 号字符串，无法提取时返回 ``None``
    :rtype: Optional[str]
    """
    if not hasattr(at_match, "available") or not at_match.available:
        return None
    result = getattr(at_match, "result", None)
    if result is None:
        return None
    origin = getattr(result, "origin", None)
    if origin is None:
        return None
    data = getattr(origin, "data", None)
    if data is None:
        return None
    return data.get("qq")

def extract_text(*matches: Any) -> str:
    """
    从多个 Alconna ``Match[str]`` 中提取并拼接文本。

    用于兼容现有的 ``qq`` + ``nickname`` 分离参数模式，
    以及新的 ``input`` 统一参数模式。

    :param matches: 一个或多个 Alconna 匹配结果对象
    :type matches: Match[str]
    :returns: 拼接后的文本，各部分以空格分隔
    :rtype: str
    """
    parts: list[str] = []
    for m in matches:
        if not hasattr(m, "available") or not m.available:
            continue
        result = getattr(m, "result", None)
        if result is None:
            continue
        text = result.strip() if isinstance(result, str) else str(result)
        if text:
            parts.append(text)
    return " ".join(parts)

__all__ = [
    "QueryIntent",
    "NumericDisambiguation",
    "ResolveStrategy",
    "ResolvedQuery",
    "QueryResolver",
    "STRATEGY_USER_LOOKUP",
    "STRATEGY_SEARCH_QUOTE",
    "STRATEGY_RANDOM_QUOTE",
    "STRATEGY_RANKING",
    "extract_at_qq",
    "extract_text",
]
