from typing import List, Dict, Any, Optional
from sqlite3 import Row
import sqlite3

from .base_dao import BaseDAO
from ..models.permission_groups import PermissionGroup, PermissionGroupCreate, PermissionGroupUpdate


class PermissionGroupDAO(BaseDAO[PermissionGroup]):
    """
    权限组数据访问对象，处理权限组相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "permission_groups"
    
    def _validate_field_name(self, field_name: str) -> bool:
        """验证字段名是否为有效的权限字段"""
        allowed_permissions = [
            "be_collected", "get_quote", "add_quote", "search_quote",
            "review_quote", "update_quote_self", "update_quote_group",
            "delete_review_self", "delete_review_group", "delete_quote_self",
            "delete_quote_group", "ban_others", "op_others", "banop_others", "others"
        ]
        return field_name in allowed_permissions
    
    def _row_to_model(self, row: Row) -> PermissionGroup:
        """将数据库行转换为PermissionGroup模型对象"""
        return PermissionGroup(
            group_name=row["group_name"]
        )
    
    def _model_to_dict(self, model: PermissionGroup) -> Dict[str, Any]:
        """将PermissionGroup模型对象转换为字典"""
        return {
            "group_name": model.group_name
        }
    
    def create_permission_group(self, permission_create: PermissionGroupCreate) -> bool:
        """
        创建新权限组
        
        Args:
            permission_create: 权限组创建模型
            
        Returns:
            bool: 创建是否成功
        """
        try:
            data = {
                "group_name": permission_create.group_name,
                "be_collected": permission_create.be_collected,
                "get_quote": permission_create.get_quote,
                "add_quote": permission_create.add_quote,
                "search_quote": permission_create.search_quote,
                "review_quote": permission_create.review_quote,
                "update_quote_self": permission_create.update_quote_self,
                "update_quote_group": permission_create.update_quote_group,
                "delete_review_self": permission_create.delete_review_self,
                "delete_review_group": permission_create.delete_review_group,
                "delete_quote_self": permission_create.delete_quote_self,
                "delete_quote_group": permission_create.delete_quote_group,
                "ban_others": permission_create.ban_others,
                "op_others": permission_create.op_others,
                "banop_others": permission_create.banop_others,
                "others": permission_create.others
            }
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            values = tuple(data.values())
            
            sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, values)
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            self.logger.error(f"创建权限组失败: {e}")
            return False
    
    def get_permission_group(self, group_name: str) -> Optional[Dict[str, Any]]:
        """
        根据权限组名获取权限组信息
        
        Args:
            group_name: 权限组名称
            
        Returns:
            Optional[Dict[str, Any]]: 权限组信息或None
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE group_name = ?"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (group_name,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            self.logger.error(f"获取权限组失败: {e}")
            return None
    
    def update_permission_group(self, group_name: str, permission_update: PermissionGroupUpdate) -> bool:
        """
        更新权限组信息
        
        Args:
            group_name: 权限组名称
            permission_update: 权限组更新模型
            
        Returns:
            bool: 更新是否成功
        """
        update_data = {}
        
        # 只更新非None的字段
        if permission_update.be_collected is not None:
            update_data["be_collected"] = permission_update.be_collected
        if permission_update.get_quote is not None:
            update_data["get_quote"] = permission_update.get_quote
        if permission_update.add_quote is not None:
            update_data["add_quote"] = permission_update.add_quote
        if permission_update.search_quote is not None:
            update_data["search_quote"] = permission_update.search_quote
        if permission_update.review_quote is not None:
            update_data["review_quote"] = permission_update.review_quote
        if permission_update.update_quote_self is not None:
            update_data["update_quote_self"] = permission_update.update_quote_self
        if permission_update.update_quote_group is not None:
            update_data["update_quote_group"] = permission_update.update_quote_group
        if permission_update.delete_review_self is not None:
            update_data["delete_review_self"] = permission_update.delete_review_self
        if permission_update.delete_review_group is not None:
            update_data["delete_review_group"] = permission_update.delete_review_group
        if permission_update.delete_quote_self is not None:
            update_data["delete_quote_self"] = permission_update.delete_quote_self
        if permission_update.delete_quote_group is not None:
            update_data["delete_quote_group"] = permission_update.delete_quote_group
        if permission_update.ban_others is not None:
            update_data["ban_others"] = permission_update.ban_others
        if permission_update.op_others is not None:
            update_data["op_others"] = permission_update.op_others
        if permission_update.banop_others is not None:
            update_data["banop_others"] = permission_update.banop_others
        if permission_update.others is not None:
            update_data["others"] = permission_update.others
        
        if not update_data:
            return True
        
        try:
            set_clauses = ', '.join([f"{field} = ?" for field in update_data.keys()])
            values = list(update_data.values()) + [group_name]
            sql = f"UPDATE permission_groups SET {set_clauses} WHERE group_name = ?"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, values)
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"更新权限组失败: {e}")
            return False
    
    def delete_permission_group(self, group_name: str) -> bool:
        """
        删除权限组
        
        Args:
            group_name: 权限组名称
            
        Returns:
            bool: 删除是否成功
        """
        try:
            sql = "DELETE FROM permission_groups WHERE group_name = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (group_name,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"删除权限组失败: {e}")
            return False
    
    def get_all_permission_groups(self) -> List[Dict[str, Any]]:
        """
        获取所有权限组
        
        Returns:
            List[Dict[str, Any]]: 权限组列表
        """
        try:
            sql = f"SELECT * FROM {self.table_name} ORDER BY group_name"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            self.logger.error(f"获取所有权限组失败: {e}")
            return []
    
    def check_permission(self, group_name: str, permission_name: str) -> bool:
        """
        检查权限组是否具有指定权限
        
        Args:
            group_name: 权限组名称
            permission_name: 权限名称
            
        Returns:
            bool: 是否具有权限
        """
        try:
            if not self._validate_field_name(permission_name):
                return False
            
            sql = f"SELECT {permission_name} FROM {self.table_name} WHERE group_name = ?"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (group_name,))
                row = cursor.fetchone()
                
                return bool(row[permission_name]) if row else False
                
        except sqlite3.Error as e:
            self.logger.error(f"检查权限失败: {e}")
            return False
    
    def get_groups_with_permission(self, permission_name: str) -> List[str]:
        """
        获取具有指定权限的权限组列表
        
        Args:
            permission_name: 权限名称
            
        Returns:
            List[str]: 权限组名称列表
        """
        try:
            if not self._validate_field_name(permission_name):
                return []
            
            sql = f"SELECT group_name FROM {self.table_name} WHERE {permission_name} = 1"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                
                return [row["group_name"] for row in rows]
                
        except sqlite3.Error as e:
            self.logger.error(f"获取具有权限的组失败: {e}")
            return []
    
    def set_permission(self, group_name: str, permission_name: str, value: bool) -> bool:
        """
        设置权限组的指定权限
        
        Args:
            group_name: 权限组名称
            permission_name: 权限名称
            value: 权限值
            
        Returns:
            bool: 设置是否成功
        """
        if not self._validate_field_name(permission_name):
            return False
        
        try:
            sql = f"UPDATE permission_groups SET {permission_name} = ? WHERE group_name = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (value, group_name))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"设置权限失败: {e}")
            return False
    
    def permission_group_exists(self, group_name: str) -> bool:
        """
        检查权限组是否存在
        
        Args:
            group_name: 权限组名称
            
        Returns:
            bool: 权限组是否存在
        """
        try:
            sql = "SELECT 1 FROM permission_groups WHERE group_name = ? LIMIT 1"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (group_name,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"检查权限组是否存在失败: {e}")
            return False
    
    def get_permission_summary(self, group_name: str) -> Dict[str, bool]:
        """
        获取权限组的权限汇总
        
        Args:
            group_name: 权限组名称
            
        Returns:
            Dict[str, bool]: 权限汇总
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE group_name = ?"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (group_name,))
                row = cursor.fetchone()
                
                if row:
                    # 排除group_name字段，只返回权限字段
                    permissions = dict(row)
                    permissions.pop("group_name", None)
                    return {k: bool(v) for k, v in permissions.items()}
                
                return {}
                
        except sqlite3.Error as e:
            self.logger.error(f"获取权限汇总失败: {e}")
            return {}
    
    def copy_permission_group(self, source_group: str, target_group: str) -> bool:
        """
        复制权限组
        
        Args:
            source_group: 源权限组名称
            target_group: 目标权限组名称
            
        Returns:
            bool: 复制是否成功
        """
        try:
            # 获取源权限组信息
            source_permissions = self.get_permission_group(source_group)
            if not source_permissions:
                return False
            
            # 更改组名
            source_permissions["group_name"] = target_group
            
            # 插入新权限组
            columns = ', '.join(source_permissions.keys())
            placeholders = ', '.join(['?' for _ in source_permissions])
            values = tuple(source_permissions.values())
            
            sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, values)
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            self.logger.error(f"复制权限组失败: {e}")
            return False
    
    def reset_to_default_permissions(self) -> bool:
        """
        重置为默认权限组（重新执行schema中的初始化数据）
        
        Returns:
            bool: 重置是否成功
        """
        # 清空现有权限组
        with self.connection_manager.cursor() as cursor:
            cursor.execute(f"DELETE FROM {self.table_name}")
        
        # 重新插入默认权限组
        default_groups = [
            ('normal',
                True, True, True, True, True,
                True, False, True, False,
                True, False, False, False, False, False),
            ('ban',
                False, False, False, False, False,
                False, False, False, False,
                False, False, False, False, False, False),
            ('ban_cud',
                True, True, False, True, False,
                False, False, False, False,
                False, False, False, False, False, False),
            ('op',
                True, True, True, True, True,
                True, True, True, True,
                True, True, True, False, False, False),
            ('root',
                True, True, True, True, True,
                True, True, True, True,
                True, True, True, True, True, True)
        ]
        
        sql = f"""
        INSERT INTO {self.table_name} (
            group_name, be_collected, get_quote, add_quote, search_quote, review_quote,
            update_quote_self, update_quote_group, delete_review_self, delete_review_group,
            delete_quote_self, delete_quote_group, ban_others, op_others, banop_others, others
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with self.connection_manager.cursor() as cursor:
            cursor.executemany(sql, default_groups)
            return True