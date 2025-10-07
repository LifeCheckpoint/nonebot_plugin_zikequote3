from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Generic, TypeVar

T = TypeVar("T")

if TYPE_CHECKING:
    from ..connection_manager import ConnectionManager

class BaseDAO(Generic[T]):
    """
    数据访问对象基类
    """
    def __init__(self, connection_manager: "ConnectionManager"):
        """
        初始化 BaseDAO
        
        Args:
            connection_manager: 数据库连接管理器
        """
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(self.__class__.__name__)

