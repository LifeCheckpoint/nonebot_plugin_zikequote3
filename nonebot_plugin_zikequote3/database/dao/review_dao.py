from typing import List, Dict, Any, Optional
from sqlite3 import Row
from datetime import datetime
import sqlite3

from .base_dao import BaseDAO
from ..models.reviews import Review, ReviewCreate, ReviewUpdate


class ReviewDAO(BaseDAO[Review]):
    """
    评论数据访问对象，处理评论相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "reviews"
    
    
    def _row_to_model(self, row: Row) -> Review:
        """将数据库行转换为Review模型对象"""
        return Review(
            review_id=row["review_id"],
            time_stamp=row["time_stamp"],
            author_id=row["author_id"],
            quote_id=row["quote_id"],
            content=row["content"]
        )
    
    def _model_to_dict(self, model: Review) -> Dict[str, Any]:
        """将Review模型对象转换为字典"""
        return {
            "review_id": model.review_id,
            "time_stamp": model.time_stamp,
            "author_id": model.author_id,
            "quote_id": model.quote_id,
            "content": model.content
        }
    
    def create_review(self, review_create: ReviewCreate) -> bool:
        """
        创建新评论
        
        Args:
            review_create: 评论创建模型
            
        Returns:
            bool: 创建是否成功
        """
        sql = "INSERT INTO reviews (review_id, time_stamp, author_id, quote_id, content) VALUES (?, ?, ?, ?, ?)"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (
                review_create.review_id,
                datetime.now().isoformat(),
                review_create.author_id,
                review_create.quote_id,
                review_create.content
            ))
            return cursor.rowcount > 0
    
    def get_review_by_id(self, review_id: str) -> Optional[Review]:
        """
        根据评论ID获取评论
        
        Args:
            review_id: 评论ID
            
        Returns:
            Optional[Review]: 评论对象或None
        """
        sql = "SELECT * FROM reviews WHERE review_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (review_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def update_review(self, review_id: str, review_update: ReviewUpdate) -> bool:
        """
        更新评论内容
        
        Args:
            review_id: 评论ID
            review_update: 评论更新模型
            
        Returns:
            bool: 更新是否成功
        """
        if review_update.content is None:
            return True
        
        sql = "UPDATE reviews SET content = ? WHERE review_id = ?"
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (review_update.content, review_id))
            return cursor.rowcount > 0
    
    def delete_review(self, review_id: str) -> bool:
        """
        删除评论
        
        Args:
            review_id: 评论ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            sql = "DELETE FROM reviews WHERE review_id = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (review_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"删除评论失败: {e}")
            return False
    
    def get_reviews_by_quote(self, quote_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Review]:
        """
        根据语录获取评论列表
        
        Args:
            quote_id: 语录ID
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Review]: 评论列表
        """
        try:
            sql = "SELECT * FROM reviews WHERE quote_id = ? ORDER BY time_stamp"
            params: List[Any] = [quote_id]
            
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"获取语录评论失败: {e}")
            return []
    
    def get_reviews_by_author(self, author_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Review]:
        """
        根据作者获取评论列表
        
        Args:
            author_id: 作者QQ号
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Review]: 评论列表
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE author_id = ? ORDER BY time_stamp"
            params: List[Any] = [author_id]
            
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"获取作者评论失败: {e}")
            return []
    
    def get_recent_reviews(self, limit: Optional[int] = None, offset: int = 0) -> List[Review]:
        """
        获取最近的评论（按时间排序）
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Review]: 最近评论列表
        """
        try:
            sql = f"SELECT * FROM {self.table_name} ORDER BY time_stamp DESC"
            params: List[Any] = []
            
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"获取最近评论失败: {e}")
            return []
    
    def search_reviews_by_content(self, keyword: str, limit: Optional[int] = None, offset: int = 0) -> List[Review]:
        """
        根据内容关键词搜索评论
        
        Args:
            keyword: 搜索关键词
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Review]: 评论列表
        """
        try:
            pattern = f"%{keyword}%"
            sql = f"SELECT * FROM {self.table_name} WHERE content LIKE ? ORDER BY time_stamp DESC"
            params: List[Any] = [pattern]
            
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                return [self._row_to_model(row) for row in rows]
                
        except sqlite3.Error as e:
            self.logger.error(f"搜索评论失败: {e}")
            return []
    
    def count_reviews_by_quote(self, quote_id: str) -> int:
        """
        统计语录的评论数量
        
        Args:
            quote_id: 语录ID
            
        Returns:
            int: 评论数量
        """
        try:
            sql = f"SELECT COUNT(*) FROM {self.table_name} WHERE quote_id = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (quote_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except sqlite3.Error as e:
            self.logger.error(f"统计语录评论数量失败: {e}")
            return 0
    
    def count_reviews_by_author(self, author_id: str) -> int:
        """
        统计作者的评论数量
        
        Args:
            author_id: 作者QQ号
            
        Returns:
            int: 评论数量
        """
        try:
            sql = f"SELECT COUNT(*) FROM {self.table_name} WHERE author_id = ?"
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (author_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except sqlite3.Error as e:
            self.logger.error(f"统计作者评论数量失败: {e}")
            return 0
    
    def get_reviews_with_quote_info(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取包含语录信息的评论列表
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Dict[str, Any]]: 包含语录信息的评论列表
        """
        try:
            sql = f"""
            SELECT 
                r.review_id, r.time_stamp, r.author_id, r.quote_id, r.content as review_content,
                q.content as quote_content, q.author_id as quote_author_id, q.group_id
            FROM {self.table_name} r
            JOIN quotes q ON r.quote_id = q.quote_id
            ORDER BY r.time_stamp DESC
            """
            params: List[Any] = []
            
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    result.append({
                        "review_id": row["review_id"],
                        "time_stamp": row["time_stamp"],
                        "author_id": row["author_id"],
                        "quote_id": row["quote_id"],
                        "review_content": row["review_content"],
                        "quote_content": row["quote_content"],
                        "quote_author_id": row["quote_author_id"],
                        "group_id": row["group_id"]
                    })
                
                return result
                
        except Exception as e:
            self.logger.error(f"获取评论和语录信息失败: {e}")
            return []
    
    def get_reviews_by_quote_author(self, quote_author_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Review]:
        """
        根据语录作者获取对其语录的评论
        
        Args:
            quote_author_id: 语录作者QQ号
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Review]: 评论列表
        """
        try:
            sql = f"""
            SELECT r.* FROM {self.table_name} r
            JOIN quotes q ON r.quote_id = q.quote_id
            WHERE q.author_id = ?
            ORDER BY r.time_stamp DESC
            """
            params: List[Any] = [quote_author_id]
            
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                return [self._row_to_model(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"根据语录作者获取评论失败: {e}")
            return []
    
    def delete_reviews_by_quote(self, quote_id: str) -> bool:
        """
        删除指定语录的所有评论
        
        Args:
            quote_id: 语录ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            sql = f"DELETE FROM {self.table_name} WHERE quote_id = ?"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (quote_id,))
                return True  # 即使没有删除任何行也返回True
                
        except Exception as e:
            self.logger.error(f"删除语录评论失败: {e}")
            return False
    
    def delete_reviews_by_author(self, author_id: str) -> bool:
        """
        删除指定作者的所有评论
        
        Args:
            author_id: 作者QQ号
            
        Returns:
            bool: 删除是否成功
        """
        try:
            sql = f"DELETE FROM {self.table_name} WHERE author_id = ?"
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql, (author_id,))
                return True  # 即使没有删除任何行也返回True
                
        except Exception as e:
            self.logger.error(f"删除作者评论失败: {e}")
            return False
    
    def batch_create_reviews(self, reviews: List[ReviewCreate]) -> bool:
        """
        批量创建评论
        
        Args:
            reviews: 评论创建模型列表
            
        Returns:
            bool: 批量创建是否成功
        """
        if not reviews:
            return True
        
        try:
            sql = "INSERT INTO reviews (review_id, time_stamp, author_id, quote_id, content) VALUES (?, ?, ?, ?, ?)"
            current_time = datetime.now().isoformat()
            values_list = [
                (review.review_id, current_time, review.author_id, review.quote_id, review.content)
                for review in reviews
            ]
            
            with self.connection_manager.cursor() as cursor:
                cursor.executemany(sql, values_list)
                return cursor.rowcount == len(reviews)
        except sqlite3.Error as e:
            self.logger.error(f"批量创建评论失败: {e}")
            return False
    
    def get_review_statistics(self) -> Dict[str, Any]:
        """
        获取评论统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            sql = f"""
            SELECT 
                COUNT(*) as total_reviews,
                COUNT(DISTINCT author_id) as unique_reviewers,
                COUNT(DISTINCT quote_id) as reviewed_quotes
            FROM {self.table_name}
            """
            
            with self.connection_manager.cursor() as cursor:
                cursor.execute(sql)
                row = cursor.fetchone()
                
                if row:
                    return {
                        "total_reviews": row["total_reviews"],
                        "unique_reviewers": row["unique_reviewers"],
                        "reviewed_quotes": row["reviewed_quotes"]
                    }
                else:
                    return {
                        "total_reviews": 0,
                        "unique_reviewers": 0,
                        "reviewed_quotes": 0
                    }
                    
        except Exception as e:
            self.logger.error(f"获取评论统计信息失败: {e}")
            return {
                "total_reviews": 0,
                "unique_reviewers": 0,
                "reviewed_quotes": 0
            }