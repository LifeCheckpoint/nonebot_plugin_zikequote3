from typing import List, Dict, Any, Optional
from sqlite3 import Row
import sqlite3

from .base_dao import BaseDAO
from ..models.user_nicknames import UserNickname, UserNicknameCreate
from ..models.group_nicknames import GroupNickname, GroupNicknameCreate


class UserNicknameDAO(BaseDAO[UserNickname]):
    """
    用户昵称数据访问对象，处理用户昵称相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "user_nicknames"
    
    
    def _row_to_model(self, row: Row) -> UserNickname:
        """将数据库行转换为UserNickname模型对象"""
        return UserNickname(
            qq_id=row["qq_id"],
            current_using=bool(row["current_using"]),
            name=row["name"]
        )
    
    def _model_to_dict(self, model: UserNickname) -> Dict[str, Any]:
        """将UserNickname模型对象转换为字典"""
        return {
            "qq_id": model.qq_id,
            "current_using": model.current_using,
            "name": model.name
        }
    
    def add_nickname(self, nickname_create: UserNicknameCreate) -> bool:
        """
        添加用户昵称
        
        Args:
            nickname_create: 昵称创建模型
            
        Returns:
            bool: 添加是否成功
        """
        sql = "INSERT INTO user_nicknames (qq_id, current_using, name) VALUES (?, ?, ?)"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (
                nickname_create.qq_id,
                nickname_create.current_using,
                nickname_create.name
            ))
            return cursor.rowcount > 0
    
    def get_current_nickname(self, qq_id: str) -> Optional[UserNickname]:
        """
        获取用户当前使用的昵称
        
        Args:
            qq_id: QQ号
            
        Returns:
            Optional[UserNickname]: 当前昵称或None
        """
        sql = "SELECT * FROM user_nicknames WHERE qq_id = ? AND current_using = 1"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def get_all_nicknames(self, qq_id: str) -> List[UserNickname]:
        """
        获取用户所有昵称记录
        
        Args:
            qq_id: QQ号
            
        Returns:
            List[UserNickname]: 昵称列表
        """
        sql = "SELECT * FROM user_nicknames WHERE qq_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def set_current_nickname(self, qq_id: str, name: str) -> bool:
        """
        设置用户当前昵称（会取消其他昵称的当前状态）
        
        Args:
            qq_id: QQ号
            name: 昵称
            
        Returns:
            bool: 设置是否成功
        """
        with self.connection_manager.cursor() as cursor:
            # 首先取消所有当前昵称
            cursor.execute(
                f"UPDATE {self.table_name} SET current_using = 0 WHERE qq_id = ?",
                (qq_id,)
            )
            
            # 设置新的当前昵称
            cursor.execute(
                f"UPDATE {self.table_name} SET current_using = 1 WHERE qq_id = ? AND name = ?",
                (qq_id, name)
            )
            
            # 如果没有更新到记录，说明昵称不存在，需要创建
            if cursor.rowcount == 0:
                cursor.execute(
                    f"INSERT INTO {self.table_name} (qq_id, current_using, name) VALUES (?, 1, ?)",
                    (qq_id, name)
                )
            
            return True
    
    def remove_nickname(self, qq_id: str, name: str) -> bool:
        """
        删除指定昵称
        
        Args:
            qq_id: QQ号
            name: 昵称
            
        Returns:
            bool: 删除是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE qq_id = ? AND name = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id, name))
            return cursor.rowcount > 0
    
    def clear_user_nicknames(self, qq_id: str) -> bool:
        """
        清空用户所有昵称
        
        Args:
            qq_id: QQ号
            
        Returns:
            bool: 清空是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE qq_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            return True


class GroupNicknameDAO(BaseDAO[GroupNickname]):
    """
    群名片数据访问对象，处理群名片相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "group_nicknames"
    
    
    def _row_to_model(self, row: Row) -> GroupNickname:
        """将数据库行转换为GroupNickname模型对象"""
        return GroupNickname(
            qq_id=row["qq_id"],
            group_id=row["group_id"],
            current_using=bool(row["current_using"]),
            name=row["name"]
        )
    
    def _model_to_dict(self, model: GroupNickname) -> Dict[str, Any]:
        """将GroupNickname模型对象转换为字典"""
        return {
            "qq_id": model.qq_id,
            "group_id": model.group_id,
            "current_using": model.current_using,
            "name": model.name
        }
    
    def add_group_nickname(self, nickname_create: GroupNicknameCreate) -> bool:
        """
        添加群名片
        
        Args:
            nickname_create: 群名片创建模型
            
        Returns:
            bool: 添加是否成功
        """
        sql = "INSERT INTO group_nicknames (qq_id, group_id, current_using, name) VALUES (?, ?, ?, ?)"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (
                nickname_create.qq_id,
                nickname_create.group_id,
                nickname_create.current_using,
                nickname_create.name
            ))
            return cursor.rowcount > 0
    
    def get_current_group_nickname(self, qq_id: str, group_id: str) -> Optional[GroupNickname]:
        """
        获取用户在群组中当前使用的名片
        
        Args:
            qq_id: QQ号
            group_id: 群号
            
        Returns:
            Optional[GroupNickname]: 当前群名片或None
        """
        sql = "SELECT * FROM group_nicknames WHERE qq_id = ? AND group_id = ? AND current_using = 1"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id, group_id))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def get_all_group_nicknames(self, qq_id: str, group_id: str) -> List[GroupNickname]:
        """
        获取用户在群组中的所有名片记录
        
        Args:
            qq_id: QQ号
            group_id: 群号
            
        Returns:
            List[GroupNickname]: 群名片列表
        """
        sql = "SELECT * FROM group_nicknames WHERE qq_id = ? AND group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id, group_id))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def get_user_all_group_nicknames(self, qq_id: str) -> List[GroupNickname]:
        """
        获取用户在所有群组中的名片记录
        
        Args:
            qq_id: QQ号
            
        Returns:
            List[GroupNickname]: 所有群名片列表
        """
        sql = "SELECT * FROM group_nicknames WHERE qq_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def set_current_group_nickname(self, qq_id: str, group_id: str, name: str) -> bool:
        """
        设置用户在群组中的当前名片（会取消该群组中其他名片的当前状态）
        
        Args:
            qq_id: QQ号
            group_id: 群号
            name: 群名片
            
        Returns:
            bool: 设置是否成功
        """
        with self.connection_manager.cursor() as cursor:
            # 首先取消该群组中的所有当前名片
            cursor.execute(
                f"UPDATE {self.table_name} SET current_using = 0 WHERE qq_id = ? AND group_id = ?",
                (qq_id, group_id)
            )
            
            # 设置新的当前名片
            cursor.execute(
                f"UPDATE {self.table_name} SET current_using = 1 WHERE qq_id = ? AND group_id = ? AND name = ?",
                (qq_id, group_id, name)
            )
            
            # 如果没有更新到记录，说明名片不存在，需要创建
            if cursor.rowcount == 0:
                cursor.execute(
                    f"INSERT INTO {self.table_name} (qq_id, group_id, current_using, name) VALUES (?, ?, 1, ?)",
                    (qq_id, group_id, name)
                )
            
            return True
    
    def remove_group_nickname(self, qq_id: str, group_id: str, name: str) -> bool:
        """
        删除指定群名片
        
        Args:
            qq_id: QQ号
            group_id: 群号
            name: 群名片
            
        Returns:
            bool: 删除是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE qq_id = ? AND group_id = ? AND name = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id, group_id, name))
            return cursor.rowcount > 0
    
    def clear_user_group_nicknames(self, qq_id: str, group_id: str) -> bool:
        """
        清空用户在指定群组中的所有名片
        
        Args:
            qq_id: QQ号
            group_id: 群号
            
        Returns:
            bool: 清空是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE qq_id = ? AND group_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id, group_id))
            return True
    
    def clear_group_all_nicknames(self, group_id: str) -> bool:
        """
        清空群组中所有用户的名片
        
        Args:
            group_id: 群号
            
        Returns:
            bool: 清空是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE group_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            return True
    
    def get_group_nickname_statistics(self, group_id: str) -> Dict[str, Any]:
        """
        获取群组名片统计信息
        
        Args:
            group_id: 群号
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        sql = f"""
        SELECT
            COUNT(*) as total_nicknames,
            COUNT(DISTINCT qq_id) as users_with_nicknames,
            COUNT(CASE WHEN current_using = 1 THEN 1 END) as current_nicknames
        FROM {self.table_name}
        WHERE group_id = ?
        """
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "total_nicknames": row["total_nicknames"],
                    "users_with_nicknames": row["users_with_nicknames"],
                    "current_nicknames": row["current_nicknames"]
                }
            else:
                return {
                    "total_nicknames": 0,
                    "users_with_nicknames": 0,
                    "current_nicknames": 0
                }