"""
自定义 @inject 装饰器与 Inject() 标记函数。

通过声明式语法简化命令处理器中的 DI 服务获取，
消除重复的 get_container() → async with container() → scope.get() 样板代码。

用法::

    @matcher.handle()
    @inject
    async def handler(
        event: GroupMessageEvent,
        arg: Message = CommandArg(),
        review_svc: ReviewService = Inject(ReviewService),
    ) -> None:
        ...

装饰器顺序：@inject 必须在 @matcher.handle() **之下**（紧贴函数定义）。
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Coroutine, TypeVar

from .nonebot_integration import get_container

T = TypeVar("T")


class _InjectMarker:
    """
    DI 注入标记，用于在函数签名中标识需要从 dishka 容器获取的参数。

    :param service_type: 需要注入的服务类型
    :type service_type: type
    """

    __slots__ = ("service_type",)

    def __init__(self, service_type: type) -> None:
        self.service_type = service_type

    def __repr__(self) -> str:
        return f"Inject({self.service_type.__name__})"


def Inject(service_type: type[T]) -> T:  # noqa: N802
    """
    声明一个需要从 dishka DI 容器注入的参数。

    返回 ``_InjectMarker`` 实例，但类型标注为 ``T``，
    使 IDE 能正确推断参数类型。必须与 :func:`inject` 装饰器配合使用。

    :param service_type: 需要注入的服务类型
    :type service_type: type[T]
    :returns: 注入标记实例（运行时为 ``_InjectMarker``，类型标注为 ``T``）
    :rtype: T
    """
    return _InjectMarker(service_type)  # type: ignore[return-value]


def inject(fn: Callable[..., Coroutine]) -> Callable[..., Coroutine]:  # type: ignore[type-arg]
    """
    装饰器：自动从 dishka 容器注入标记为 ``Inject()`` 的参数。

    工作原理：

    1. 通过 ``inspect.signature`` 扫描原函数签名，
       识别 default 为 ``_InjectMarker`` 的参数。
    2. 如果没有 ``Inject`` 参数，直接返回原函数（零开销）。
    3. 创建 wrapper 函数，在调用时：

       a. 调用 ``get_container()`` 获取全局容器
       b. ``async with container() as scope`` 创建 REQUEST 作用域
       c. 从 scope 中获取所有标记的服务
       d. 将服务作为关键字参数传入原函数

    4. 修改 ``wrapper.__signature__``，移除 ``Inject`` 参数，
       使 NoneBot2 不会尝试解析它们。

    :param fn: 需要注入依赖的异步函数
    :type fn: Callable[..., Coroutine]
    :returns: 包装后的异步函数，自动注入标记的依赖
    :rtype: Callable[..., Coroutine]
    """
    original_sig = inspect.signature(fn)

    # 识别需要注入的参数
    inject_params: dict[str, type] = {}  # param_name -> service_type
    kept_params: list[inspect.Parameter] = []

    for name, param in original_sig.parameters.items():
        if isinstance(param.default, _InjectMarker):
            inject_params[name] = param.default.service_type
        else:
            kept_params.append(param)

    # 没有 Inject 参数 → 直接返回原函数（零开销）
    if not inject_params:
        return fn

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        container = get_container()
        async with container() as request_scope:
            for param_name, service_type in inject_params.items():
                kwargs[param_name] = await request_scope.get(service_type)
            return await fn(*args, **kwargs)

    # 修改签名：移除 Inject 参数，NoneBot2 只看到框架参数
    wrapper.__signature__ = original_sig.replace(parameters=kept_params)  # type: ignore[attr-defined]

    return wrapper
