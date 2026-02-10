"""
命令层单元测试 conftest —— 共享 fixture 与 mock 工具函数。

设计思路：
- 直接调用 handler 函数，mock DI 服务，不使用 nonebug App
- 通过 patch ``get_container`` 返回 mock container（方案A）
- 为 ``command_definition`` 模块注册 stub，避免触发 nonebot 初始化链
- ``matcher.finish()`` 在 NoneBot2 中抛出 FinishedException，测试中保持此行为

Stub 策略：
- ``tests/unit/conftest.py`` 已注册 ``nonebot_plugin_zikequote3``、
  ``nonebot_plugin_zikequote3.database``、``nonebot_plugin_zikequote3.services``
  三个 stub 包（仅有 ``__path__``，无属性）。
- 本 conftest 额外注册：
  1. ``nonebot_plugin_zikequote3.di`` stub（避免 ``di/__init__.py`` 触发
     ``container.py`` → providers 的重量级导入链）
  2. ``nonebot_plugin_zikequote3.command.command_definition`` stub（避免
     ``on_command`` / ``create_plugin_service`` 等模块级调用）
- 并为 ``services`` 和 ``di`` stub 填充实际的类/函数属性，
  使 handler 文件的 ``from ...services import XxxService`` 能正常工作。
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

_plugin_root = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "nonebot_plugin_zikequote3"
)

# ---------------------------------------------------------------------------
# 1) Stub di 包 —— 避免 di/__init__.py 触发 container.py 导入链
# ---------------------------------------------------------------------------
_di_root = _plugin_root / "di"
if "nonebot_plugin_zikequote3.di" not in sys.modules:
    _stub_di = types.ModuleType("nonebot_plugin_zikequote3.di")
    _stub_di.__path__ = [str(_di_root)]
    sys.modules["nonebot_plugin_zikequote3.di"] = _stub_di

# di.inject 和 di.nonebot_integration 可安全导入（仅依赖 dishka）
from nonebot_plugin_zikequote3.di.inject import Inject, inject  # noqa: E402

_di_mod = sys.modules["nonebot_plugin_zikequote3.di"]
_di_mod.Inject = Inject  # type: ignore[attr-defined]
_di_mod.inject = inject  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# 2) 填充 services stub —— 使 handler 的 from ...services import XxxService 可用
#    （services 子模块本身不依赖 nonebot，可安全导入）
# ---------------------------------------------------------------------------
from nonebot_plugin_zikequote3.services.config_service import ConfigService  # noqa: E402
from nonebot_plugin_zikequote3.services.group_service import GroupService  # noqa: E402
from nonebot_plugin_zikequote3.services.migration_service import MigrationService  # noqa: E402
from nonebot_plugin_zikequote3.services.quote_collection_service import QuoteCollectionService  # noqa: E402
from nonebot_plugin_zikequote3.services.quote_read_service import QuoteReadService  # noqa: E402
from nonebot_plugin_zikequote3.services.quote_write_service import QuoteWriteService  # noqa: E402
from nonebot_plugin_zikequote3.services.review_service import ReviewService  # noqa: E402
from nonebot_plugin_zikequote3.services.statistics_service import StatisticsService  # noqa: E402
from nonebot_plugin_zikequote3.services.user_service import UserService  # noqa: E402

_svc_mod = sys.modules["nonebot_plugin_zikequote3.services"]
_svc_mod.ConfigService = ConfigService  # type: ignore[attr-defined]
_svc_mod.GroupService = GroupService  # type: ignore[attr-defined]
_svc_mod.MigrationService = MigrationService  # type: ignore[attr-defined]
_svc_mod.QuoteCollectionService = QuoteCollectionService  # type: ignore[attr-defined]
_svc_mod.QuoteReadService = QuoteReadService  # type: ignore[attr-defined]
_svc_mod.QuoteWriteService = QuoteWriteService  # type: ignore[attr-defined]
_svc_mod.ReviewService = ReviewService  # type: ignore[attr-defined]
_svc_mod.StatisticsService = StatisticsService  # type: ignore[attr-defined]
_svc_mod.UserService = UserService  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# 3) Stub command 子包 —— 避免导入 command_definition.py 的模块级代码
# ---------------------------------------------------------------------------
_command_root = _plugin_root / "command"
if "nonebot_plugin_zikequote3.command" not in sys.modules:
    _stub_cmd = types.ModuleType("nonebot_plugin_zikequote3.command")
    _stub_cmd.__path__ = [str(_command_root)]
    sys.modules["nonebot_plugin_zikequote3.command"] = _stub_cmd

_cmds_root = _command_root / "cmds"
if "nonebot_plugin_zikequote3.command.cmds" not in sys.modules:
    _stub_cmds = types.ModuleType("nonebot_plugin_zikequote3.command.cmds")
    _stub_cmds.__path__ = [str(_cmds_root)]
    sys.modules["nonebot_plugin_zikequote3.command.cmds"] = _stub_cmds

# ---------------------------------------------------------------------------
# 4) Stub command_definition —— 提供 mock matcher 对象
# ---------------------------------------------------------------------------
_ALL_MATCHER_NAMES = [
    "matcher_collecting_listener",
    "matcher_get_ranking",
    "matcher_get_quote_list",
    "matcher_get_user_info",
    "matcher_add_quote",
    "matcher_add_quote_image",
    "matcher_remove_quote",
    "matcher_remove_quote_image",
    "matcher_add_quote_comment",
    "matcher_add_quote_comment_no_prefix",
    "matcher_remove_quote_comment",
    "matcher_random_quote",
    "matcher_random_quote_card",
    "matcher_search_quote",
    "matcher_random_quote_image",
    "matcher_update_quote_force",
    "matcher_get_current_config",
    "matcher_modify_config",
    "matcher_batch_modify_config",
    "matcher_reset_config",
    "matcher_reload_config",
    "matcher_group_migration",
    "matcher_get_privacy",
    "matcher_stop_using_zikequote3",
]


def _make_stub_matcher() -> MagicMock:
    """创建 stub matcher：handle() 透传、finish() 抛 FinishedException。"""
    m = MagicMock()
    m.finish = AsyncMock(side_effect=FinishedException)
    m.send = AsyncMock(return_value={"message_id": 12345})
    m.handle.return_value = lambda fn: fn
    return m


_stub_cmd_def = types.ModuleType(
    "nonebot_plugin_zikequote3.command.command_definition"
)
for _name in _ALL_MATCHER_NAMES:
    setattr(_stub_cmd_def, _name, _make_stub_matcher())
sys.modules[
    "nonebot_plugin_zikequote3.command.command_definition"
] = _stub_cmd_def


# ---------------------------------------------------------------------------
# Mock 容器工具函数（从 test_inject_decorator.py 提取为共享版本）
# ---------------------------------------------------------------------------


def make_mock_container(
    service_map: dict[type, Any],
) -> tuple[MagicMock, AsyncMock]:
    """
    创建模拟的 dishka 容器和 scope。

    Args:
        service_map: ``{ServiceType: instance}`` 映射表。

    Returns:
        ``(mock_container, mock_scope)`` 元组。
        ``mock_container()`` 作为 async context manager 返回 ``mock_scope``，
        ``mock_scope.get(service_type)`` 从 *service_map* 中查找并返回实例。
    """
    mock_scope = AsyncMock()
    mock_scope.get = AsyncMock(
        side_effect=lambda svc_type: service_map[svc_type]
    )

    # scope 需要支持 async with
    mock_scope.__aenter__ = AsyncMock(return_value=mock_scope)
    mock_scope.__aexit__ = AsyncMock(return_value=False)

    # container() 返回 scope（async context manager）
    mock_container = MagicMock()
    mock_container.return_value = mock_scope

    return mock_container, mock_scope


# ---------------------------------------------------------------------------
# Mock matcher 工具函数
# ---------------------------------------------------------------------------


def create_mock_matcher() -> MagicMock:
    """
    创建一个行为与 NoneBot2 Matcher 一致的 mock matcher。

    - ``finish()`` 抛出 :class:`FinishedException`（与 NoneBot2 行为一致）
    - ``send()`` 返回 ``AsyncMock``（可正常 await）
    - ``handle()`` 返回透传装饰器（不修改被装饰函数）
    """
    mock = MagicMock()
    mock.finish = AsyncMock(side_effect=FinishedException)
    mock.send = AsyncMock(return_value={"message_id": 12345})
    mock.handle.return_value = lambda fn: fn
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_stub_matchers():
    """每个测试前重置所有 stub matcher 的调用记录。"""
    for name in _ALL_MATCHER_NAMES:
        matcher = getattr(_stub_cmd_def, name)
        matcher.finish.reset_mock()
        matcher.finish.side_effect = FinishedException
        matcher.send.reset_mock()
        matcher.send.return_value = {"message_id": 12345}
    yield


@pytest.fixture
def patch_container():
    """
    Fixture 工厂：patch ``get_container`` 并返回辅助对象。

    用法::

        def test_xxx(patch_container):
            ctx = patch_container({SomeService: mock_svc})
            # ctx.container — mock 容器
            # ctx.scope    — mock scope
            # 此时 get_container() 已被 patch

    Returns:
        一个可调用对象，接受 ``service_map`` 参数，返回包含
        ``container`` 和 ``scope`` 属性的命名空间。
    """

    class _PatchContext:
        def __init__(self, container: MagicMock, scope: AsyncMock):
            self.container = container
            self.scope = scope

    _stack: list[Any] = []

    def _factory(service_map: dict[type, Any]) -> _PatchContext:
        mock_container, mock_scope = make_mock_container(service_map)
        patcher = patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        )
        patcher.start()
        _stack.append(patcher)
        return _PatchContext(mock_container, mock_scope)

    yield _factory

    # teardown：停止所有 patcher
    for p in reversed(_stack):
        p.stop()


@pytest.fixture
def mock_group_event() -> MagicMock:
    """
    模拟 ``GroupMessageEvent``。

    提供命令处理器常用的属性：
    - ``group_id``: 群号
    - ``user_id``: 用户 QQ 号
    - ``sender``: 发送者信息（含 ``nickname``、``card``）
    - ``reply``: 回复消息（默认 ``None``）
    """
    event = MagicMock()
    event.group_id = 123456
    event.user_id = 654321
    event.sender = MagicMock()
    event.sender.nickname = "测试用户"
    event.sender.card = "测试群名片"
    event.reply = None
    return event


@pytest.fixture
def mock_bot() -> MagicMock:
    """
    模拟 ``Bot`` 对象。

    提供常用的异步方法：
    - ``get_group_member_info``: 返回包含 nickname/card 的字典
    - ``send``: 返回 message_id
    """
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock(
        return_value={"nickname": "测试用户", "card": "测试群名片"}
    )
    bot.send = AsyncMock(return_value={"message_id": 99999})
    return bot


@pytest.fixture
def mock_message() -> MagicMock:
    """
    模拟 ``Message`` 对象（通常由 ``CommandArg()`` 提供）。

    默认 ``extract_plain_text()`` 返回空字符串。
    可在测试中通过 ``mock_message.extract_plain_text.return_value = "xxx"``
    自定义返回值。
    """
    msg = MagicMock()
    msg.extract_plain_text.return_value = ""
    return msg
