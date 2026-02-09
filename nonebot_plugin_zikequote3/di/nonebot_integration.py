"""
NoneBot2 与 dishka 的桥接层。

由于 dishka 没有官方 NoneBot2 集成，此模块提供：
- setup_dishka(): 将 AsyncContainer 绑定到 NoneBot Driver 生命周期
- inject: 从 dishka 导入的注入装饰器（供 handler 使用）

注意：此模块依赖 NoneBot2 运行时，单元测试中不测试此模块。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dishka import AsyncContainer

if TYPE_CHECKING:
    from nonebot.internal.driver import Driver


def setup_dishka(container: AsyncContainer, driver: "Driver") -> None:
    """
    将 dishka AsyncContainer 绑定到 NoneBot Driver 的生命周期。

    在 Driver shutdown 时自动关闭容器，释放 APP 作用域资源
    （如 AsyncEngine 的连接池）。

    参数:
        container: 已组装好的 dishka AsyncContainer。
        driver: NoneBot Driver 实例。
    """

    @driver.on_shutdown
    async def _shutdown_container() -> None:
        await container.close()
