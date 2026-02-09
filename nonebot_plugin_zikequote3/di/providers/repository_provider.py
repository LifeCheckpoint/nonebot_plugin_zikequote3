"""
Repository 层的 dishka Provider。

后续子任务 6-8 会在此注册各 Repository 类。
"""

from dishka import Provider


class RepositoryProvider(Provider):
    """
    Repository 依赖提供者（骨架）。

    当前为空，后续子任务会逐步添加：
    - QuoteRepository
    - UserRepository
    - GroupRepository
    - 等等
    """
