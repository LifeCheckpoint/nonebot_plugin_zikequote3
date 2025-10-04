from typing import List, Dict, Any, Optional
from sqlite3 import Row
import sqlite3

from .base_dao import BaseDAO
from ..models.users import User, UserCreate, UserUpdate


class UserDAO(BaseDAO[User]):
    """
    用户数据访问对象，处理用户相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "users"
    
    @property
    def primary_key(self) -> str:
        return "qq_id"
    
    @property
    def allowed_fields(self) -> List[str]:
        return ["qq_id", "avatar"]
    
    def _row_to_model(self, row: Row) -> User:
        """将数据库行转换为User模型对象"""
        return User(
            qq_id=row["qq_id"],
            avatar=row["avatar"]
        )
    
    def _model_to_dict(self, model: User) -> Dict[str, Any]:
        """将User模型对象转换为字典"""
        return {
            "qq_id": model.qq_id,
            "avatar": model.avatar
        }
    
    def _create_user(self, user_create: UserCreate) -> bool:
        """
        创建新用户（内部方法）
        
        Args:
            user_create: 用户创建模型
            
        Returns:
            bool: 创建是否成功
        """
        sql = "INSERT INTO users (qq_id, avatar) VALUES (?, ?)"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (user_create.qq_id, user_create.avatar))
            return cursor.rowcount > 0

    def create_user(self, qq_id: str, avatar: Optional[bytes] = None) -> bool:
        """
        创建新用户
        
        Args:
            qq_id: QQ号
            avatar: 头像数据（可选）
            
        Returns:
            bool: 创建是否成功
        """
        user_create = UserCreate(qq_id=qq_id, avatar=avatar)
        return self._create_user(user_create)
    
    def get_user_by_qq_id(self, qq_id: str) -> Optional[User]:
        """
        根据QQ号获取用户
        
        Args:
            qq_id: QQ号
            
        Returns:
            Optional[User]: 用户对象或None
        """
        sql = "SELECT * FROM users WHERE qq_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def _update_user(self, qq_id: str, user_update: UserUpdate) -> bool:
        """
        更新用户信息（内部方法）
        
        Args:
            qq_id: QQ号
            user_update: 用户更新模型
            
        Returns:
            bool: 更新是否成功
        """
        if user_update.avatar is None:
            return True  # 没有需要更新的字段
        
        sql = "UPDATE users SET avatar = ? WHERE qq_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (user_update.avatar, qq_id))
            return cursor.rowcount > 0

    def update_user(self, qq_id: str, avatar: Optional[bytes] = None) -> bool:
        """
        更新用户信息
        
        Args:
            qq_id: QQ号
            avatar: 头像数据（可选）
            
        Returns:
            bool: 更新是否成功
        """
        user_update = UserUpdate(avatar=avatar)
        return self._update_user(qq_id, user_update)
    
    def delete_user(self, qq_id: str) -> bool:
        """
        删除用户
        
        Args:
            qq_id: QQ号
            
        Returns:
            bool: 删除是否成功
        """
        sql = "DELETE FROM users WHERE qq_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            return cursor.rowcount > 0
    
    def user_exists(self, qq_id: str) -> bool:
        """
        检查用户是否存在
        
        Args:
            qq_id: QQ号
            
        Returns:
            bool: 用户是否存在
        """
        sql = "SELECT 1 FROM users WHERE qq_id = ? LIMIT 1"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            return cursor.fetchone() is not None
    
    def get_users_by_qq_ids(self, qq_ids: List[str]) -> List[User]:
        """
        根据QQ号列表批量获取用户
        
        Args:
            qq_ids: QQ号列表
            
        Returns:
            List[User]: 用户列表
        """
        if not qq_ids:
            return []
        
        placeholders = ', '.join(['?' for _ in qq_ids])
        sql = f"SELECT * FROM {self.table_name} WHERE qq_id IN ({placeholders})"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, qq_ids)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_users_with_avatar(self) -> List[User]:
        """
        获取有头像的用户列表
        
        Returns:
            List[User]: 有头像的用户列表
        """
        sql = "SELECT * FROM users WHERE avatar IS NOT NULL"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def count_users(self) -> int:
        """
        统计用户总数
        
        Returns:
            int: 用户总数
        """
        sql = "SELECT COUNT(*) FROM users"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def _batch_create_users(self, users: List[UserCreate]) -> bool:
        """
        批量创建用户（内部方法）
        
        Args:
            users: 用户创建模型列表
            
        Returns:
            bool: 批量创建是否成功
        """
        if not users:
            return True
        
        sql = "INSERT INTO users (qq_id, avatar) VALUES (?, ?)"
        values_list = [(user.qq_id, user.avatar) for user in users]
        
        with self.connection_manager.cursor() as cursor:
            cursor.executemany(sql, values_list)
            return cursor.rowcount == len(users)

    def batch_create_users(self, users: List[Dict[str, Any]]) -> bool:
        """
        批量创建用户
        
        Args:
            users: 用户列表，每个用户包含 qq_id 和 avatar（可选）
            
        Returns:
            bool: 批量创建是否成功
        """
        if not users:
            return True
        
        user_creates = []
        for user in users:
            user_creates.append(UserCreate(
                qq_id=user["qq_id"],
                avatar=user.get("avatar")
            ))
        
        return self._batch_create_users(user_creates)
    
    def get_users_without_avatar(self) -> List[User]:
        """
        获取没有头像的用户列表
        
        Returns:
            List[User]: 没有头像的用户列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE avatar IS NULL"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]