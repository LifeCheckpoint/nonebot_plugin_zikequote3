"""
Service 层的 dishka Provider。

后续子任务 9-12 会在此注册各 Service 类。
"""

from dishka import Provider


class ServiceProvider(Provider):
    """
    Service 依赖提供者（骨架）。

    当前为空，后续子任务会逐步添加：
    - QuoteService
    - UserService
    - ConfigService
    - 等等
    """
