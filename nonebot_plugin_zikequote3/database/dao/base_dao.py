from typing import Generic, TypeVar
import logging

from ..connection_manager import ConnectionManager

T = TypeVar('T')

class BaseDAO(Generic[T]):
    """
    数据访问对象基类
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        """
        初始化 BaseDAO
        
        Args:
            connection_manager: 数据库连接管理器
        """
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(self.__class__.__name__)