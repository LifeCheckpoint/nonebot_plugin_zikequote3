from typing import List, Dict, Any, Optional
from sqlite3 import Row
import sqlite3

from .base_dao import BaseDAO
from ..models.groups import Group, GroupCreate, GroupUpdate


class GroupDAO(BaseDAO[Group]):
    """
    群组数据访问对象，处理群组相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "groups"
    
    @property
    def primary_key(self) -> str:
        return "group_id"
    
    @property
    def allowed_fields(self) -> List[str]:
        return ["group_id", "name"]
    
    def _row_to_model(self, row: Row) -> Group:
        """将数据库行转换为Group模型对象"""
        return Group(
            group_id=row["group_id"],
            name=row["name"]
        )
    
    def _model_to_dict(self, model: Group) -> Dict[str, Any]:
        """将Group模型对象转换为字典"""
        return {
            "group_id": model.group_id,
            "name": model.name
        }
    
    def _create_group(self, group_create: GroupCreate) -> bool:
        """
        创建新群组（内部方法）
        
        Args:
            group_create: 群组创建模型
            
        Returns:
            bool: 创建是否成功
        """
        sql = "INSERT INTO groups (group_id, name) VALUES (?, ?)"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_create.group_id, group_create.name))
            return cursor.rowcount > 0

    def create_group(self, group_id: str, name: str) -> bool:
        """
        创建新群组
        
        Args:
            group_id: 群号
            name: 群名称
            
        Returns:
            bool: 创建是否成功
        """
        group_create = GroupCreate(group_id=group_id, name=name)
        return self._create_group(group_create)
    
    def get_group_by_id(self, group_id: str) -> Optional[Group]:
        """
        根据群号获取群组
        
        Args:
            group_id: 群号
            
        Returns:
            Optional[Group]: 群组对象或None
        """
        sql = "SELECT * FROM groups WHERE group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def _update_group(self, group_id: str, group_update: GroupUpdate) -> bool:
        """
        更新群组信息（内部方法）
        
        Args:
            group_id: 群号
            group_update: 群组更新模型
            
        Returns:
            bool: 更新是否成功
        """
        if group_update.name is None:
            return True  # 没有需要更新的字段
        
        sql = "UPDATE groups SET name = ? WHERE group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_update.name, group_id))
            return cursor.rowcount > 0

    def update_group(self, group_id: str, name: str) -> bool:
        """
        更新群组信息
        
        Args:
            group_id: 群号
            name: 群名称
            
        Returns:
            bool: 更新是否成功
        """
        group_update = GroupUpdate(name=name)
        return self._update_group(group_id, group_update)
    
    def delete_group(self, group_id: str) -> bool:
        """
        删除群组
        
        Args:
            group_id: 群号
            
        Returns:
            bool: 删除是否成功
        """
        sql = "DELETE FROM groups WHERE group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            return cursor.rowcount > 0
    
    def group_exists(self, group_id: str) -> bool:
        """
        检查群组是否存在
        
        Args:
            group_id: 群号
            
        Returns:
            bool: 群组是否存在
        """
        sql = "SELECT 1 FROM groups WHERE group_id = ? LIMIT 1"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            return cursor.fetchone() is not None
    
    def find_groups_by_name(self, name: str) -> List[Group]:
        """
        根据群名称查找群组（精确匹配）
        
        Args:
            name: 群名称
            
        Returns:
            List[Group]: 群组列表
        """
        sql = "SELECT * FROM groups WHERE name = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (name,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def search_groups_by_name_like(self, name_pattern: str) -> List[Group]:
        """
        根据群名称模糊搜索群组
        
        Args:
            name_pattern: 群名称模式（支持%通配符）
            
        Returns:
            List[Group]: 群组列表
        """
        sql = "SELECT * FROM groups WHERE name LIKE ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (name_pattern,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def get_groups_by_ids(self, group_ids: List[str]) -> List[Group]:
        """
        根据群号列表批量获取群组
        
        Args:
            group_ids: 群号列表
            
        Returns:
            List[Group]: 群组列表
        """
        if not group_ids:
            return []
        
        placeholders = ', '.join(['?' for _ in group_ids])
        sql = f"SELECT * FROM {self.table_name} WHERE group_id IN ({placeholders})"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, group_ids)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_all_groups_ordered_by_name(self) -> List[Group]:
        """
        获取所有群组，按名称排序
        
        Returns:
            List[Group]: 按名称排序的群组列表
        """
        sql = "SELECT * FROM groups ORDER BY name"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def count_groups(self) -> int:
        """
        统计群组总数
        
        Returns:
            int: 群组总数
        """
        sql = "SELECT COUNT(*) FROM groups"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def _batch_create_groups(self, groups: List[GroupCreate]) -> bool:
        """
        批量创建群组（内部方法）
        
        Args:
            groups: 群组创建模型列表
            
        Returns:
            bool: 批量创建是否成功
        """
        if not groups:
            return True
        
        sql = "INSERT INTO groups (group_id, name) VALUES (?, ?)"
        values_list = [(group.group_id, group.name) for group in groups]
        
        with self.connection_manager.cursor() as cursor:
            cursor.executemany(sql, values_list)
            return cursor.rowcount == len(groups)

    def batch_create_groups(self, groups: List[Dict[str, str]]) -> bool:
        """
        批量创建群组
        
        Args:
            groups: 群组列表，每个群组包含 group_id 和 name
            
        Returns:
            bool: 批量创建是否成功
        """
        if not groups:
            return True
        
        group_creates = [GroupCreate(group_id=group["group_id"], name=group["name"])
                        for group in groups]
        return self._batch_create_groups(group_creates)
    
    def get_groups_with_name_containing(self, keyword: str) -> List[Group]:
        """
        获取群名称包含指定关键词的群组
        
        Args:
            keyword: 关键词
            
        Returns:
            List[Group]: 群组列表
        """
        pattern = f"%{keyword}%"
        return self.search_groups_by_name_like(pattern)
    
    def update_or_create_group(self, group_id: str, name: str) -> bool:
        """
        更新或创建群组（如果群组不存在则创建，存在则更新名称）
        
        Args:
            group_id: 群号
            name: 群名称
            
        Returns:
            bool: 操作是否成功
        """
        if self.group_exists(group_id):
            return self.update_group(group_id, name)
        else:
            return self.create_group(group_id, name)