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
    
    def _create_permission_group(self, permission_create: PermissionGroupCreate) -> bool:
        """
        创建新权限组（内部方法）
        
        Args:
            permission_create: 权限组创建模型
            
        Returns:
            bool: 创建是否成功
        """
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
            "modify_settings": permission_create.modify_settings,
            "common_operations": permission_create.common_operations,
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

    def create_permission_group(self, group_name: str, be_collected: bool, get_quote: bool,
                               add_quote: bool, search_quote: bool, review_quote: bool,
                               update_quote_self: bool, update_quote_group: bool,
                               delete_review_self: bool, delete_review_group: bool,
                               delete_quote_self: bool, delete_quote_group: bool,
                               modify_settings: bool, common_operations: bool,
                               ban_others: bool, op_others: bool, banop_others: bool,
                               others: bool) -> bool:
        """
        创建新权限组
        
        Args:
            group_name: 权限组名称
            be_collected: 是否可被收集
            get_quote: 是否可获取语录
            add_quote: 是否可添加语录
            search_quote: 是否可搜索语录
            review_quote: 是否可审核语录
            update_quote_self: 是否可更新自己的语录
            update_quote_group: 是否可更新群组语录
            delete_review_self: 是否可删除自己的审核
            delete_review_group: 是否可删除群组审核
            delete_quote_self: 是否可删除自己的语录
            delete_quote_group: 是否可删除群组语录
            modify_settings: 是否可修改设置
            common_operations: 是否可进行常用操作
            ban_others: 是否可封禁他人
            op_others: 是否可操作他人
            banop_others: 是否可封禁操作他人
            others: 其他权限
            
        Returns:
            bool: 创建是否成功
        """
        permission_create = PermissionGroupCreate(
            group_name=group_name,
            be_collected=be_collected,
            get_quote=get_quote,
            add_quote=add_quote,
            search_quote=search_quote,
            review_quote=review_quote,
            update_quote_self=update_quote_self,
            update_quote_group=update_quote_group,
            delete_review_self=delete_review_self,
            delete_review_group=delete_review_group,
            delete_quote_self=delete_quote_self,
            delete_quote_group=delete_quote_group,
            modify_settings=modify_settings,
            common_operations=common_operations,
            ban_others=ban_others,
            op_others=op_others,
            banop_others=banop_others,
            others=others
        )
        return self._create_permission_group(permission_create)
    
    def get_permission_group(self, group_name: str) -> Optional[Dict[str, Any]]:
        """
        根据权限组名获取权限组信息
        
        Args:
            group_name: 权限组名称
            
        Returns:
            Optional[Dict[str, Any]]: 权限组信息或None
        """
        sql = f"SELECT * FROM {self.table_name} WHERE group_name = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_name,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
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
        if permission_update.modify_settings is not None:
            update_data["modify_settings"] = permission_update.modify_settings
        if permission_update.common_operations is not None:
            update_data["common_operations"] = permission_update.common_operations
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
        
        set_clauses = ', '.join([f"{field} = ?" for field in update_data.keys()])
        values = list(update_data.values()) + [group_name]
        sql = f"UPDATE permission_groups SET {set_clauses} WHERE group_name = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0
    
    def delete_permission_group(self, group_name: str) -> bool:
        """
        删除权限组
        
        Args:
            group_name: 权限组名称
            
        Returns:
            bool: 删除是否成功
        """
        sql = "DELETE FROM permission_groups WHERE group_name = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_name,))
            return cursor.rowcount > 0
    
    def get_all_permission_groups(self) -> List[Dict[str, Any]]:
        """
        获取所有权限组
        
        Returns:
            List[Dict[str, Any]]: 权限组列表
        """
        sql = f"SELECT * FROM {self.table_name} ORDER BY group_name"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def check_permission(self, group_name: str, permission_name: str) -> bool:
        """
        检查权限组是否具有指定权限
        
        Args:
            group_name: 权限组名称
            permission_name: 权限名称
            
        Returns:
            bool: 是否具有权限
        """
        sql = f"SELECT {permission_name} FROM {self.table_name} WHERE group_name = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_name,))
            row = cursor.fetchone()
            
            return bool(row[permission_name]) if row else False
    
    def get_groups_with_permission(self, permission_name: str) -> List[str]:
        """
        获取具有指定权限的权限组列表
        
        Args:
            permission_name: 权限名称
            
        Returns:
            List[str]: 权限组名称列表
        """
        sql = f"SELECT group_name FROM {self.table_name} WHERE {permission_name} = 1"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            return [row["group_name"] for row in rows]
    
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
        sql = f"UPDATE permission_groups SET {permission_name} = ? WHERE group_name = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (value, group_name))
            return cursor.rowcount > 0
    
    def permission_group_exists(self, group_name: str) -> bool:
        """
        检查权限组是否存在
        
        Args:
            group_name: 权限组名称
            
        Returns:
            bool: 权限组是否存在
        """
        sql = "SELECT 1 FROM permission_groups WHERE group_name = ? LIMIT 1"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_name,))
            return cursor.fetchone() is not None
    
    def get_permission_summary(self, group_name: str) -> Dict[str, bool]:
        """
        获取权限组的权限汇总
        
        Args:
            group_name: 权限组名称
            
        Returns:
            Dict[str, bool]: 权限汇总
        """
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
    
    def copy_permission_group(self, source_group: str, target_group: str) -> bool:
        """
        复制权限组
        
        Args:
            source_group: 源权限组名称
            target_group: 目标权限组名称
            
        Returns:
            bool: 复制是否成功
        """
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
    