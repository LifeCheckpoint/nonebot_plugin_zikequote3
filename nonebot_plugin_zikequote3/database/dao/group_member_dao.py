from typing import List, Dict, Any, Optional, Tuple
from sqlite3 import Row
import sqlite3

from .base_dao import BaseDAO
from ..models.group_members import GroupMember, GroupMemberCreate


class GroupMemberDAO(BaseDAO[GroupMember]):
    """
    群成员数据访问对象，处理群成员关系相关的数据库操作
    注意：此表使用复合主键 (group_id, qq_id)
    """
    
    @property
    def table_name(self) -> str:
        return "group_members"
    
    
    def _row_to_model(self, row: Row) -> GroupMember:
        """将数据库行转换为GroupMember模型对象"""
        return GroupMember(
            group_id=row["group_id"],
            qq_id=row["qq_id"],
            permission_group=row["permission_group"]
        )
    
    def _model_to_dict(self, model: GroupMember) -> Dict[str, Any]:
        """将GroupMember模型对象转换为字典"""
        return {
            "group_id": model.group_id,
            "qq_id": model.qq_id,
            "permission_group": model.permission_group
        }
    
    def create_group_member(self, group_member_create: GroupMemberCreate) -> bool:
        """
        创建新群成员关系
        
        Args:
            group_member_create: 群成员创建模型
            
        Returns:
            bool: 创建是否成功
        """
        sql = "INSERT INTO group_members (group_id, qq_id, permission_group) VALUES (?, ?, ?)"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (
                group_member_create.group_id,
                group_member_create.qq_id,
                group_member_create.permission_group
            ))
            return cursor.rowcount > 0
    
    def get_group_member(self, group_id: str, qq_id: str) -> Optional[GroupMember]:
        """
        根据群号和QQ号获取群成员
        
        Args:
            group_id: 群号
            qq_id: QQ号
            
        Returns:
            Optional[GroupMember]: 群成员对象或None
        """
        sql = f"SELECT * FROM {self.table_name} WHERE group_id = ? AND qq_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id, qq_id))
            row = cursor.fetchone()
            
            return self._row_to_model(row) if row else None
    
    def update_group_member_permission(self, group_id: str, qq_id: str, permission_group: str) -> bool:
        """
        更新群成员权限
        
        Args:
            group_id: 群号
            qq_id: QQ号
            permission_group: 权限组
            
        Returns:
            bool: 更新是否成功
        """
        sql = f"UPDATE {self.table_name} SET permission_group = ? WHERE group_id = ? AND qq_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (permission_group, group_id, qq_id))
            return cursor.rowcount > 0
    
    def delete_group_member(self, group_id: str, qq_id: str) -> bool:
        """
        删除群成员关系
        
        Args:
            group_id: 群号
            qq_id: QQ号
            
        Returns:
            bool: 删除是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE group_id = ? AND qq_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id, qq_id))
            return cursor.rowcount > 0
    
    def group_member_exists(self, group_id: str, qq_id: str) -> bool:
        """
        检查群成员关系是否存在
        
        Args:
            group_id: 群号
            qq_id: QQ号
            
        Returns:
            bool: 群成员关系是否存在
        """
        sql = f"SELECT 1 FROM {self.table_name} WHERE group_id = ? AND qq_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id, qq_id))
            return cursor.fetchone() is not None
    
    def get_members_by_group(self, group_id: str) -> List[GroupMember]:
        """
        获取群组的所有成员
        
        Args:
            group_id: 群号
            
        Returns:
            List[GroupMember]: 群成员列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def get_groups_by_user(self, qq_id: str) -> List[GroupMember]:
        """
        获取用户加入的所有群组
        
        Args:
            qq_id: QQ号
            
        Returns:
            List[GroupMember]: 群成员关系列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE qq_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def get_members_by_permission(self, group_id: str, permission_group: str) -> List[GroupMember]:
        """
        根据权限组获取群成员
        
        Args:
            group_id: 群号
            permission_group: 权限组
            
        Returns:
            List[GroupMember]: 群成员列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE group_id = ? AND permission_group = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id, permission_group))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def get_admins_by_group(self, group_id: str) -> List[GroupMember]:
        """
        获取群组的管理员
        
        Args:
            group_id: 群号
            
        Returns:
            List[GroupMember]: 管理员列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE group_id = ? AND permission_group IN ('op', 'root')"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def count_members_by_group(self, group_id: str) -> int:
        """
        统计群组成员数量
        
        Args:
            group_id: 群号
            
        Returns:
            int: 成员数量
        """
        sql = f"SELECT COUNT(*) FROM {self.table_name} WHERE group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def count_groups_by_user(self, qq_id: str) -> int:
        """
        统计用户加入的群组数量
        
        Args:
            qq_id: QQ号
            
        Returns:
            int: 群组数量
        """
        sql = f"SELECT COUNT(*) FROM {self.table_name} WHERE qq_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_group_permission_statistics(self, group_id: str) -> Dict[str, int]:
        """
        获取群组权限分布统计
        
        Args:
            group_id: 群号
            
        Returns:
            Dict[str, int]: 权限分布统计
        """
        sql = f"""
        SELECT permission_group, COUNT(*) as count
        FROM {self.table_name}
        WHERE group_id = ?
        GROUP BY permission_group
        """
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            rows = cursor.fetchall()
            
            result = {}
            for row in rows:
                result[row["permission_group"]] = row["count"]
            
            return result
    
    def batch_add_members(self, group_id: str, qq_ids: List[str], permission_group: str = "normal") -> bool:
        """
        批量添加群成员
        
        Args:
            group_id: 群号
            qq_ids: QQ号列表
            permission_group: 权限组
            
        Returns:
            bool: 批量添加是否成功
        """
        if not qq_ids:
            return True
        
        sql = f"INSERT OR IGNORE INTO {self.table_name} (group_id, qq_id, permission_group) VALUES (?, ?, ?)"
        
        values = [(group_id, qq_id, permission_group) for qq_id in qq_ids]
        
        with self.connection_manager.cursor() as cursor:
            cursor.executemany(sql, values)
            return True
    
    def batch_remove_members(self, group_id: str, qq_ids: List[str]) -> bool:
        """
        批量移除群成员
        
        Args:
            group_id: 群号
            qq_ids: QQ号列表
            
        Returns:
            bool: 批量移除是否成功
        """
        if not qq_ids:
            return True
        
        placeholders = ', '.join(['?' for _ in qq_ids])
        sql = f"DELETE FROM {self.table_name} WHERE group_id = ? AND qq_id IN ({placeholders})"
        params = [group_id] + qq_ids
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            return True
    
    def update_or_create_member(self, group_id: str, qq_id: str, permission_group: str = "normal") -> bool:
        """
        更新或创建群成员关系（如果不存在则创建，存在则更新权限）
        
        Args:
            group_id: 群号
            qq_id: QQ号
            permission_group: 权限组
            
        Returns:
            bool: 操作是否成功
        """
        # 使用 INSERT OR REPLACE 语法
        sql = f"INSERT OR REPLACE INTO {self.table_name} (group_id, qq_id, permission_group) VALUES (?, ?, ?)"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id, qq_id, permission_group))
            return cursor.rowcount > 0
    
    def delete_all_members_by_group(self, group_id: str) -> bool:
        """
        删除群组的所有成员关系
        
        Args:
            group_id: 群号
            
        Returns:
            bool: 删除是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE group_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            return True  # 即使没有删除任何行也返回True
    
    def get_member_permission_group(self, group_id: str, qq_id: str) -> Optional[str]:
        """
        获取指定成员的权限组名称
        
        Args:
            group_id: 群号
            qq_id: QQ号
            
        Returns:
            Optional[str]: 权限组名称，如果不存在则返回None
        """
        member = self.get_group_member(group_id, qq_id)
        return member.permission_group if member else None

    def delete_all_groups_by_user(self, qq_id: str) -> bool:
        """
        删除用户的所有群组关系
        
        Args:
            qq_id: QQ号
            
        Returns:
            bool: 删除是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE qq_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            return True  # 即使没有删除任何行也返回True