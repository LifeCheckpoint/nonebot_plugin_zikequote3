"""
NoneBot2 与 dishka 的桥接层。

由于 dishka 没有官方 NoneBot2 集成，此模块提供：
- setup_dishka(): 将 AsyncContainer 绑定到 NoneBot Driver 生命周期
- get_container(): 获取已绑定的 AsyncContainer 实例（供 handler 使用）

注意：此模块依赖 NoneBot2 运行时，单元测试中不测试此模块。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from dishka import AsyncContainer

if TYPE_CHECKING:
    from nonebot.internal.driver import Driver

# 模块级容器引用，由 setup_dishka() 设置
_container: Optional[AsyncContainer] = None


def setup_dishka(container: AsyncContainer, driver: "Driver") -> None:
    """
    将 dishka AsyncContainer 绑定到 NoneBot Driver 的生命周期。

    在 Driver shutdown 时自动关闭容器，释放 APP 作用域资源
    （如 AsyncEngine 的连接池）。

    :param container: 已组装好的 dishka AsyncContainer
    :type container: AsyncContainer
    :param driver: NoneBot Driver 实例
    :type driver: Driver
    """
    global _container
    _container = container

    @driver.on_shutdown
    async def _shutdown_container() -> None:
        global _container
        await container.close()
        _container = None


def get_container() -> AsyncContainer:
    """
    获取已绑定的 dishka AsyncContainer 实例。

    必须在 ``setup_dishka()`` 调用之后使用（即 NoneBot startup 之后）。

    :returns: 已绑定的 AsyncContainer 实例
    :rtype: AsyncContainer
    :raises RuntimeError: 容器尚未初始化时抛出
    """
    if _container is None:
        raise RuntimeError(
            "dishka 容器尚未初始化，请确保 setup_dishka() 已被调用"
        )
    return _container
