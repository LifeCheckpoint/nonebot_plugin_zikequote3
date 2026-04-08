"""rebuild_index_cmd 命令处理器单元测试。"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from nonebot_plugin_zikequote3.services.config_service import ConfigService
from nonebot_plugin_zikequote3.vector_search.capability import (
    UnavailableVectorSearchService,
    VectorCapabilityStatus,
    VectorSearchCapability,
)

_stub_cmd_def = sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
]
matcher_rebuild_index: MagicMock = getattr(
    _stub_cmd_def, "matcher_rebuild_index"
)

from nonebot_plugin_zikequote3.command.cmds.rebuild_index_cmd import (  # noqa: E402
    handle_rebuild_index,
)


def _make_query(*, available: bool = True, result=None) -> MagicMock:
    query = MagicMock()
    query.available = available
    query.result = result
    return query


class TestHandleRebuildIndex:
    async def test_finish_when_vector_capability_unavailable(
        self,
        patch_container,
        mock_bot: MagicMock,
        mock_group_event: MagicMock,
    ) -> None:
        mock_config_svc = AsyncMock(spec=ConfigService)
        mock_cfg = MagicMock()
        mock_cfg.embedding.enabled = True
        mock_config_svc.get_parsed_config = AsyncMock(return_value=mock_cfg)
        vector_capability = UnavailableVectorSearchService("基础设施未就绪")
        patch_container({
            ConfigService: mock_config_svc,
            VectorSearchCapability: vector_capability,
        })

        with pytest.raises(FinishedException):
            await handle_rebuild_index(
                bot=mock_bot,
                event=mock_group_event,
                rebuild_all=_make_query(result=False),
            )

        finish_calls = matcher_rebuild_index.finish.call_args_list
        assert any("基础设施未就绪" in str(call) for call in finish_calls)

    async def test_schedule_background_rebuild_when_capability_available(
        self,
        patch_container,
        mock_bot: MagicMock,
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
        })

        sentinel_task = object()
        mock_container = MagicMock()

        with (
            patch(
                "nonebot_plugin_zikequote3.command.cmds.rebuild_index_cmd.get_container",
                return_value=mock_container,
            ),
            patch(
                "nonebot_plugin_zikequote3.command.cmds.rebuild_index_cmd._do_rebuild",
                new=MagicMock(return_value=sentinel_task),
            ) as mock_do_rebuild,
            patch(
                "nonebot_plugin_zikequote3.command.cmds.rebuild_index_cmd.asyncio.create_task"
            ) as mock_create_task,
        ):
            await handle_rebuild_index(
                bot=mock_bot,
                event=mock_group_event,
                rebuild_all=_make_query(result=False),
            )

        matcher_rebuild_index.send.assert_awaited_once()
        mock_do_rebuild.assert_called_once_with(
            mock_container,
            mock_bot,
            mock_group_event,
            "123456",
            "本群(123456)",
        )
        mock_create_task.assert_called_once_with(sentinel_task)
