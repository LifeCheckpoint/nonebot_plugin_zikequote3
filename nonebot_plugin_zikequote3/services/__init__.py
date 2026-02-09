"""
服务层。

提供业务逻辑的 Service 类，通过 DI 容器注入 Repository 依赖。
"""

from .user_service import UserService
from .group_service import GroupService
from .quote_write_service import QuoteWriteService
from .quote_read_service import QuoteReadService
from .quote_collection_service import QuoteCollectionService
from .review_service import ReviewService
from .statistics_service import StatisticsService
from .config_service import ConfigService
from .migration_service import MigrationService

__all__ = [
    "UserService",
    "GroupService",
    "QuoteWriteService",
    "QuoteReadService",
    "QuoteCollectionService",
    "ReviewService",
    "StatisticsService",
    "ConfigService",
    "MigrationService",
]
