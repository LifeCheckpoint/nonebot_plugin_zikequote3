from typing import List, Dict, Any, Optional
from sqlite3 import Row
from datetime import datetime
import sqlite3

from .base_dao import BaseDAO
from ..models.quotes import Quote, QuoteCreate, QuoteUpdate


class QuoteDAO(BaseDAO[Quote]):
    """
    语录数据访问对象，处理语录相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "quotes"
    
    def _row_to_model(self, row: Row) -> Quote:
        """将数据库行转换为Quote模型对象"""
        return Quote(
            quote_id=row["quote_id"],
            time_stamp=row["time_stamp"],
            author_id=row["author_id"],
            group_id=row["group_id"],
            content=row["content"],
            image_content_uuid=row["image_content_uuid"],
            total_show_time=row["total_show_time"]
        )
    
    def _model_to_dict(self, model: Quote) -> Dict[str, Any]:
        """将Quote模型对象转换为字典"""
        return {
            "quote_id": model.quote_id,
            "time_stamp": model.time_stamp,
            "author_id": model.author_id,
            "group_id": model.group_id,
            "content": model.content,
            "image_content_uuid": model.image_content_uuid,
            "total_show_time": model.total_show_time
        }
    
    def _create_quote(self, quote_create: QuoteCreate) -> bool:
        """
        创建新语录（内部方法）
        
        Args:
            quote_create: 语录创建模型
            
        Returns:
            bool: 创建是否成功
        """
        sql = """
        INSERT INTO quotes (quote_id, time_stamp, author_id, group_id, content, image_content_uuid, total_show_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            quote_create.quote_id,
            datetime.now().isoformat(),
            quote_create.author_id,
            quote_create.group_id,
            quote_create.content,
            quote_create.image_content_uuid,
            quote_create.total_show_time
        )
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    def create_quote(self, quote_id: str, author_id: str, group_id: str, content: str,
                    image_content_uuid: Optional[str] = None, total_show_time: int = 0) -> bool:
        """
        创建新语录
        
        Args:
            quote_id: 语录ID
            author_id: 作者QQ号
            group_id: 群号
            content: 语录内容
            image_content_uuid: 图片内容UUID（可选）
            total_show_time: 总展示次数（默认0）
            
        Returns:
            bool: 创建是否成功
        """
        quote_create = QuoteCreate(
            quote_id=quote_id,
            author_id=author_id,
            group_id=group_id,
            content=content,
            image_content_uuid=image_content_uuid,
            total_show_time=total_show_time
        )
        return self._create_quote(quote_create)
    
    def get_quote_by_id(self, quote_id: str) -> Optional[Quote]:
        """
        根据语录ID获取语录
        
        Args:
            quote_id: 语录ID
            
        Returns:
            Optional[Quote]: 语录对象或None
        """
        sql = "SELECT * FROM quotes WHERE quote_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (quote_id,))
            row = cursor.fetchone()
            
            return self._row_to_model(row) if row else None
    
    def _update_quote(self, quote_id: str, quote_update: QuoteUpdate) -> bool:
        """
        更新语录信息（内部方法）
        
        Args:
            quote_id: 语录ID
            quote_update: 语录更新模型
            
        Returns:
            bool: 更新是否成功
        """
        update_parts = []
        params = []
        
        if quote_update.content is not None:
            update_parts.append("content = ?")
            params.append(quote_update.content)
        if quote_update.image_content_uuid is not None:
            update_parts.append("image_content_uuid = ?")
            params.append(quote_update.image_content_uuid)
        if quote_update.total_show_time is not None:
            update_parts.append("total_show_time = ?")
            params.append(quote_update.total_show_time)
        
        if not update_parts:
            return True
        
        sql = f"UPDATE quotes SET {', '.join(update_parts)} WHERE quote_id = ?"
        params.append(quote_id)
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    def update_quote(self, quote_id: str, content: Optional[str] = None,
                    image_content_uuid: Optional[str] = None, total_show_time: Optional[int] = None) -> bool:
        """
        更新语录信息
        
        Args:
            quote_id: 语录ID
            content: 语录内容（可选）
            image_content_uuid: 图片内容UUID（可选）
            total_show_time: 总展示次数（可选）
            
        Returns:
            bool: 更新是否成功
        """
        quote_update = QuoteUpdate(
            content=content,
            image_content_uuid=image_content_uuid,
            total_show_time=total_show_time
        )
        return self._update_quote(quote_id, quote_update)
    
    def delete_quote(self, quote_id: str) -> bool:
        """
        删除语录
        
        Args:
            quote_id: 语录ID
            
        Returns:
            bool: 删除是否成功
        """
        sql = "DELETE FROM quotes WHERE quote_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (quote_id,))
            return cursor.rowcount > 0
    
    def get_quotes_by_group(self, group_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Quote]:
        """
        根据群组获取语录列表
        
        Args:
            group_id: 群号
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Quote]: 语录列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE group_id = ? ORDER BY time_stamp"
        params: List[Any] = [group_id]
        
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_quotes_by_author(self, author_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Quote]:
        """
        根据作者获取语录列表
        
        Args:
            author_id: 作者QQ号
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Quote]: 语录列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE author_id = ? ORDER BY time_stamp"
        params: List[Any] = [author_id]
        
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
        
    def check_quote_exists_by_author_content(self, author_id: str, content: str) -> bool:
        """
        检查指定作者和内容的语录是否存在
        
        Args:
            author_id: 作者QQ号
            content: 语录内容
            
        Returns:
            bool: 是否存在
        """
        sql = f"SELECT 1 FROM {self.table_name} WHERE author_id = ? AND content = ? LIMIT 1"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (author_id, content))
            return cursor.fetchone() is not None
    
    def get_quotes_by_group_and_author(self, group_id: str, author_id: str,
                                     limit: Optional[int] = None, offset: int = 0) -> List[Quote]:
        """
        根据群组和作者获取语录列表
        
        Args:
            group_id: 群号
            author_id: 作者QQ号
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Quote]: 语录列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE group_id = ? AND author_id = ? ORDER BY time_stamp"
        params: List[Any] = [group_id, author_id]
        
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def search_quotes_by_content(self, keyword: str, group_id: Optional[str] = None, 
                               limit: Optional[int] = None, offset: int = 0) -> List[Quote]:
        """
        根据内容关键词搜索语录
        
        Args:
            keyword: 搜索关键词
            group_id: 可选的群号过滤
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Quote]: 语录列表
        """
        pattern = f"%{keyword}%"
        
        if group_id:
            sql = f"SELECT * FROM {self.table_name} WHERE content LIKE ? AND group_id = ? ORDER BY time_stamp DESC"
            params: List[Any] = [pattern, group_id]
        else:
            sql = f"SELECT * FROM {self.table_name} WHERE content LIKE ? ORDER BY time_stamp DESC"
            params: List[Any] = [pattern]
        
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_popular_quotes(self, group_id: Optional[str] = None, 
                         limit: Optional[int] = None, offset: int = 0) -> List[Quote]:
        """
        获取热门语录（按展示次数排序）
        
        Args:
            group_id: 可选的群号过滤
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Quote]: 热门语录列表
        """
        if group_id:
            sql = f"SELECT * FROM {self.table_name} WHERE group_id = ? ORDER BY total_show_time DESC"
            params: List[Any] = [group_id]
        else:
            sql = f"SELECT * FROM {self.table_name} ORDER BY total_show_time DESC"
            params: List[Any] = []
        
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_recent_quotes(self, group_id: Optional[str] = None, 
                        limit: Optional[int] = None, offset: int = 0) -> List[Quote]:
        """
        获取最近的语录（按时间排序）
        
        Args:
            group_id: 可选的群号过滤
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Quote]: 最近语录列表
        """
        if group_id:
            sql = f"SELECT * FROM {self.table_name} WHERE group_id = ? ORDER BY time_stamp DESC"
            params: List[Any] = [group_id]
        else:
            sql = f"SELECT * FROM {self.table_name} ORDER BY time_stamp DESC"
            params: List[Any] = []
        
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def increment_show_time(self, quote_id: str) -> bool:
        """
        增加语录展示次数
        
        Args:
            quote_id: 语录ID
            
        Returns:
            bool: 更新是否成功
        """
        sql = f"UPDATE {self.table_name} SET total_show_time = total_show_time + 1 WHERE quote_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (quote_id,))
            return cursor.rowcount > 0
    
    def count_quotes_by_group(self, group_id: str) -> int:
        """
        统计群组语录数量
        
        Args:
            group_id: 群号
            
        Returns:
            int: 语录数量
        """
        sql = f"SELECT COUNT(*) FROM {self.table_name} WHERE group_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def count_quotes_by_author(self, author_id: str) -> int:
        """
        统计作者语录数量
        
        Args:
            author_id: 作者QQ号
            
        Returns:
            int: 语录数量
        """
        sql = f"SELECT COUNT(*) FROM {self.table_name} WHERE author_id = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (author_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_quote_statistics_by_group(self, group_id: str) -> Dict[str, Any]:
        """
        获取群组语录统计信息
        
        Args:
            group_id: 群号
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        sql = f"""
        SELECT
            COUNT(*) as total_quotes,
            COUNT(DISTINCT author_id) as unique_authors,
            SUM(total_show_time) as total_shows,
            AVG(total_show_time) as avg_shows
        FROM {self.table_name}
        WHERE group_id = ?
        """
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (group_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "total_quotes": row["total_quotes"],
                    "unique_authors": row["unique_authors"],
                    "total_shows": row["total_shows"] or 0,
                    "avg_shows": round(row["avg_shows"] or 0, 2)
                }
            else:
                return {
                    "total_quotes": 0,
                    "unique_authors": 0,
                    "total_shows": 0,
                    "avg_shows": 0
                }
    
    def get_random_quote(self, group_id: Optional[str] = None) -> Optional[Quote]:
        """
        获取随机语录
        
        Args:
            group_id: 可选的群号过滤
            
        Returns:
            Optional[Quote]: 随机语录或None
        """
        if group_id:
            sql = f"SELECT * FROM {self.table_name} WHERE group_id = ? ORDER BY RANDOM() LIMIT 1"
            params = [group_id]
        else:
            sql = f"SELECT * FROM {self.table_name} ORDER BY RANDOM() LIMIT 1"
            params = []
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            
            return self._row_to_model(row) if row else None
    
    def batch_create_quotes(self, quotes: List[QuoteCreate]) -> bool:
        """
        批量创建语录
        
        Args:
            quotes: 语录创建模型列表
            
        Returns:
            bool: 批量创建是否成功
        """
        if not quotes:
            return True
        
        sql = """
        INSERT INTO quotes (quote_id, time_stamp, author_id, group_id, content, image_content_uuid, total_show_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        values_list = []
        for quote in quotes:
            values_list.append((
                quote.quote_id,
                datetime.now(),
                quote.author_id,
                quote.group_id,
                quote.content,
                quote.image_content_uuid,
                quote.total_show_time
            ))
        
        with self.connection_manager.cursor() as cursor:
            cursor.executemany(sql, values_list)
            return cursor.rowcount == len(quotes)