"""
重构后的服务层（第一批）：UserService 和 GroupService。

使用 ``services/new/`` 子目录避免与现有服务冲突，后续清理阶段再移动。
"""

from .user_service import UserService
from .group_service import GroupService

__all__ = ["UserService", "GroupService"]
