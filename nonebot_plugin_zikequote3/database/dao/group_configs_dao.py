from typing import List, Dict, Any, Optional
from sqlite3 import Row
import sqlite3

from .base_dao import BaseDAO
from ..models.group_configs import GroupConfigs, GroupConfigsCreate, GroupConfigsUpdate


class GroupConfigsDAO(BaseDAO[GroupConfigs]):
    """
    群自定义配置数据访问对象，处理群自定义配置相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "group_configs"
    
    @property
    def primary_key(self) -> str:
        return "group_id"
    
    @property
    def allowed_fields(self) -> List[str]:
        return ["group_id", "toml_config"]
    
    def _row_to_model(self, row: Row) -> GroupConfigs:
        """将数据库行转换为GroupConfigs模型对象"""
        return GroupConfigs(
            group_id=row["group_id"],
            toml_config=row["toml_config"]
        )
    
    def _model_to_dict(self, model: GroupConfigs) -> Dict[str, Any]:
        """将GroupConfigs模型对象转换为字典"""
        return {
            "group_id": model.group_id,
            "toml_config": model.toml_config
        }
    
    def _create_group_config(self, config_create: GroupConfigsCreate) -> bool:
        """
        创建群自定义配置（内部方法）
        
        Args:
            config_create: 群配置创建模型
            
        Returns:
            bool: 创建是否成功
        """
        sql = "INSERT INTO group_configs (group_id, toml_config) VALUES (?, ?)"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (config_create.group_id, config_create.toml_config))
            return cursor.rowcount > 0

    def create_group_config(self, group_id: str, toml_config: str) -> bool:
        """
        创建群自定义配置
        
        Args:
            group_id: 群号
            toml_config: TOML配置内容
            
        Returns:
            bool: 创建是否成功
        """
        config_create = GroupConfigsCreate(group_id=group_id, toml_config=toml_config)
        return self._create_group_config(config_create)
    
    def get_group_config_by_id(self, group_id: str) -> Optional[GroupConfigs]:
        """
        根据群号获取群自定义配置
        
        Args:
            group_id: 群号
            
        Returns:
            Optional[GroupConfigs]: 群配置对象或None
        """
        sql = "SELECT * FROM group_configs WHERE group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def _update_group_config(self, group_id: str, config_update: GroupConfigsUpdate) -> bool:
        """
        更新群自定义配置（内部方法）
        
        Args:
            group_id: 群号
            config_update: 群配置更新模型
            
        Returns:
            bool: 更新是否成功
        """
        if config_update.toml_config is None:
            return True  # 没有需要更新的字段
        
        sql = "UPDATE group_configs SET toml_config = ? WHERE group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (config_update.toml_config, group_id))
            return cursor.rowcount > 0

    def update_group_config(self, group_id: str, toml_config: str) -> bool:
        """
        更新群自定义配置
        
        Args:
            group_id: 群号
            toml_config: TOML配置内容
            
        Returns:
            bool: 更新是否成功
        """
        config_update = GroupConfigsUpdate(toml_config=toml_config)
        return self._update_group_config(group_id, config_update)
    
    def delete_group_config(self, group_id: str) -> bool:
        """
        删除群自定义配置
        
        Args:
            group_id: 群号
            
        Returns:
            bool: 删除是否成功
        """
        sql = "DELETE FROM group_configs WHERE group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            return cursor.rowcount > 0
    
    def group_config_exists(self, group_id: str) -> bool:
        """
        检查群自定义配置是否存在
        
        Args:
            group_id: 群号
            
        Returns:
            bool: 群配置是否存在
        """
        sql = "SELECT 1 FROM group_configs WHERE group_id = ? LIMIT 1"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            return cursor.fetchone() is not None
    
    def get_group_configs_by_ids(self, group_ids: List[str]) -> List[GroupConfigs]:
        """
        根据群号列表批量获取群自定义配置
        
        Args:
            group_ids: 群号列表
            
        Returns:
            List[GroupConfigs]: 群配置列表
        """
        if not group_ids:
            return []
        
        placeholders = ', '.join(['?' for _ in group_ids])
        sql = f"SELECT * FROM {self.table_name} WHERE group_id IN ({placeholders})"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, group_ids)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_all_group_configs(self) -> List[GroupConfigs]:
        """
        获取所有群自定义配置
        
        Returns:
            List[GroupConfigs]: 群配置列表
        """
        sql = "SELECT * FROM group_configs ORDER BY group_id"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def count_group_configs(self) -> int:
        """
        统计群自定义配置总数
        
        Returns:
            int: 群配置总数
        """
        sql = "SELECT COUNT(*) FROM group_configs"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def _batch_create_group_configs(self, configs: List[GroupConfigsCreate]) -> bool:
        """
        批量创建群自定义配置（内部方法）
        
        Args:
            configs: 群配置创建模型列表
            
        Returns:
            bool: 批量创建是否成功
        """
        if not configs:
            return True
        
        sql = "INSERT INTO group_configs (group_id, toml_config) VALUES (?, ?)"
        values_list = [(config.group_id, config.toml_config) for config in configs]
        
        with self.connection_manager.cursor() as cursor:
            cursor.executemany(sql, values_list)
            return cursor.rowcount == len(configs)

    def batch_create_group_configs(self, configs: List[Dict[str, str]]) -> bool:
        """
        批量创建群自定义配置
        
        Args:
            configs: 群配置列表，每个配置包含 group_id 和 toml_config
            
        Returns:
            bool: 批量创建是否成功
        """
        if not configs:
            return True
        
        config_creates = [GroupConfigsCreate(group_id=config["group_id"], toml_config=config["toml_config"])
                         for config in configs]
        return self._batch_create_group_configs(config_creates)
    
    def update_or_create_group_config(self, group_id: str, toml_config: str) -> bool:
        """
        更新或创建群自定义配置（如果配置不存在则创建，存在则更新）
        
        Args:
            group_id: 群号
            toml_config: TOML配置内容
            
        Returns:
            bool: 操作是否成功
        """
        if self.group_config_exists(group_id):
            return self.update_group_config(group_id, toml_config)
        else:
            return self.create_group_config(group_id, toml_config)
    
    def get_toml_config_by_group_id(self, group_id: str) -> Optional[str]:
        """
        根据群号获取TOML配置内容
        
        Args:
            group_id: 群号
            
        Returns:
            Optional[str]: TOML配置内容或None
        """
        sql = "SELECT toml_config FROM group_configs WHERE group_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            row = cursor.fetchone()
            return row["toml_config"] if row else None
    
    def set_toml_config(self, group_id: str, toml_config: str) -> bool:
        """
        设置群TOML配置内容
        
        Args:
            group_id: 群号
            toml_config: TOML配置内容
            
        Returns:
            bool: 设置是否成功
        """
        return self.update_or_create_group_config(group_id, toml_config)