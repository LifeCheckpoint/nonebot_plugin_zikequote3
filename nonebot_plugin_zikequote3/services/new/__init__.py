"""
重构后的服务层。

使用 ``services/new/`` 子目录避免与现有服务冲突，后续清理阶段再移动。
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
