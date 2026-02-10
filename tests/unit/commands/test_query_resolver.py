"""
QueryResolver 统一查询解析器单元测试。

覆盖场景：
- @提及解析
- 空输入 + fallback_to_self=True/False
- 纯数字 + 三种消解策略（PREFER_QQ / PREFER_QUOTE_ID / PREFER_KEYWORD / AS_BOTH）
- 文本输入 + 昵称匹配成功/失败
- merge_candidates 模式
- 各预配置策略常量的正确性
- 边界情况（4位数字、特殊字符等）
- ResolvedQuery 属性测试
- 辅助函数 extract_at_qq / extract_text
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from nonebot_plugin_zikequote3.command.parse_helper.query_resolver import (
    NumericDisambiguation,
    QueryIntent,
    QueryResolver,
    ResolvedQuery,
    ResolveStrategy,
    STRATEGY_RANDOM_QUOTE,
    STRATEGY_RANKING,
    STRATEGY_SEARCH_QUOTE,
    STRATEGY_USER_LOOKUP,
    extract_at_qq,
    extract_text,
)


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture
def mock_user_svc() -> MagicMock:
    """创建 mock UserService，默认 search_users_by_name 返回空列表。"""
    svc = MagicMock()
    svc.search_users_by_name = AsyncMock(return_value=[])
    return svc


@pytest.fixture
def resolver(mock_user_svc: MagicMock) -> QueryResolver:
    """创建 QueryResolver 实例，注入 mock UserService。"""
    return QueryResolver(user_svc=mock_user_svc)


# ------------------------------------------------------------------ #
#  预配置策略常量正确性测试
# ------------------------------------------------------------------ #


class TestStrategyConstants:
    """预配置策略常量的字段值验证。"""

    def test_strategy_user_lookup(self) -> None:
        """STRATEGY_USER_LOOKUP 应配置为用户查找模式。"""
        s = STRATEGY_USER_LOOKUP
        assert s.support_at is True
        assert s.support_qq is True
        assert s.support_nickname is True
        assert s.support_keyword is False
        assert s.support_quote_id is False
        assert s.numeric_disambiguation == NumericDisambiguation.PREFER_QQ
        assert s.nickname_exact is False
        assert s.merge_candidates is False
        assert s.fallback_to_self is True
        assert s.fallback_to_keyword is False

    def test_strategy_search_quote(self) -> None:
        """STRATEGY_SEARCH_QUOTE 应配置为语录搜索模式。"""
        s = STRATEGY_SEARCH_QUOTE
        assert s.support_at is True
        assert s.support_qq is True
        assert s.support_nickname is True
        assert s.support_keyword is True
        assert s.support_quote_id is False
        assert s.numeric_disambiguation == NumericDisambiguation.PREFER_KEYWORD
        assert s.nickname_exact is False
        assert s.merge_candidates is False
        assert s.fallback_to_self is False
        assert s.fallback_to_keyword is True

    def test_strategy_random_quote(self) -> None:
        """STRATEGY_RANDOM_QUOTE 应配置为随机语录合并候选池模式。"""
        s = STRATEGY_RANDOM_QUOTE
        assert s.support_at is True
        assert s.support_qq is True
        assert s.support_nickname is True
        assert s.support_keyword is True
        assert s.support_quote_id is True
        assert s.numeric_disambiguation == NumericDisambiguation.PREFER_QUOTE_ID
        assert s.nickname_exact is False
        assert s.merge_candidates is True
        assert s.fallback_to_self is False
        assert s.fallback_to_keyword is True

    def test_strategy_ranking(self) -> None:
        """STRATEGY_RANKING 应配置为排行榜模式（不支持任何查询维度）。"""
        s = STRATEGY_RANKING
        assert s.support_at is False
        assert s.support_qq is False
        assert s.support_nickname is False
        assert s.support_keyword is False
        assert s.support_quote_id is False
        assert s.numeric_disambiguation == NumericDisambiguation.PREFER_KEYWORD
        assert s.merge_candidates is False
        assert s.fallback_to_self is False
        assert s.fallback_to_keyword is True

    def test_strategy_frozen(self) -> None:
        """策略常量应为不可变对象。"""
        with pytest.raises(Exception):
            STRATEGY_USER_LOOKUP.support_at = False  # type: ignore[misc]


# ------------------------------------------------------------------ #
#  ResolvedQuery 属性测试
# ------------------------------------------------------------------ #


class TestResolvedQueryProperties:
    """ResolvedQuery 的计算属性验证。"""

    def test_has_user_true(self) -> None:
        """有用户候选时 has_user 应为 True。"""
        rq = ResolvedQuery(
            intent=QueryIntent.USER_BY_AT, user_candidates=["12345"],
        )
        assert rq.has_user is True

    def test_has_user_false(self) -> None:
        """无用户候选时 has_user 应为 False。"""
        rq = ResolvedQuery(intent=QueryIntent.KEYWORD)
        assert rq.has_user is False

    def test_single_user_one(self) -> None:
        """仅一个用户候选时 single_user 应返回该用户。"""
        rq = ResolvedQuery(
            intent=QueryIntent.USER_BY_QQ, user_candidates=["99999"],
        )
        assert rq.single_user == "99999"

    def test_single_user_multiple(self) -> None:
        """多个用户候选时 single_user 应返回 None。"""
        rq = ResolvedQuery(
            intent=QueryIntent.USER_BY_NAME,
            user_candidates=["111", "222"],
        )
        assert rq.single_user is None

    def test_single_user_empty(self) -> None:
        """无用户候选时 single_user 应返回 None。"""
        rq = ResolvedQuery(intent=QueryIntent.KEYWORD)
        assert rq.single_user is None

    def test_has_keyword_true(self) -> None:
        """有非空关键词时 has_keyword 应为 True。"""
        rq = ResolvedQuery(intent=QueryIntent.KEYWORD, keyword="测试")
        assert rq.has_keyword is True

    def test_has_keyword_false_none(self) -> None:
        """keyword 为 None 时 has_keyword 应为 False。"""
        rq = ResolvedQuery(intent=QueryIntent.KEYWORD, keyword=None)
        assert rq.has_keyword is False

    def test_has_keyword_false_empty(self) -> None:
        """keyword 为空字符串时 has_keyword 应为 False。"""
        rq = ResolvedQuery(intent=QueryIntent.KEYWORD, keyword="")
        assert rq.has_keyword is False

    def test_has_keyword_false_whitespace(self) -> None:
        """keyword 为纯空白时 has_keyword 应为 False。"""
        rq = ResolvedQuery(intent=QueryIntent.KEYWORD, keyword="   ")
        assert rq.has_keyword is False


# ------------------------------------------------------------------ #
#  @提及解析测试
# ------------------------------------------------------------------ #


class TestAtMention:
    """@提及解析场景。"""

    @pytest.mark.asyncio
    async def test_at_target_returns_user_by_at(
        self, resolver: QueryResolver,
    ) -> None:
        """有 at_target 且策略支持 @提及时，应返回 USER_BY_AT。"""
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            at_target="12345",
            raw_text="",
        )
        assert result.intent == QueryIntent.USER_BY_AT
        assert result.user_candidates == ["12345"]

    @pytest.mark.asyncio
    async def test_at_target_with_raw_text(
        self, resolver: QueryResolver,
    ) -> None:
        """@提及优先级高于 raw_text，raw_text 保留在 raw_input 中。"""
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            at_target="12345",
            raw_text="一些文本",
        )
        assert result.intent == QueryIntent.USER_BY_AT
        assert result.user_candidates == ["12345"]
        assert result.raw_input == "一些文本"

    @pytest.mark.asyncio
    async def test_at_target_ignored_when_not_supported(
        self, resolver: QueryResolver,
    ) -> None:
        """策略不支持 @提及时，at_target 应被忽略。"""
        result = await resolver.resolve(
            strategy=STRATEGY_RANKING,
            group_id="G1",
            sender_id="sender1",
            at_target="12345",
            raw_text="",
        )
        # STRATEGY_RANKING 的 support_at=False, fallback_to_self=False
        assert result.intent == QueryIntent.KEYWORD
        assert result.user_candidates == []


# ------------------------------------------------------------------ #
#  空输入测试
# ------------------------------------------------------------------ #


class TestEmptyInput:
    """空输入场景。"""

    @pytest.mark.asyncio
    async def test_empty_with_fallback_to_self(
        self, resolver: QueryResolver,
    ) -> None:
        """空输入 + fallback_to_self=True 时，应返回 SELF + 发送者 QQ。"""
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            raw_text="",
        )
        assert result.intent == QueryIntent.SELF
        assert result.user_candidates == ["sender1"]

    @pytest.mark.asyncio
    async def test_empty_without_fallback(
        self, resolver: QueryResolver,
    ) -> None:
        """空输入 + fallback_to_self=False 时，应返回 KEYWORD + 空关键词。"""
        result = await resolver.resolve(
            strategy=STRATEGY_SEARCH_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.keyword == ""
        assert result.user_candidates == []

    @pytest.mark.asyncio
    async def test_whitespace_only_treated_as_empty(
        self, resolver: QueryResolver,
    ) -> None:
        """纯空白输入应视为空输入。"""
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            raw_text="   ",
        )
        assert result.intent == QueryIntent.SELF
        assert result.user_candidates == ["sender1"]

    @pytest.mark.asyncio
    async def test_none_at_target_with_empty_text(
        self, resolver: QueryResolver,
    ) -> None:
        """at_target=None + 空文本 + fallback_to_self=True → SELF。"""
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            at_target=None,
            raw_text="",
        )
        assert result.intent == QueryIntent.SELF


# ------------------------------------------------------------------ #
#  纯数字输入 + 歧义消解测试
# ------------------------------------------------------------------ #


class TestNumericDisambiguation:
    """纯数字输入的歧义消解场景。"""

    @pytest.mark.asyncio
    async def test_prefer_qq(self, resolver: QueryResolver) -> None:
        """PREFER_QQ 策略下，纯数字应解析为 QQ 号。"""
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            raw_text="12345678",
        )
        assert result.intent == QueryIntent.USER_BY_QQ
        assert result.user_candidates == ["12345678"]

    @pytest.mark.asyncio
    async def test_prefer_quote_id(self, resolver: QueryResolver) -> None:
        """PREFER_QUOTE_ID 策略下，纯数字应解析为语录 ID。"""
        result = await resolver.resolve(
            strategy=STRATEGY_RANDOM_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="42",
        )
        assert result.intent == QueryIntent.QUOTE_BY_ID
        assert result.quote_id == "42"

    @pytest.mark.asyncio
    async def test_prefer_keyword(self, resolver: QueryResolver) -> None:
        """PREFER_KEYWORD 策略下，纯数字应解析为关键词。"""
        result = await resolver.resolve(
            strategy=STRATEGY_SEARCH_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="12345",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.keyword == "12345"

    @pytest.mark.asyncio
    async def test_prefer_quote_id_fallback_to_qq(
        self, resolver: QueryResolver,
    ) -> None:
        """PREFER_QUOTE_ID 但 support_quote_id=False 时，应回退到 QQ 号。"""
        strategy = ResolveStrategy(
            support_quote_id=False,
            support_qq=True,
            numeric_disambiguation=NumericDisambiguation.PREFER_QUOTE_ID,
        )
        result = await resolver.resolve(
            strategy=strategy,
            group_id="G1",
            sender_id="sender1",
            raw_text="12345678",
        )
        assert result.intent == QueryIntent.USER_BY_QQ
        assert result.user_candidates == ["12345678"]

    @pytest.mark.asyncio
    async def test_prefer_quote_id_fallback_to_keyword(
        self, resolver: QueryResolver,
    ) -> None:
        """PREFER_QUOTE_ID 但 support_quote_id=False 且 support_qq=False 时，应回退到关键词。"""
        strategy = ResolveStrategy(
            support_quote_id=False,
            support_qq=False,
            numeric_disambiguation=NumericDisambiguation.PREFER_QUOTE_ID,
        )
        result = await resolver.resolve(
            strategy=strategy,
            group_id="G1",
            sender_id="sender1",
            raw_text="12345678",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.keyword == "12345678"

    @pytest.mark.asyncio
    async def test_prefer_qq_fallback_to_quote_id(
        self, resolver: QueryResolver,
    ) -> None:
        """PREFER_QQ 但 support_qq=False 时，应回退到语录 ID。"""
        strategy = ResolveStrategy(
            support_qq=False,
            support_quote_id=True,
            numeric_disambiguation=NumericDisambiguation.PREFER_QQ,
        )
        result = await resolver.resolve(
            strategy=strategy,
            group_id="G1",
            sender_id="sender1",
            raw_text="42",
        )
        assert result.intent == QueryIntent.QUOTE_BY_ID
        assert result.quote_id == "42"

    @pytest.mark.asyncio
    async def test_prefer_qq_fallback_to_keyword(
        self, resolver: QueryResolver,
    ) -> None:
        """PREFER_QQ 但 support_qq=False 且 support_quote_id=False 时，应回退到关键词。"""
        strategy = ResolveStrategy(
            support_qq=False,
            support_quote_id=False,
            numeric_disambiguation=NumericDisambiguation.PREFER_QQ,
        )
        result = await resolver.resolve(
            strategy=strategy,
            group_id="G1",
            sender_id="sender1",
            raw_text="12345",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.keyword == "12345"

    @pytest.mark.asyncio
    async def test_as_both(self, resolver: QueryResolver) -> None:
        """AS_BOTH 策略下，应同时填充 user_candidates 和 keyword。"""
        strategy = ResolveStrategy(
            support_qq=True,
            numeric_disambiguation=NumericDisambiguation.AS_BOTH,
        )
        result = await resolver.resolve(
            strategy=strategy,
            group_id="G1",
            sender_id="sender1",
            raw_text="12345678",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.user_candidates == ["12345678"]
        assert result.keyword == "12345678"

    @pytest.mark.asyncio
    async def test_as_both_no_qq_support(
        self, resolver: QueryResolver,
    ) -> None:
        """AS_BOTH 但 support_qq=False 时，user_candidates 应为空。"""
        strategy = ResolveStrategy(
            support_qq=False,
            numeric_disambiguation=NumericDisambiguation.AS_BOTH,
        )
        result = await resolver.resolve(
            strategy=strategy,
            group_id="G1",
            sender_id="sender1",
            raw_text="12345678",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.user_candidates == []
        assert result.keyword == "12345678"


# ------------------------------------------------------------------ #
#  文本输入 + 昵称匹配测试
# ------------------------------------------------------------------ #


class TestTextInput:
    """非数字文本输入的解析场景。"""

    @pytest.mark.asyncio
    async def test_nickname_match_single(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """昵称搜索匹配到唯一用户时，应返回 USER_BY_NAME。"""
        mock_user_svc.search_users_by_name.return_value = ["99999"]
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            raw_text="张三",
        )
        assert result.intent == QueryIntent.USER_BY_NAME
        assert result.user_candidates == ["99999"]
        assert result.single_user == "99999"
        mock_user_svc.search_users_by_name.assert_awaited_once_with(
            "张三", "G1", exact=False,
        )

    @pytest.mark.asyncio
    async def test_nickname_match_multiple(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """昵称搜索匹配到多个用户时，应返回 USER_BY_NAME + 多候选。"""
        mock_user_svc.search_users_by_name.return_value = ["111", "222"]
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            raw_text="张",
        )
        assert result.intent == QueryIntent.USER_BY_NAME
        assert result.user_candidates == ["111", "222"]
        assert result.single_user is None

    @pytest.mark.asyncio
    async def test_nickname_no_match_fallback_keyword(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """昵称搜索无匹配 + fallback_to_keyword=True 时，应回退为 KEYWORD。"""
        mock_user_svc.search_users_by_name.return_value = []
        result = await resolver.resolve(
            strategy=STRATEGY_SEARCH_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="不存在的名字",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.keyword == "不存在的名字"

    @pytest.mark.asyncio
    async def test_nickname_no_match_no_fallback(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """昵称搜索无匹配 + fallback_to_keyword=False 时，仍返回 KEYWORD。"""
        mock_user_svc.search_users_by_name.return_value = []
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            raw_text="不存在的名字",
        )
        # STRATEGY_USER_LOOKUP: support_keyword=False, fallback_to_keyword=False
        # 但最终兜底仍返回 KEYWORD
        assert result.intent == QueryIntent.KEYWORD
        assert result.keyword == "不存在的名字"

    @pytest.mark.asyncio
    async def test_nickname_disabled(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """support_nickname=False 时，不应调用昵称搜索。"""
        strategy = ResolveStrategy(
            support_nickname=False,
            support_keyword=True,
            fallback_to_self=False,
        )
        result = await resolver.resolve(
            strategy=strategy,
            group_id="G1",
            sender_id="sender1",
            raw_text="张三",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.keyword == "张三"
        mock_user_svc.search_users_by_name.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_nickname_exact_mode(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """nickname_exact=True 时，应传递 exact=True 给搜索方法。"""
        mock_user_svc.search_users_by_name.return_value = ["88888"]
        strategy = ResolveStrategy(
            support_nickname=True,
            nickname_exact=True,
            fallback_to_self=False,
        )
        result = await resolver.resolve(
            strategy=strategy,
            group_id="G1",
            sender_id="sender1",
            raw_text="张三",
        )
        assert result.intent == QueryIntent.USER_BY_NAME
        mock_user_svc.search_users_by_name.assert_awaited_once_with(
            "张三", "G1", exact=True,
        )


# ------------------------------------------------------------------ #
#  merge_candidates 模式测试
# ------------------------------------------------------------------ #


class TestMergeCandidates:
    """merge_candidates=True（语录卡模式）的解析场景。"""

    @pytest.mark.asyncio
    async def test_merge_with_nickname_match(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """merge_candidates 模式下，昵称匹配成功时应同时返回 user_candidates 和 keyword。"""
        mock_user_svc.search_users_by_name.return_value = ["12345"]
        result = await resolver.resolve(
            strategy=STRATEGY_RANDOM_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="张三",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.user_candidates == ["12345"]
        assert result.keyword == "张三"
        assert result.has_user is True
        assert result.has_keyword is True

    @pytest.mark.asyncio
    async def test_merge_without_nickname_match(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """merge_candidates 模式下，昵称无匹配时仅返回 keyword。"""
        mock_user_svc.search_users_by_name.return_value = []
        result = await resolver.resolve(
            strategy=STRATEGY_RANDOM_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="好笑",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.user_candidates == []
        assert result.keyword == "好笑"
        assert result.has_user is False
        assert result.has_keyword is True

    @pytest.mark.asyncio
    async def test_merge_with_multiple_users(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """merge_candidates 模式下，多个昵称匹配应全部返回。"""
        mock_user_svc.search_users_by_name.return_value = ["111", "222", "333"]
        result = await resolver.resolve(
            strategy=STRATEGY_RANDOM_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="张",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.user_candidates == ["111", "222", "333"]
        assert result.keyword == "张"

    @pytest.mark.asyncio
    async def test_merge_nickname_disabled(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """merge_candidates=True 但 support_nickname=False 时，不搜索昵称。"""
        strategy = ResolveStrategy(
            support_nickname=False,
            merge_candidates=True,
            fallback_to_self=False,
        )
        result = await resolver.resolve(
            strategy=strategy,
            group_id="G1",
            sender_id="sender1",
            raw_text="张三",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.user_candidates == []
        assert result.keyword == "张三"
        mock_user_svc.search_users_by_name.assert_not_awaited()


# ------------------------------------------------------------------ #
#  边界情况测试
# ------------------------------------------------------------------ #


class TestEdgeCases:
    """边界情况与特殊输入。"""

    @pytest.mark.asyncio
    async def test_four_digit_number_is_numeric(
        self, resolver: QueryResolver,
    ) -> None:
        """4位数字应被识别为纯数字并走数字消解流程。"""
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            raw_text="1234",
        )
        # STRATEGY_USER_LOOKUP: PREFER_QQ
        assert result.intent == QueryIntent.USER_BY_QQ
        assert result.user_candidates == ["1234"]

    @pytest.mark.asyncio
    async def test_single_digit(
        self, resolver: QueryResolver,
    ) -> None:
        """单个数字应被识别为纯数字。"""
        result = await resolver.resolve(
            strategy=STRATEGY_RANDOM_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="5",
        )
        # STRATEGY_RANDOM_QUOTE: PREFER_QUOTE_ID
        assert result.intent == QueryIntent.QUOTE_BY_ID
        assert result.quote_id == "5"

    @pytest.mark.asyncio
    async def test_mixed_digits_and_text(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """数字+文本混合输入不应被视为纯数字。"""
        mock_user_svc.search_users_by_name.return_value = []
        result = await resolver.resolve(
            strategy=STRATEGY_SEARCH_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="abc123",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.keyword == "abc123"

    @pytest.mark.asyncio
    async def test_special_characters(
        self, resolver: QueryResolver, mock_user_svc: MagicMock,
    ) -> None:
        """特殊字符输入应作为文本处理。"""
        mock_user_svc.search_users_by_name.return_value = []
        result = await resolver.resolve(
            strategy=STRATEGY_SEARCH_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="@#$%^&",
        )
        assert result.intent == QueryIntent.KEYWORD
        assert result.keyword == "@#$%^&"

    @pytest.mark.asyncio
    async def test_leading_trailing_whitespace_stripped(
        self, resolver: QueryResolver,
    ) -> None:
        """输入前后空白应被去除后再解析。"""
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            raw_text="  12345678  ",
        )
        assert result.intent == QueryIntent.USER_BY_QQ
        assert result.user_candidates == ["12345678"]

    @pytest.mark.asyncio
    async def test_raw_input_preserved(
        self, resolver: QueryResolver,
    ) -> None:
        """raw_input 应保留原始输入（含空白）。"""
        result = await resolver.resolve(
            strategy=STRATEGY_USER_LOOKUP,
            group_id="G1",
            sender_id="sender1",
            raw_text="  12345678  ",
        )
        assert result.raw_input == "  12345678  "

    @pytest.mark.asyncio
    async def test_zero_is_numeric(
        self, resolver: QueryResolver,
    ) -> None:
        """'0' 应被识别为纯数字。"""
        result = await resolver.resolve(
            strategy=STRATEGY_RANDOM_QUOTE,
            group_id="G1",
            sender_id="sender1",
            raw_text="0",
        )
        assert result.intent == QueryIntent.QUOTE_BY_ID
        assert result.quote_id == "0"


# ------------------------------------------------------------------ #
#  辅助函数 extract_at_qq 测试
# ------------------------------------------------------------------ #


class TestExtractAtQQ:
    """extract_at_qq 辅助函数测试。"""

    def test_valid_at_match(self) -> None:
        """正常的 At Match 对象应提取出 QQ 号。"""
        match = MagicMock()
        match.available = True
        match.result = MagicMock()
        match.result.origin = MagicMock()
        match.result.origin.data = {"qq": "12345"}
        assert extract_at_qq(match) == "12345"

    def test_not_available(self) -> None:
        """available=False 时应返回 None。"""
        match = MagicMock()
        match.available = False
        assert extract_at_qq(match) is None

    def test_no_available_attr(self) -> None:
        """无 available 属性时应返回 None。"""
        assert extract_at_qq(42) is None

    def test_result_none(self) -> None:
        """result 为 None 时应返回 None。"""
        match = MagicMock()
        match.available = True
        match.result = None
        assert extract_at_qq(match) is None

    def test_origin_none(self) -> None:
        """origin 为 None 时应返回 None。"""
        match = MagicMock()
        match.available = True
        match.result = MagicMock()
        match.result.origin = None
        assert extract_at_qq(match) is None

    def test_data_none(self) -> None:
        """data 为 None 时应返回 None。"""
        match = MagicMock()
        match.available = True
        match.result = MagicMock()
        match.result.origin = MagicMock()
        match.result.origin.data = None
        assert extract_at_qq(match) is None

    def test_data_no_qq_key(self) -> None:
        """data 中无 'qq' 键时应返回 None。"""
        match = MagicMock()
        match.available = True
        match.result = MagicMock()
        match.result.origin = MagicMock()
        match.result.origin.data = {"other": "value"}
        assert extract_at_qq(match) is None


# ------------------------------------------------------------------ #
#  辅助函数 extract_text 测试
# ------------------------------------------------------------------ #


class TestExtractText:
    """extract_text 辅助函数测试。"""

    def test_single_match(self) -> None:
        """单个有效 Match 应返回其文本。"""
        m = MagicMock()
        m.available = True
        m.result = "hello"
        assert extract_text(m) == "hello"

    def test_multiple_matches(self) -> None:
        """多个有效 Match 应以空格拼接。"""
        m1 = MagicMock()
        m1.available = True
        m1.result = "hello"
        m2 = MagicMock()
        m2.available = True
        m2.result = "world"
        assert extract_text(m1, m2) == "hello world"

    def test_skip_unavailable(self) -> None:
        """available=False 的 Match 应被跳过。"""
        m1 = MagicMock()
        m1.available = False
        m2 = MagicMock()
        m2.available = True
        m2.result = "only"
        assert extract_text(m1, m2) == "only"

    def test_skip_none_result(self) -> None:
        """result=None 的 Match 应被跳过。"""
        m = MagicMock()
        m.available = True
        m.result = None
        assert extract_text(m) == ""

    def test_strip_whitespace(self) -> None:
        """结果文本应去除前后空白。"""
        m = MagicMock()
        m.available = True
        m.result = "  hello  "
        assert extract_text(m) == "hello"

    def test_empty_matches(self) -> None:
        """无参数时应返回空字符串。"""
        assert extract_text() == ""

    def test_non_string_result(self) -> None:
        """非字符串 result 应被转换为字符串。"""
        m = MagicMock()
        m.available = True
        m.result = 12345
        assert extract_text(m) == "12345"

    def test_no_available_attr(self) -> None:
        """无 available 属性的对象应被跳过。"""
        assert extract_text(42) == ""
