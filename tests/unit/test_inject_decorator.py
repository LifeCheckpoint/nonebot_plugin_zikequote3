"""
@inject 装饰器与 Inject() 标记函数的单元测试。

测试覆盖：
1. 无 Inject 参数时直接返回原函数（零开销验证）
2. 单个服务注入
3. 多个服务注入（共享同一 request scope）
4. 混合参数（NoneBot2 参数不受影响）
5. 签名修改（wrapper.__signature__ 中不包含 Inject 参数）
6. 异常传播
7. scope 生命周期（scope 在函数执行后正确关闭）
"""

from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nonebot_plugin_zikequote3.di.inject import Inject, _InjectMarker, inject


# ---------------------------------------------------------------------------
# 测试用的 dummy 服务类
# ---------------------------------------------------------------------------


class _ServiceA:
    """测试用服务 A。"""


class _ServiceB:
    """测试用服务 B。"""


# ---------------------------------------------------------------------------
# Mock 容器工具
# ---------------------------------------------------------------------------


def _make_mock_container(
    service_map: dict[type, Any],
) -> tuple[MagicMock, AsyncMock]:
    """
    创建模拟的 dishka 容器和 scope。

    返回:
        (mock_container, mock_scope)
        mock_container() 作为 async context manager 返回 mock_scope，
        mock_scope.get(service_type) 从 service_map 中查找并返回实例。
    """
    mock_scope = AsyncMock()
    mock_scope.get = AsyncMock(side_effect=lambda svc_type: service_map[svc_type])

    # scope 需要支持 async with，记录 __aenter__ / __aexit__ 调用
    mock_scope.__aenter__ = AsyncMock(return_value=mock_scope)
    mock_scope.__aexit__ = AsyncMock(return_value=False)

    # container() 返回 scope（async context manager）
    mock_container = MagicMock()
    mock_container.return_value = mock_scope

    return mock_container, mock_scope


# ---------------------------------------------------------------------------
# 1. 无 Inject 参数时直接返回原函数
# ---------------------------------------------------------------------------


class TestInjectNoopWithoutMarkers:
    """验证无 Inject 参数时 @inject 直接返回原函数（零开销）。"""

    async def test_returns_original_function(self) -> None:
        """没有 Inject 参数时，@inject 应返回原函数本身。"""

        async def handler(event: str, bot: int) -> str:
            return "ok"

        decorated = inject(handler)
        assert decorated is handler

    async def test_no_container_call(self) -> None:
        """没有 Inject 参数时，不应调用 get_container()。"""

        async def handler() -> str:
            return "ok"

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container"
        ) as mock_get:
            decorated = inject(handler)
            result = await decorated()
            mock_get.assert_not_called()
            assert result == "ok"


# ---------------------------------------------------------------------------
# 2. 单个服务注入
# ---------------------------------------------------------------------------


class TestInjectSingleService:
    """验证单个服务被正确注入到函数参数中。"""

    async def test_single_service_injected(self) -> None:
        """单个 Inject 参数应被正确解析并注入。"""
        svc_a_instance = _ServiceA()
        mock_container, mock_scope = _make_mock_container(
            {_ServiceA: svc_a_instance}
        )

        @inject
        async def handler(svc_a: _ServiceA = Inject(_ServiceA)) -> _ServiceA:
            return svc_a

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            result = await handler()

        assert result is svc_a_instance
        mock_scope.get.assert_awaited_once_with(_ServiceA)


# ---------------------------------------------------------------------------
# 3. 多个服务注入（共享同一 request scope）
# ---------------------------------------------------------------------------


class TestInjectMultipleServices:
    """验证多个服务共享同一 request scope。"""

    async def test_multiple_services_injected(self) -> None:
        """多个 Inject 参数应从同一 scope 获取。"""
        svc_a_instance = _ServiceA()
        svc_b_instance = _ServiceB()
        mock_container, mock_scope = _make_mock_container(
            {_ServiceA: svc_a_instance, _ServiceB: svc_b_instance}
        )

        @inject
        async def handler(
            svc_a: _ServiceA = Inject(_ServiceA),
            svc_b: _ServiceB = Inject(_ServiceB),
        ) -> tuple:
            return (svc_a, svc_b)

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            result = await handler()

        assert result == (svc_a_instance, svc_b_instance)
        # 两次 get 调用都在同一个 scope 上
        assert mock_scope.get.await_count == 2

    async def test_shared_scope(self) -> None:
        """多个服务应共享同一 request scope（只创建一次 scope）。"""
        mock_container, mock_scope = _make_mock_container(
            {_ServiceA: _ServiceA(), _ServiceB: _ServiceB()}
        )

        @inject
        async def handler(
            svc_a: _ServiceA = Inject(_ServiceA),
            svc_b: _ServiceB = Inject(_ServiceB),
        ) -> None:
            pass

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            await handler()

        # container() 只被调用一次（创建一个 scope）
        mock_container.assert_called_once()


# ---------------------------------------------------------------------------
# 4. 混合参数（NoneBot2 参数不受影响）
# ---------------------------------------------------------------------------


class TestInjectMixedParams:
    """验证 NoneBot2 参数（位置参数、关键字参数）不受影响。"""

    async def test_positional_args_preserved(self) -> None:
        """位置参数应正常传递给原函数。"""
        svc_a_instance = _ServiceA()
        mock_container, _ = _make_mock_container({_ServiceA: svc_a_instance})

        @inject
        async def handler(
            event: str,
            bot: int,
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> tuple:
            return (event, bot, svc_a)

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            result = await handler("test_event", 42)

        assert result == ("test_event", 42, svc_a_instance)

    async def test_keyword_args_preserved(self) -> None:
        """关键字参数应正常传递给原函数。"""
        svc_a_instance = _ServiceA()
        mock_container, _ = _make_mock_container({_ServiceA: svc_a_instance})

        @inject
        async def handler(
            event: str,
            bot: int = 0,
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> tuple:
            return (event, bot, svc_a)

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            result = await handler("test_event", bot=99)

        assert result == ("test_event", 99, svc_a_instance)

    async def test_default_values_preserved(self) -> None:
        """非 Inject 的默认值参数应保持原有行为。"""
        svc_a_instance = _ServiceA()
        mock_container, _ = _make_mock_container({_ServiceA: svc_a_instance})

        sentinel = object()

        @inject
        async def handler(
            event: str,
            flag: object = sentinel,
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> tuple:
            return (event, flag, svc_a)

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            result = await handler("evt")

        assert result == ("evt", sentinel, svc_a_instance)


# ---------------------------------------------------------------------------
# 5. 签名修改
# ---------------------------------------------------------------------------


class TestInjectSignatureModification:
    """验证 wrapper.__signature__ 中不包含 Inject 参数。"""

    async def test_inject_params_removed_from_signature(self) -> None:
        """Inject 参数应从 wrapper 签名中移除。"""

        @inject
        async def handler(
            event: str,
            bot: int,
            svc_a: _ServiceA = Inject(_ServiceA),
            svc_b: _ServiceB = Inject(_ServiceB),
        ) -> None:
            pass

        sig = inspect.signature(handler)
        param_names = list(sig.parameters.keys())
        assert param_names == ["event", "bot"]
        assert "svc_a" not in param_names
        assert "svc_b" not in param_names

    async def test_non_inject_params_preserved_in_signature(self) -> None:
        """非 Inject 参数应保留在 wrapper 签名中。"""

        sentinel = object()

        @inject
        async def handler(
            event: str,
            bot: int,
            flag: object = sentinel,
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> None:
            pass

        sig = inspect.signature(handler)
        param_names = list(sig.parameters.keys())
        assert param_names == ["event", "bot", "flag"]
        # 验证 flag 的默认值保持不变
        assert sig.parameters["flag"].default is sentinel

    async def test_functools_wraps_metadata(self) -> None:
        """wrapper 应保留原函数的 __name__ 和 __doc__。"""

        @inject
        async def my_handler(
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> None:
            """Handler docstring."""

        assert my_handler.__name__ == "my_handler"
        assert my_handler.__doc__ == "Handler docstring."


# ---------------------------------------------------------------------------
# 6. 异常传播
# ---------------------------------------------------------------------------


class TestInjectExceptionPropagation:
    """验证函数内抛出的异常正常传播。"""

    async def test_runtime_error_propagates(self) -> None:
        """RuntimeError 应正常传播。"""
        mock_container, _ = _make_mock_container({_ServiceA: _ServiceA()})

        @inject
        async def handler(
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> None:
            raise RuntimeError("test error")

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            with pytest.raises(RuntimeError, match="test error"):
                await handler()

    async def test_custom_exception_propagates(self) -> None:
        """自定义异常（模拟 FinishedException）应正常传播。"""

        class FinishedException(Exception):
            """模拟 NoneBot2 的 FinishedException。"""

        mock_container, _ = _make_mock_container({_ServiceA: _ServiceA()})

        @inject
        async def handler(
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> None:
            raise FinishedException("finish")

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            with pytest.raises(FinishedException, match="finish"):
                await handler()

    async def test_base_exception_propagates(self) -> None:
        """BaseException 子类（如 KeyboardInterrupt）应正常传播。"""
        mock_container, _ = _make_mock_container({_ServiceA: _ServiceA()})

        @inject
        async def handler(
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> None:
            raise KeyboardInterrupt()

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            with pytest.raises(KeyboardInterrupt):
                await handler()


# ---------------------------------------------------------------------------
# 7. scope 生命周期
# ---------------------------------------------------------------------------


class TestInjectScopeLifecycle:
    """验证 scope 在函数执行后正确关闭。"""

    async def test_scope_closed_after_success(self) -> None:
        """正常执行后 scope 的 __aexit__ 应被调用。"""
        mock_container, mock_scope = _make_mock_container(
            {_ServiceA: _ServiceA()}
        )

        @inject
        async def handler(
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> str:
            return "ok"

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            await handler()

        mock_scope.__aexit__.assert_awaited_once()

    async def test_scope_closed_after_error(self) -> None:
        """异常时 scope 的 __aexit__ 仍应被调用。"""
        mock_container, mock_scope = _make_mock_container(
            {_ServiceA: _ServiceA()}
        )

        @inject
        async def handler(
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> None:
            raise ValueError("boom")

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            with pytest.raises(ValueError, match="boom"):
                await handler()

        mock_scope.__aexit__.assert_awaited_once()

    async def test_scope_exit_receives_exception_info(self) -> None:
        """异常时 __aexit__ 应收到异常信息。"""
        mock_container, mock_scope = _make_mock_container(
            {_ServiceA: _ServiceA()}
        )

        @inject
        async def handler(
            svc_a: _ServiceA = Inject(_ServiceA),
        ) -> None:
            raise RuntimeError("scope test")

        with patch(
            "nonebot_plugin_zikequote3.di.inject.get_container",
            return_value=mock_container,
        ):
            with pytest.raises(RuntimeError):
                await handler()

        # __aexit__ 被调用时应收到异常类型信息
        call_args = mock_scope.__aexit__.call_args
        assert call_args is not None
        # args[0] 是 exc_type
        assert call_args[0][0] is RuntimeError


# ---------------------------------------------------------------------------
# _InjectMarker 辅助测试
# ---------------------------------------------------------------------------


class TestInjectMarker:
    """_InjectMarker 和 Inject() 的基础行为测试。"""

    def test_inject_returns_marker(self) -> None:
        """Inject() 应返回 _InjectMarker 实例。"""
        marker = Inject(_ServiceA)
        assert isinstance(marker, _InjectMarker)

    def test_marker_stores_service_type(self) -> None:
        """_InjectMarker 应存储服务类型。"""
        marker = Inject(_ServiceA)
        assert marker.service_type is _ServiceA  # type: ignore[union-attr]

    def test_marker_repr(self) -> None:
        """_InjectMarker.__repr__ 应包含服务类名。"""
        marker = _InjectMarker(_ServiceA)
        assert repr(marker) == "Inject(_ServiceA)"
