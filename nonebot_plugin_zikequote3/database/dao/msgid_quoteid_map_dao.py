from typing import List, Dict, Any, Optional
from sqlite3 import Row
import sqlite3

from .base_dao import BaseDAO
from ..models.msgid_quoteid_map import MsgQuoteID, MsgQuoteIDCreate


class MsgQuoteIDDAO(BaseDAO[MsgQuoteID]):
    """
    消息ID与语录ID映射数据访问对象，处理消息ID与语录ID映射相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "msgid_quoteid_map"
    
    @property
    def primary_key(self) -> str:
        return "msg_id"
    
    @property
    def allowed_fields(self) -> List[str]:
        return ["msg_id", "quote_id"]
    
    def _row_to_model(self, row: Row) -> MsgQuoteID:
        """将数据库行转换为MsgQuoteID模型对象"""
        return MsgQuoteID(
            msg_id=row["msg_id"],
            quote_id=row["quote_id"]
        )
    
    def _model_to_dict(self, model: MsgQuoteID) -> Dict[str, Any]:
        """将MsgQuoteID模型对象转换为字典"""
        return {
            "msg_id": model.msg_id,
            "quote_id": model.quote_id
        }
    
    def create_mapping(self, mapping_create: MsgQuoteIDCreate) -> bool:
        """
        创建新的消息ID与语录ID映射关系
        
        Args:
            mapping_create: 映射关系创建模型
            
        Returns:
            bool: 创建是否成功
        """
        try:
            sql = "INSERT INTO msgid_quoteid_map (msg_id, quote_id) VALUES (?, ?)"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (mapping_create.msg_id, mapping_create.quote_id))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"创建消息ID与语录ID映射失败: {e}")
            return False
    
    def get_mapping_by_msg_id(self, msg_id: str) -> Optional[MsgQuoteID]:
        """
        根据消息ID获取映射关系
        
        Args:
            msg_id: 消息ID
            
        Returns:
            Optional[MsgQuoteID]: 映射关系对象或None
        """
        try:
            sql = "SELECT * FROM msgid_quoteid_map WHERE msg_id = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (msg_id,))
                row = cursor.fetchone()
                return self._row_to_model(row) if row else None
        except sqlite3.Error as e:
            self.logger.error(f"根据消息ID获取映射关系失败: {e}")
            return None
    
    def get_mappings_by_quote_id(self, quote_id: str) -> List[MsgQuoteID]:
        """
        根据语录ID获取所有相关的映射关系
        
        Args:
            quote_id: 语录ID
            
        Returns:
            List[MsgQuoteID]: 映射关系列表
        """
        try:
            sql = "SELECT * FROM msgid_quoteid_map WHERE quote_id = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (quote_id,))
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"根据语录ID获取映射关系失败: {e}")
            return []
    
    def delete_mapping_by_msg_id(self, msg_id: str) -> bool:
        """
        根据消息ID删除映射关系
        
        Args:
            msg_id: 消息ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            sql = "DELETE FROM msgid_quoteid_map WHERE msg_id = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (msg_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"根据消息ID删除映射关系失败: {e}")
            return False
    
    def delete_mappings_by_quote_id(self, quote_id: str) -> bool:
        """
        根据语录ID删除所有相关的映射关系
        
        Args:
            quote_id: 语录ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            sql = "DELETE FROM msgid_quoteid_map WHERE quote_id = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (quote_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"根据语录ID删除映射关系失败: {e}")
            return False
    
    def clear_all_mappings(self) -> bool:
        """
        清空所有映射关系
        
        Returns:
            bool: 清空是否成功
        """
        try:
            sql = "DELETE FROM msgid_quoteid_map"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql)
                return True
        except sqlite3.Error as e:
            self.logger.error(f"清空所有映射关系失败: {e}")
            return False
    
    def mapping_exists(self, msg_id: str) -> bool:
        """
        检查消息ID的映射关系是否存在
        
        Args:
            msg_id: 消息ID
            
        Returns:
            bool: 映射关系是否存在
        """
        try:
            sql = "SELECT 1 FROM msgid_quoteid_map WHERE msg_id = ? LIMIT 1"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (msg_id,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"检查映射关系是否存在失败: {e}")
            return False
    
    def get_mappings_by_msg_ids(self, msg_ids: List[str]) -> List[MsgQuoteID]:
        """
        根据消息ID列表批量获取映射关系
        
        Args:
            msg_ids: 消息ID列表
            
        Returns:
            List[MsgQuoteID]: 映射关系列表
        """
        if not msg_ids:
            return []
        
        try:
            placeholders = ', '.join(['?' for _ in msg_ids])
            sql = f"SELECT * FROM {self.table_name} WHERE msg_id IN ({placeholders})"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, msg_ids)
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"批量获取映射关系失败: {e}")
            return []
    
    def count_mappings_by_quote_id(self, quote_id: str) -> int:
        """
        统计语录ID对应的映射关系数量
        
        Args:
            quote_id: 语录ID
            
        Returns:
            int: 映射关系数量
        """
        try:
            sql = "SELECT COUNT(*) FROM msgid_quoteid_map WHERE quote_id = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (quote_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except sqlite3.Error as e:
            self.logger.error(f"统计映射关系数量失败: {e}")
            return 0
    
    def get_all_mappings(self) -> List[MsgQuoteID]:
        """
        获取所有映射关系
        
        Returns:
            List[MsgQuoteID]: 所有映射关系列表
        """
        try:
            sql = "SELECT * FROM msgid_quoteid_map"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"获取所有映射关系失败: {e}")
            return []
    
    def batch_create_mappings(self, mappings: List[MsgQuoteIDCreate]) -> bool:
        """
        批量创建映射关系
        
        Args:
            mappings: 映射关系创建模型列表
            
        Returns:
            bool: 批量创建是否成功
        """
        if not mappings:
            return True
        
        try:
            sql = "INSERT INTO msgid_quoteid_map (msg_id, quote_id) VALUES (?, ?)"
            values_list = [(mapping.msg_id, mapping.quote_id) for mapping in mappings]
            
            with self.connection_manager.cursor() as cursor:
                cursor.executemany(sql, values_list)
                return cursor.rowcount == len(mappings)
        except sqlite3.Error as e:
            self.logger.error(f"批量创建映射关系失败: {e}")
            return False
    
    def update_or_create_mapping(self, msg_id: str, quote_id: str) -> bool:
        """
        更新或创建映射关系（如果映射关系不存在则创建，存在则更新）
        
        Args:
            msg_id: 消息ID
            quote_id: 语录ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if self.mapping_exists(msg_id):
                # 更新现有映射关系
                sql = "UPDATE msgid_quoteid_map SET quote_id = ? WHERE msg_id = ?"
                with self.connection_manager.cursor() as cursor:
                    cursor.execute(sql, (quote_id, msg_id))
                    return cursor.rowcount > 0
            else:
                # 创建新映射关系
                mapping_create = MsgQuoteIDCreate(msg_id=msg_id, quote_id=quote_id)
                return self.create_mapping(mapping_create)
        except sqlite3.Error as e:
            self.logger.error(f"更新或创建映射关系失败: {e}")
            return False