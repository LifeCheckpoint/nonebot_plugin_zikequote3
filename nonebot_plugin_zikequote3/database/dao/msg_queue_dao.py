from typing import List, Dict, Any, Optional
from sqlite3 import Row
import sqlite3
from datetime import datetime

from .base_dao import BaseDAO
from ..models.msgs_queue import MsgQueue, MsgQueueCreate, MsgQueueUpdate
from ..models.queue_group_message_counts import QueueGroupMessageCount, QueueGroupMessageCountCreate


class MsgQueueDAO(BaseDAO[MsgQueue]):
    """
    消息队列数据访问对象，处理暂存消息相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "msgs_queue"
    
    
    def _row_to_model(self, row: Row) -> MsgQueue:
        """将数据库行转换为MsgQueue模型对象"""
        return MsgQueue(
            msg_id=row["msg_id"],
            group_id=row["group_id"],
            qq_id=row["qq_id"],
            time_stamp=row["time_stamp"],
            content=row["content"]
        )
    
    def _model_to_dict(self, model: MsgQueue) -> Dict[str, Any]:
        """将MsgQueue模型对象转换为字典"""
        return {
            "msg_id": model.msg_id,
            "group_id": model.group_id,
            "qq_id": model.qq_id,
            "time_stamp": model.time_stamp,
            "content": model.content
        }
    
    def _create_msg(self, msg_create: MsgQueueCreate) -> bool:
        """
        创建新的队列消息（内部方法）
        
        Args:
            msg_create: 消息创建模型
            
        Returns:
            bool: 创建是否成功
        """
        sql = "INSERT INTO msgs_queue (msg_id, group_id, qq_id, time_stamp, content) VALUES (?, ?, ?, ?, ?)"
        current_time = datetime.now()
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (
                msg_create.msg_id,
                msg_create.group_id,
                msg_create.qq_id,
                current_time.isoformat(),
                msg_create.content
            ))
            return cursor.rowcount > 0

    def create_msg(self, msg_id: str, group_id: str, qq_id: str, content: str) -> bool:
        """
        创建新的队列消息
        
        Args:
            msg_id: 消息ID
            group_id: 群号
            qq_id: QQ号
            content: 消息内容
            
        Returns:
            bool: 创建是否成功
        """
        msg_create = MsgQueueCreate(
            msg_id=msg_id,
            group_id=group_id,
            qq_id=qq_id,
            content=content
        )
        return self._create_msg(msg_create)
    
    def get_msg_by_id(self, msg_id: str) -> Optional[MsgQueue]:
        """
        根据消息ID获取消息
        
        Args:
            msg_id: 消息ID
            
        Returns:
            Optional[MsgQueue]: 消息对象或None
        """
        sql = "SELECT * FROM msgs_queue WHERE msg_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (msg_id,))
            row = cursor.fetchone()
            
            return self._row_to_model(row) if row else None
    
    def get_msgs_by_group(self, group_id: str, limit: Optional[int] = None, offset: int = 0) -> List[MsgQueue]:
        """
        根据群组获取消息列表，取最后 limit 条
        
        Args:
            group_id: 群号
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[MsgQueue]: 消息列表
        """
        # 这里有一点要注意，我们要获取最后几条，但是获取到的顺序是结果从早到晚
        # 因此我们需要先 LIMIT 再反转顺序
        limitsql = "" if limit is None else f"LIMIT {limit} OFFSET {offset} "
        sql = f"SELECT * FROM ( SELECT * FROM msgs_queue WHERE group_id = ? ORDER BY time_stamp DESC {limitsql}) AS latest_records ORDER BY time_stamp ASC"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_msgs_by_user(self, qq_id: str, limit: Optional[int] = None, offset: int = 0) -> List[MsgQueue]:
        """
        根据用户获取消息列表
        
        Args:
            qq_id: QQ号
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[MsgQueue]: 消息列表
        """
        sql = "SELECT * FROM msgs_queue WHERE qq_id = ? ORDER BY time_stamp"
        
        if limit is not None:
            sql += f" LIMIT {limit} OFFSET {offset}"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (qq_id,))
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_recent_msgs_by_group(self, group_id: str, limit: int = 100) -> List[MsgQueue]:
        """
        获取群组最近的消息
        
        Args:
            group_id: 群号
            limit: 限制返回数量
            
        Returns:
            List[MsgQueue]: 最近消息列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE group_id = ? ORDER BY time_stamp DESC LIMIT ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id, limit))
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def clear_group_queue(self, group_id: str) -> bool:
        """
        清空群组的消息队列
        
        Args:
            group_id: 群号
            
        Returns:
            bool: 清空是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE group_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            return True
    
    def count_msgs_by_group(self, group_id: str) -> int:
        """
        统计群组消息数量
        
        Args:
            group_id: 群号
            
        Returns:
            int: 消息数量
        """
        sql = "SELECT COUNT(*) as count FROM msgs_queue WHERE group_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            row = cursor.fetchone()
            
            return row["count"] if row else 0
    
    def delete_old_msgs(self, days: int = 30) -> bool:
        """
        删除超过指定天数的旧消息
        
        Args:
            days: 保留天数
            
        Returns:
            bool: 删除是否成功
        """
        sql = f"DELETE FROM {self.table_name} WHERE time_stamp < datetime('now', '-{days} days')"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            return True


class QueueGroupMessageCountDAO(BaseDAO[QueueGroupMessageCount]):
    """
    群消息计数数据访问对象，处理群消息计数相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "queue_group_message_counts"
    
    
    def _row_to_model(self, row: Row) -> QueueGroupMessageCount:
        """将数据库行转换为QueueGroupMessageCount模型对象"""
        return QueueGroupMessageCount(
            group_id=row["group_id"],
            message_count=row["message_count"]
        )
    
    def _model_to_dict(self, model: QueueGroupMessageCount) -> Dict[str, Any]:
        """将QueueGroupMessageCount模型对象转换为字典"""
        return {
            "group_id": model.group_id,
            "message_count": model.message_count
        }
    
    def get_group_count(self, group_id: str) -> int:
        """
        获取群组消息计数（如果不存在则创建）
        
        Args:
            group_id: 群号
            
        Returns:
            QueueGroupMessageCount: 群组消息计数对象
        """
        # 先尝试获取现有记录
        sql = "SELECT * FROM queue_group_message_counts WHERE group_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model(row).message_count
            
            # 如果不存在，创建新记录
            insert_sql = "INSERT INTO queue_group_message_counts (group_id, message_count) VALUES (?, ?)"
            cursor.execute(insert_sql, (group_id, 0))
            
            return 0
    
    def increment_count(self, group_id: str) -> int:
        """
        增加群组消息计数
        
        Args:
            group_id: 群号
            
        Returns:
            int: 增加后的计数
        """
        # 使用 INSERT OR REPLACE 确保记录存在
        sql = f"""
        INSERT OR REPLACE INTO {self.table_name} (group_id, message_count)
        VALUES (?, COALESCE((SELECT message_count FROM {self.table_name} WHERE group_id = ?), 0) + 1)
        """
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id, group_id))
            
            # 获取更新后的计数
            cursor.execute(f"SELECT message_count FROM {self.table_name} WHERE group_id = ?", (group_id,))
            row = cursor.fetchone()
            return row["message_count"] if row else 1
    
    def reset_count(self, group_id: str) -> bool:
        """
        重置群组消息计数
        
        Args:
            group_id: 群号
            
        Returns:
            bool: 重置是否成功
        """
        sql = "UPDATE queue_group_message_counts SET message_count = 0 WHERE group_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            return cursor.rowcount > 0
    
    def set_count(self, group_id: str, count: int) -> bool:
        """
        设置群组消息计数
        
        Args:
            group_id: 群号
            count: 计数值
            
        Returns:
            bool: 设置是否成功
        """
        sql = f"INSERT OR REPLACE INTO {self.table_name} (group_id, message_count) VALUES (?, ?)"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id, count))
            return cursor.rowcount > 0
    
    def get_all_counts(self) -> List[QueueGroupMessageCount]:
        """
        获取所有群组的消息计数
        
        Returns:
            List[QueueGroupMessageCount]: 所有群组计数列表
        """
        sql = "SELECT * FROM queue_group_message_counts"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_groups_over_threshold(self, threshold: int) -> List[QueueGroupMessageCount]:
        """
        获取消息计数超过阈值的群组
        
        Args:
            threshold: 阈值
            
        Returns:
            List[QueueGroupMessageCount]: 超过阈值的群组列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE message_count >= ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (threshold,))
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def delete_group_count(self, group_id: str) -> bool:
        """
        删除群组消息计数记录
        
        Args:
            group_id: 群号
            
        Returns:
            bool: 删除是否成功
        """
        sql = "DELETE FROM queue_group_message_counts WHERE group_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            return cursor.rowcount > 0