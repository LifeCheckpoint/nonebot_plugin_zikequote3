"""
search_quote_cmd 命令处理器单元测试。

覆盖：
- handle_search_quote：搜索语录（成功搜索 / 无结果 / max_result 参数校验）
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.database.image_store import ImageStore
from nonebot_plugin_zikequote3.exceptions import ValidationException
from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.services.html_render_service import HtmlRenderServiceBase
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService
from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService
from nonebot_plugin_zikequote3.services.user_service import UserService
from nonebot_plugin_zikequote3.vector_search.search_service import VectorSearchService

# 运行时从 stub 模块获取 mock matcher
_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_search_quote: MagicMock = getattr(
    _stub_cmd_def, "matcher_search_quote"
)

# patch 模板渲染和辅助函数，避免 jinja2 依赖
with (
    patch(
        "nonebot_plugin_zikequote3.command.cmds.search_quote_cmd.render_list",
        return_value="<html>search</html>",
    ),
    patch(
        "nonebot_plugin_zikequote3.command.cmds.search_quote_cmd.transform_quotes_to_template_boxes",
        new_callable=AsyncMock,
        return_value=[],
    ),
):
    from nonebot_plugin_zikequote3.command.cmds.search_quote_cmd import (
        handle_search_quote,
    )


def _make_match(available: bool = False, result=None) -> MagicMock:
    """创建模拟的 Match 对象。"""
    m = MagicMock()
    m.available = available
    m.result = result
    return m


def _make_query(available: bool = True, result=None) -> MagicMock:
    """创建模拟的 Query 对象。"""
    q = MagicMock()
    q.available = available
    q.result = result
    return q


def _make_keyword_match(text: str) -> MagicMock:
    """创建模拟的 keyword Match（UniMessage 类型）。"""
    uni_msg = MagicMock()
    uni_msg.extract_plain_text.return_value = text
    return _make_match(available=True, result=uni_msg)


class TestHandleSearchQuote:
    """搜索语录命令。"""

    async def test_search_success(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """关键词搜索成功：渲染列表图片。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.search_quotes = AsyncMock(return_value=([], 0))
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.quote_content_max_length = 500
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        mock_vector_svc = AsyncMock(spec=VectorSearchService)

        patch_container({
            StatisticsService: mock_stats_svc,
            QuoteReadService: mock_read_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
            ConfigService: mock_config_svc,
            VectorSearchService: mock_vector_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_search_quote(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                max_result=_make_match(),
                keyword=_make_keyword_match("测试关键词"),
                similarity=_make_match(),
                top_n=_make_match(),
                no_image=_make_query(result=False),
                use_regex=_make_query(result=False),
                use_fuzzy=_make_query(result=False),
                stats_svc=mock_stats_svc,
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证搜索服务调用
        mock_stats_svc.search_quotes.assert_awaited_once()
        mock_render_svc.render.assert_awaited_once()

    async def test_max_result_too_small(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """max_result < 1：提示用户。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.quote_content_max_length = 500
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        mock_vector_svc = AsyncMock(spec=VectorSearchService)

        patch_container({
            StatisticsService: mock_stats_svc,
            QuoteReadService: mock_read_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
            ConfigService: mock_config_svc,
            VectorSearchService: mock_vector_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_search_quote(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                max_result=_make_match(available=True, result=0),
                keyword=_make_keyword_match("测试"),
                similarity=_make_match(),
                top_n=_make_match(),
                no_image=_make_query(result=False),
                use_regex=_make_query(result=False),
                use_fuzzy=_make_query(result=False),
                stats_svc=mock_stats_svc,
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含提示
        finish_calls = matcher_search_quote.finish.call_args_list
        assert any("至少为 1" in str(c) for c in finish_calls)

    async def test_render_failure(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """渲染失败：command_error_handler 捕获并发送错误消息。"""
        # Arrange
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.search_quotes = AsyncMock(return_value=([], 0))
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(
            side_effect=RuntimeError("playwright crashed"),
        )

        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.quote_content_max_length = 500
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        mock_vector_svc = AsyncMock(spec=VectorSearchService)

        patch_container({
            StatisticsService: mock_stats_svc,
            QuoteReadService: mock_read_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
            ConfigService: mock_config_svc,
            VectorSearchService: mock_vector_svc,
        })

        # Act & Assert
        with pytest.raises(FinishedException):
            await handle_search_quote(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                max_result=_make_match(),
                keyword=_make_keyword_match("测试"),
                similarity=_make_match(),
                top_n=_make_match(),
                no_image=_make_query(result=False),
                use_regex=_make_query(result=False),
                use_fuzzy=_make_query(result=False),
                stats_svc=mock_stats_svc,
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        # 验证 finish 包含 "发生错误" 通用消息
        finish_calls = matcher_search_quote.finish.call_args_list
        assert any("发生错误" in str(c) for c in finish_calls)

    async def test_hitokoto_url_passed_to_runtime_request(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """搜索展示链路会把运行时配置中的 hitokoto_url 传给一言请求入口。"""
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_stats_svc.search_quotes = AsyncMock(return_value=([], 0))
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.showcase.quote_content_max_length = 500
        mock_cfg.showcase.hitokoto_url = "https://example.com/hitokoto"
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)
        mock_vector_svc = AsyncMock(spec=VectorSearchService)

        patch_container({
            StatisticsService: mock_stats_svc,
            QuoteReadService: mock_read_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
            ConfigService: mock_config_svc,
            VectorSearchService: mock_vector_svc,
        })

        with patch(
            "nonebot_plugin_zikequote3.utils.hitokoto.get_hitokoto",
            return_value=("一句话", "作者"),
        ) as mock_hitokoto:
            with pytest.raises(FinishedException):
                await handle_search_quote(
                    event=mock_group_event,
                    at_user=_make_match(),
                    qq=_make_match(),
                    max_result=_make_match(),
                    keyword=_make_keyword_match("测试关键词"),
                    similarity=_make_match(),
                    top_n=_make_match(),
                    no_image=_make_query(result=False),
                    use_regex=_make_query(result=False),
                    use_fuzzy=_make_query(result=False),
                    stats_svc=mock_stats_svc,
                    quote_read_svc=mock_read_svc,
                    user_svc=mock_user_svc,
                    image_store=mock_image_store,
                    html_render_svc=mock_render_svc,
                )

        mock_hitokoto.assert_called_once_with(
            hitokoto_url="https://example.com/hitokoto"
        )

    async def test_fuzzy_search_uses_runtime_embedding_defaults(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        """未显式提供 -s/-n 时，模糊搜索使用运行时配置中的默认阈值与条数。"""
        mock_stats_svc = AsyncMock(spec=StatisticsService)
        mock_read_svc = AsyncMock(spec=QuoteReadService)
        mock_user_svc = AsyncMock(spec=UserService)
        mock_image_store = MagicMock(spec=ImageStore)
        mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
        mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.embedding.enabled = True
        mock_cfg.embedding.default_top_n = 7
        mock_cfg.embedding.default_threshold = 0.66
        mock_cfg.showcase.quote_content_max_length = 500
        mock_cfg.showcase.hitokoto_url = ""
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

        mock_vector_svc = AsyncMock(spec=VectorSearchService)
        mock_vector_svc.is_available = AsyncMock(return_value=True)
        mock_vector_svc.get_index_count = AsyncMock(return_value=1)
        mock_vector_svc.semantic_search = AsyncMock(return_value=[])

        patch_container({
            StatisticsService: mock_stats_svc,
            QuoteReadService: mock_read_svc,
            UserService: mock_user_svc,
            ImageStore: mock_image_store,
            HtmlRenderServiceBase: mock_render_svc,
            ConfigService: mock_config_svc,
            VectorSearchService: mock_vector_svc,
        })

        with pytest.raises(FinishedException):
            await handle_search_quote(
                event=mock_group_event,
                at_user=_make_match(),
                qq=_make_match(),
                max_result=_make_match(),
                keyword=_make_keyword_match("语义关键词"),
                similarity=_make_match(),
                top_n=_make_match(),
                no_image=_make_query(result=False),
                use_regex=_make_query(result=False),
                use_fuzzy=_make_query(result=True),
                stats_svc=mock_stats_svc,
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
            )

        mock_vector_svc.semantic_search.assert_awaited_once_with(
            "语义关键词",
            "123456",
            limit=7,
            threshold=0.66,
        )
