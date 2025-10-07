"""
DAO模块初始化文件

提供所有DAO类的导入和工厂模式的统一管理
"""

from typing import TYPE_CHECKING

from .base_dao import BaseDAO
from .user_dao import UserDAO
from .group_dao import GroupDAO
from .quote_dao import QuoteDAO
from .review_dao import ReviewDAO
from .group_member_dao import GroupMemberDAO
from .msg_queue_dao import MsgQueueDAO, QueueGroupMessageCountDAO
from .nickname_dao import UserNicknameDAO, GroupNicknameDAO
from .permission_dao import PermissionGroupDAO
from .group_configs_dao import GroupConfigsDAO
from .image_dao import ImageDAO
from .msgid_quoteid_map_dao import MappingDAO

if TYPE_CHECKING:
    from ..connection_manager import ConnectionManager


class DAOFactory:
    """
    DAO工厂类，统一管理所有DAO实例
    """
    
    def __init__(self, connection_manager: "ConnectionManager"):
        """
        初始化DAO工厂
        
        Args:
            connection_manager: 数据库连接管理器
        """
        self.connection_manager = connection_manager
        
        # 初始化所有DAO实例
        self.user_dao = UserDAO(connection_manager)
        self.group_dao = GroupDAO(connection_manager)
        self.quote_dao = QuoteDAO(connection_manager)
        self.review_dao = ReviewDAO(connection_manager)
        self.group_member_dao = GroupMemberDAO(connection_manager)
        self.msg_queue_dao = MsgQueueDAO(connection_manager)
        self.queue_count_dao = QueueGroupMessageCountDAO(connection_manager)
        self.user_nickname_dao = UserNicknameDAO(connection_manager)
        self.group_nickname_dao = GroupNicknameDAO(connection_manager)
        self.permission_dao = PermissionGroupDAO(connection_manager)
        self.group_configs_dao = GroupConfigsDAO(connection_manager)
        self.image_dao = ImageDAO(connection_manager)
        self.mapping_dao = MappingDAO(connection_manager)
    
    def get_user_dao(self) -> UserDAO:
        """获取用户DAO"""
        return self.user_dao
    
    def get_group_dao(self) -> GroupDAO:
        """获取群组DAO"""
        return self.group_dao
    
    def get_quote_dao(self) -> QuoteDAO:
        """获取语录DAO"""
        return self.quote_dao
    
    def get_review_dao(self) -> ReviewDAO:
        """获取评论DAO"""
        return self.review_dao
    
    def get_group_member_dao(self) -> GroupMemberDAO:
        """获取群成员DAO"""
        return self.group_member_dao
    
    def get_msg_queue_dao(self) -> MsgQueueDAO:
        """获取消息队列DAO"""
        return self.msg_queue_dao
    
    def get_queue_count_dao(self) -> QueueGroupMessageCountDAO:
        """获取队列计数DAO"""
        return self.queue_count_dao
    
    def get_user_nickname_dao(self) -> UserNicknameDAO:
        """获取用户昵称DAO"""
        return self.user_nickname_dao
    
    def get_group_nickname_dao(self) -> GroupNicknameDAO:
        """获取群名片DAO"""
        return self.group_nickname_dao
    
    def get_permission_dao(self) -> PermissionGroupDAO:
        """获取权限组DAO"""
        return self.permission_dao
    
    def get_group_configs_dao(self) -> GroupConfigsDAO:
        """获取群配置DAO"""
        return self.group_configs_dao
    
    def get_image_dao(self) -> ImageDAO:
        """获取图片DAO"""
        return self.image_dao

    def get_mapping_dao(self) -> MappingDAO:
        """获取映射DAO"""
        return self.mapping_dao
