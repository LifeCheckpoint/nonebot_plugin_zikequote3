"""
recent_quotes_cmd 命令处理器单元测试。

覆盖：
- 默认 3 条 / 显式 1、6、10 条
- 超上限截断并写入 listing 头部轻提示
- 非法参数走现有错误提示风格
- 空结果走现有空结果消息路径且不触发 listing 渲染
- 非空结果继续复用 listing 渲染与 HTML 截图链路
"""

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

_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_recent_quotes: MagicMock = getattr(_stub_cmd_def, "matcher_recent_quotes")

from nonebot_plugin_zikequote3.command.cmds.recent_quotes_cmd import (  # noqa: E402
    _parse_recent_limit,
    handle_recent_quotes,
)

_CMD_MODULE = "nonebot_plugin_zikequote3.command.cmds.recent_quotes_cmd"


class _FakeMessage:
    def __init__(self, plain_text: str = "", raw_text: str | None = None) -> None:
        self._plain_text = plain_text
        self._raw_text = raw_text if raw_text is not None else plain_text

    def extract_plain_text(self) -> str:
        return self._plain_text

    def __str__(self) -> str:
        return self._raw_text


def _make_quote(
    *,
    quote_id: str = "Q-1",
    author_id: str = "111111",
    content: str = "语录内容",
) -> MagicMock:
    q = MagicMock()
    q.quote_id = quote_id
    q.author_id = author_id
    q.content = content
    q.image_content_uuid = None
    q.time_stamp = MagicMock()
    return q


def _install_services(patch_container, *, quotes: list[MagicMock]):
    mock_read_svc = AsyncMock(spec=QuoteReadService)
    mock_read_svc.get_recent_quotes_by_group = AsyncMock(return_value=quotes)
    mock_user_svc = AsyncMock(spec=UserService)
    mock_image_store = MagicMock(spec=ImageStore)
    mock_render_svc = AsyncMock(spec=HtmlRenderServiceBase)
    mock_render_svc.render = AsyncMock(return_value=b"\x89PNG_FAKE")
    mock_config_svc = AsyncMock(spec=ConfigService)
    mock_cfg = MagicMock()
    mock_cfg.showcase.quote_content_max_length = 500
    mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)

    patch_container({
        QuoteReadService: mock_read_svc,
        UserService: mock_user_svc,
        ImageStore: mock_image_store,
        HtmlRenderServiceBase: mock_render_svc,
        ConfigService: mock_config_svc,
    })
    return (
        mock_read_svc,
        mock_user_svc,
        mock_image_store,
        mock_render_svc,
        mock_config_svc,
    )


class TestParseRecentLimit:
    def test_default_limit(self) -> None:
        assert _parse_recent_limit("") == (3, None)

    def test_accept_valid_limit(self) -> None:
        assert _parse_recent_limit("6") == (6, None)

    def test_clamp_limit(self) -> None:
        assert _parse_recent_limit("20") == (10, "已按上限展示最近 10 条语录")

    @pytest.mark.parametrize("text", ["0", "-1", "abc", "1 abc"])
    def test_invalid_limit_raises(self, text: str) -> None:
        with pytest.raises(Exception):
            _parse_recent_limit(text, text)


class TestHandleRecentQuotes:
    async def test_recent_quotes_default_limit_uses_3(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        quotes = [_make_quote()]
        (
            mock_read_svc,
            mock_user_svc,
            mock_image_store,
            mock_render_svc,
            mock_config_svc,
        ) = _install_services(patch_container, quotes=quotes)

        with (
            patch(f"{_CMD_MODULE}.transform_quotes_to_template_boxes",
                  new_callable=AsyncMock, return_value=[]),
            patch(f"{_CMD_MODULE}.render_list", return_value="<html>recent</html>"),
            pytest.raises(FinishedException),
        ):
            await handle_recent_quotes(
                event=mock_group_event,
                arg=_FakeMessage(),
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
                config_svc=mock_config_svc,
            )

        mock_read_svc.get_recent_quotes_by_group.assert_awaited_once_with(
            "123456", limit=3,
        )

    @pytest.mark.parametrize("limit_text, expected", [("1", 1), ("6", 6), ("10", 10)])
    async def test_recent_quotes_accepts_valid_limits(
        self,
        patch_container,
        mock_group_event: MagicMock,
        limit_text: str,
        expected: int,
    ) -> None:
        quotes = [_make_quote()]
        (
            mock_read_svc,
            mock_user_svc,
            mock_image_store,
            mock_render_svc,
            mock_config_svc,
        ) = _install_services(patch_container, quotes=quotes)

        with (
            patch(f"{_CMD_MODULE}.transform_quotes_to_template_boxes",
                  new_callable=AsyncMock, return_value=[]),
            patch(f"{_CMD_MODULE}.render_list", return_value="<html>recent</html>"),
            pytest.raises(FinishedException),
        ):
            await handle_recent_quotes(
                event=mock_group_event,
                arg=_FakeMessage(limit_text),
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
                config_svc=mock_config_svc,
            )

        mock_read_svc.get_recent_quotes_by_group.assert_awaited_once_with(
            "123456", limit=expected,
        )

    async def test_recent_quotes_limit_over_10_is_clamped_and_sets_hint(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        quotes = [_make_quote()]
        (
            mock_read_svc,
            mock_user_svc,
            mock_image_store,
            mock_render_svc,
            mock_config_svc,
        ) = _install_services(patch_container, quotes=quotes)

        captured_data = None

        def _capture(data):
            nonlocal captured_data
            captured_data = data
            return "<html>recent</html>"

        with (
            patch(f"{_CMD_MODULE}.transform_quotes_to_template_boxes",
                  new_callable=AsyncMock, return_value=[]),
            patch(f"{_CMD_MODULE}.render_list", side_effect=_capture),
            pytest.raises(FinishedException),
        ):
            await handle_recent_quotes(
                event=mock_group_event,
                arg=_FakeMessage("20"),
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
                config_svc=mock_config_svc,
            )

        mock_read_svc.get_recent_quotes_by_group.assert_awaited_once_with(
            "123456", limit=10,
        )
        assert captured_data is not None
        assert captured_data.title == "最近语录"
        assert captured_data.clamp_hint == "已按上限展示最近 10 条语录"

    @pytest.mark.parametrize("raw_arg", ["0", "abc", "1 abc"])
    async def test_recent_quotes_invalid_param_uses_existing_error_style(
        self,
        patch_container,
        mock_group_event: MagicMock,
        raw_arg: str,
    ) -> None:
        quotes = [_make_quote()]
        (
            mock_read_svc,
            mock_user_svc,
            mock_image_store,
            mock_render_svc,
            mock_config_svc,
        ) = _install_services(patch_container, quotes=quotes)

        with pytest.raises(FinishedException):
            await handle_recent_quotes(
                event=mock_group_event,
                arg=_FakeMessage(raw_arg, raw_arg),
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
                config_svc=mock_config_svc,
            )

        finish_calls = matcher_recent_quotes.finish.call_args_list
        assert any("输入有误" in str(c) for c in finish_calls)
        mock_read_svc.get_recent_quotes_by_group.assert_not_awaited()

    async def test_recent_quotes_empty_result_uses_existing_empty_message(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        (
            mock_read_svc,
            mock_user_svc,
            mock_image_store,
            mock_render_svc,
            mock_config_svc,
        ) = _install_services(patch_container, quotes=[])

        with (
            patch(f"{_CMD_MODULE}.transform_quotes_to_template_boxes",
                  new_callable=AsyncMock) as mock_transform,
            patch(f"{_CMD_MODULE}.render_list") as mock_render_list,
            pytest.raises(FinishedException),
        ):
            await handle_recent_quotes(
                event=mock_group_event,
                arg=_FakeMessage(),
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
                config_svc=mock_config_svc,
            )

        mock_transform.assert_not_awaited()
        mock_render_list.assert_not_called()
        mock_render_svc.render.assert_not_awaited()
        finish_calls = matcher_recent_quotes.finish.call_args_list
        assert any("没有找到" in str(c) or "没找到" in str(c) for c in finish_calls)

    async def test_recent_quotes_non_empty_result_uses_listing_render_path(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        quotes = [_make_quote()]
        (
            mock_read_svc,
            mock_user_svc,
            mock_image_store,
            mock_render_svc,
            mock_config_svc,
        ) = _install_services(patch_container, quotes=quotes)

        from nonebot_plugin_zikequote3.templates.schema.listing import TemplateQuoteBoxData

        transformed_boxes = [TemplateQuoteBoxData(quote_id="Q-1", quote_text="语录内容")]
        with (
            patch(f"{_CMD_MODULE}.transform_quotes_to_template_boxes",
                  new_callable=AsyncMock, return_value=transformed_boxes) as mock_transform,
            patch(f"{_CMD_MODULE}.render_list", return_value="<html>recent</html>") as mock_render_list,
            pytest.raises(FinishedException),
        ):
            await handle_recent_quotes(
                event=mock_group_event,
                arg=_FakeMessage("6"),
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
                config_svc=mock_config_svc,
            )

        mock_transform.assert_awaited_once()
        transform_kwargs = mock_transform.await_args.kwargs
        assert transform_kwargs["show_author"] is True
        assert transform_kwargs["show_time"] is True
        mock_render_list.assert_called_once()
        mock_render_svc.render.assert_awaited_once()

    async def test_recent_quotes_does_not_use_query_resolver(
        self,
        patch_container,
        mock_group_event: MagicMock,
    ) -> None:
        quotes = [_make_quote()]
        (
            mock_read_svc,
            mock_user_svc,
            mock_image_store,
            mock_render_svc,
            mock_config_svc,
        ) = _install_services(patch_container, quotes=quotes)

        with (
            patch(f"{_CMD_MODULE}.transform_quotes_to_template_boxes",
                  new_callable=AsyncMock, return_value=[]),
            patch(f"{_CMD_MODULE}.render_list", return_value="<html>recent</html>"),
            patch("nonebot_plugin_zikequote3.command.cmds.recent_quotes_cmd.QueryResolver",
                  create=True) as mock_query_resolver,
            pytest.raises(FinishedException),
        ):
            await handle_recent_quotes(
                event=mock_group_event,
                arg=_FakeMessage(),
                quote_read_svc=mock_read_svc,
                user_svc=mock_user_svc,
                image_store=mock_image_store,
                html_render_svc=mock_render_svc,
                config_svc=mock_config_svc,
            )

        mock_query_resolver.assert_not_called()
