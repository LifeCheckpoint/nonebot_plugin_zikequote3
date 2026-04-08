"""fuzzy_search_quote_cmd 命令处理器单元测试。"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.user_service import UserService
from nonebot_plugin_zikequote3.vector_search.capability import (
    UnavailableVectorSearchService,
    VectorCapabilityStatus,
    VectorSearchCapability,
)

_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_fuzzy_search_quote: MagicMock = getattr(
    _stub_cmd_def, "matcher_fuzzy_search_quote"
)

from nonebot_plugin_zikequote3.command.cmds.fuzzy_search_quote_cmd import (  # noqa: E402
    handle_fuzzy_search_quote,
)


def _make_match(*, available: bool = False, result=None) -> MagicMock:
    match = MagicMock()
    match.available = available
    match.result = result
    return match


def _make_keyword_match(text: str) -> MagicMock:
    uni_msg = MagicMock()
    uni_msg.extract_plain_text.return_value = text
    return _make_match(available=True, result=uni_msg)


def _make_query(*, available: bool = True, result=None) -> MagicMock:
    query = MagicMock()
    query.available = available
    query.result = result
    return query


class TestHandleFuzzySearchQuote:
    async def test_finish_when_vector_capability_unavailable(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.embedding.enabled = True
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)
        patch_container({
            ConfigService: mock_config_svc,
            VectorSearchCapability: UnavailableVectorSearchService("基础设施未就绪"),
            QuoteReadService: AsyncMock(spec=QuoteReadService),
            UserService: AsyncMock(spec=UserService),
            ImageStore: MagicMock(spec=ImageStore),
            HtmlRenderServiceBase: AsyncMock(spec=HtmlRenderServiceBase),
        })

        with pytest.raises(FinishedException):
            await handle_fuzzy_search_quote(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                keyword=_make_keyword_match("测试关键词"),
                similarity=_make_match(),
                top_n=_make_match(),
                no_image=_make_query(result=False),
            )

        finish_calls = matcher_fuzzy_search_quote.finish.call_args_list
        assert any("基础设施未就绪" in str(call) for call in finish_calls)

    async def test_parse_shorthand_and_delegate_to_shared_fuzzy_flow(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.embedding.enabled = True
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        vector_capability = MagicMock(spec=VectorSearchCapability)
        vector_capability.get_status.return_value = VectorCapabilityStatus.available_status()
        patch_container({
            ConfigService: mock_config_svc,
            VectorSearchCapability: vector_capability,
            QuoteReadService: AsyncMock(spec=QuoteReadService),
            UserService: AsyncMock(spec=UserService),
            ImageStore: MagicMock(spec=ImageStore),
            HtmlRenderServiceBase: AsyncMock(spec=HtmlRenderServiceBase),
        })

        with patch(
            "nonebot_plugin_zikequote3.command.cmds.fuzzy_search_quote_cmd._do_fuzzy_search",
            new_callable=AsyncMock,
        ) as mock_do_fuzzy_search:
            await handle_fuzzy_search_quote(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                keyword=_make_keyword_match("15 hello world"),
                similarity=_make_match(),
                top_n=_make_match(),
                no_image=_make_query(result=False),
            )

        mock_do_fuzzy_search.assert_awaited_once()
        args = mock_do_fuzzy_search.await_args.args
        params = args[2]
        assert args[1] == "123456"
        assert params.top_n == 15
        assert params.pattern == "hello world"
