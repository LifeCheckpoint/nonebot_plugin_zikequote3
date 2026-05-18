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

from nonebot import logger

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


def _resolve_annotation(annotation: Any, globalns: dict[str, Any]) -> Any:
    """
    尝试将字符串注解（ForwardRef）解析为真实类型对象。

    当注解为 ``str`` 类型时，使用提供的全局命名空间 ``eval()`` 解析；
    若注解为 ``inspect.Parameter.empty`` 或已经是类型对象，则原样返回。
    解析失败时静默回退，保留原始字符串注解。

    :param annotation: 参数或返回值的注解，可能是字符串、类型对象或 ``empty``
    :type annotation: Any
    :param globalns: 用于解析字符串注解的全局命名空间（通常为 ``fn.__globals__``）
    :type globalns: dict[str, Any]
    :returns: 解析后的类型对象，或在无法解析时返回原始注解
    :rtype: Any
    """
    if not isinstance(annotation, str):
        return annotation
    try:
        return eval(annotation, globalns)  # noqa: S307
    except Exception:
        logger.opt(exception=True).warning(
            "ForwardRef 注解 '{}' 解析失败，将保留为字符串。"
            "如果后续出现 NameError，请检查类型导入是否正确。",
            annotation,
        )
        return annotation


def _resolve_param_annotation(
    param: inspect.Parameter, globalns: dict[str, Any]
) -> inspect.Parameter:
    """
    对单个参数的注解进行 ForwardRef 预解析。

    如果注解是字符串且能成功解析，返回替换了注解的新 Parameter；
    否则返回原始 Parameter。

    :param param: 需要处理的函数参数
    :type param: inspect.Parameter
    :param globalns: 用于解析字符串注解的全局命名空间
    :type globalns: dict[str, Any]
    :returns: 注解已解析（或无需解析）的参数
    :rtype: inspect.Parameter
    """
    resolved = _resolve_annotation(param.annotation, globalns)
    if resolved is not param.annotation:
        return param.replace(annotation=resolved)
    return param


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

    # 被装饰函数的全局命名空间，用于解析 ForwardRef 字符串注解。
    # 当命令 handler 文件使用 ``from __future__ import annotations`` 时，
    # 所有注解在运行时均为字符串（PEP 563）。wrapper 的 ``__globals__``
    # 指向 inject.py 的命名空间，缺少 handler 文件中导入的类型
    # （如 ``GroupMessageEvent``、``Bot``），导致 NoneBot2 调用
    # ``get_typed_signature(wrapper)`` 解析 ForwardRef 时抛出 NameError。
    # 因此在此处使用原函数的 ``__globals__`` 预先解析字符串注解为真实类型对象，
    # 使 wrapper 签名中的注解不再依赖 ``__globals__`` 解析。
    fn_globals: dict[str, Any] = getattr(fn, "__globals__", {})

    # 识别需要注入的参数
    inject_params: dict[str, type] = {}  # param_name -> service_type
    kept_params: list[inspect.Parameter] = []

    for name, param in original_sig.parameters.items():
        if isinstance(param.default, _InjectMarker):
            inject_params[name] = param.default.service_type
        else:
            # 预解析字符串注解（ForwardRef），避免 NoneBot2 通过
            # wrapper.__globals__ 解析时因命名空间不匹配而失败。
            resolved_param = _resolve_param_annotation(param, fn_globals)
            kept_params.append(resolved_param)

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

    # 预解析 return annotation
    resolved_return = _resolve_annotation(
        original_sig.return_annotation, fn_globals
    )

    # 修改签名：移除 Inject 参数，NoneBot2 只看到框架参数
    wrapper.__signature__ = original_sig.replace(  # type: ignore[attr-defined]
        parameters=kept_params,
        return_annotation=resolved_return,
    )

    return wrapper
