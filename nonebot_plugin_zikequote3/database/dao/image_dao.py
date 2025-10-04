from typing import List, Dict, Any, Optional
from sqlite3 import Row
from datetime import datetime
import sqlite3

from .base_dao import BaseDAO
from ..models.images import Image, ImageCreate, ImageUpdate


class ImageDAO(BaseDAO[Image]):
    """
    图片数据访问对象，处理图片相关的数据库操作
    """
    
    @property
    def table_name(self) -> str:
        return "images"
    
    @property
    def primary_key(self) -> str:
        return "uuid"
    
    @property
    def allowed_fields(self) -> List[str]:
        return ["uuid", "original_filename", "stored_filename", "file_path", "time_stamp", "checksum_sha256"]
    
    def _row_to_model(self, row: Row) -> Image:
        """将数据库行转换为Image模型对象"""
        return Image(
            uuid=row["uuid"],
            original_filename=row["original_filename"],
            stored_filename=row["stored_filename"],
            file_path=row["file_path"],
            time_stamp=row["time_stamp"],
            checksum_sha256=row["checksum_sha256"]
        )
    
    def _model_to_dict(self, model: Image) -> Dict[str, Any]:
        """将Image模型对象转换为字典"""
        return {
            "uuid": model.uuid,
            "original_filename": model.original_filename,
            "stored_filename": model.stored_filename,
            "file_path": model.file_path,
            "time_stamp": model.time_stamp,
            "checksum_sha256": model.checksum_sha256
        }
    
    def _create_image(self, image_create: ImageCreate) -> bool:
        """
        创建新图片（内部方法）
        
        Args:
            image_create: 图片创建模型
            
        Returns:
            bool: 创建是否成功
        """
        sql = """
        INSERT INTO images (uuid, original_filename, stored_filename, file_path, time_stamp, checksum_sha256)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        values = (
            image_create.uuid,
            image_create.original_filename,
            image_create.stored_filename,
            image_create.file_path,
            datetime.now().isoformat(),
            image_create.checksum_sha256
        )
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    def create_image(self, uuid: str, original_filename: str, stored_filename: str, file_path: str, checksum_sha256: str) -> bool:
        """
        创建新图片
        
        Args:
            uuid: 图片UUID
            original_filename: 原始文件名
            stored_filename: 存储文件名
            file_path: 文件路径
            checksum_sha256: SHA256校验和
            
        Returns:
            bool: 创建是否成功
        """
        image_create = ImageCreate(
            uuid=uuid,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            checksum_sha256=checksum_sha256
        )
        return self._create_image(image_create)
    
    def get_image_by_uuid(self, uuid: str) -> Optional[Image]:
        """
        根据UUID获取图片
        
        Args:
            uuid: 图片UUID
            
        Returns:
            Optional[Image]: 图片对象或None
        """
        sql = "SELECT * FROM images WHERE uuid = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (uuid,))
            row = cursor.fetchone()
            
            return self._row_to_model(row) if row else None
    
    def _update_image(self, uuid: str, image_update: ImageUpdate) -> bool:
        """
        更新图片信息（内部方法）
        
        Args:
            uuid: 图片UUID
            image_update: 图片更新模型
            
        Returns:
            bool: 更新是否成功
        """
        update_parts = []
        params = []
        
        if image_update.original_filename is not None:
            update_parts.append("original_filename = ?")
            params.append(image_update.original_filename)
        if image_update.stored_filename is not None:
            update_parts.append("stored_filename = ?")
            params.append(image_update.stored_filename)
        if image_update.file_path is not None:
            update_parts.append("file_path = ?")
            params.append(image_update.file_path)
        if image_update.checksum_sha256 is not None:
            update_parts.append("checksum_sha256 = ?")
            params.append(image_update.checksum_sha256)
        
        if not update_parts:
            return True
        
        sql = f"UPDATE images SET {', '.join(update_parts)} WHERE uuid = ?"
        params.append(uuid)
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    def update_image(self, uuid: str, original_filename: Optional[str] = None, stored_filename: Optional[str] = None,
                    file_path: Optional[str] = None, checksum_sha256: Optional[str] = None) -> bool:
        """
        更新图片信息
        
        Args:
            uuid: 图片UUID
            original_filename: 原始文件名（可选）
            stored_filename: 存储文件名（可选）
            file_path: 文件路径（可选）
            checksum_sha256: SHA256校验和（可选）
            
        Returns:
            bool: 更新是否成功
        """
        image_update = ImageUpdate(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            checksum_sha256=checksum_sha256
        )
        return self._update_image(uuid, image_update)
    
    def delete_image(self, uuid: str) -> bool:
        """
        删除图片
        
        Args:
            uuid: 图片UUID
            
        Returns:
            bool: 删除是否成功
        """
        sql = "DELETE FROM images WHERE uuid = ?"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (uuid,))
            return cursor.rowcount > 0
    
    def get_images_by_checksum(self, checksum_sha256: str) -> List[Image]:
        """
        根据SHA256校验和获取图片
        
        Args:
            checksum_sha256: SHA256校验和
            
        Returns:
            List[Image]: 图片列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE checksum_sha256 = ? ORDER BY time_stamp"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (checksum_sha256,))
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def get_recent_images(self, limit: Optional[int] = None, offset: int = 0) -> List[Image]:
        """
        获取最近的图片（按时间排序）
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Image]: 最近图片列表
        """
        sql = f"SELECT * FROM {self.table_name} ORDER BY time_stamp DESC"
        params: List[Any] = []
        
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def image_exists(self, uuid: str) -> bool:
        """
        检查图片是否存在
        
        Args:
            uuid: 图片UUID
            
        Returns:
            bool: 图片是否存在
        """
        sql = "SELECT 1 FROM images WHERE uuid = ? LIMIT 1"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (uuid,))
            return cursor.fetchone() is not None
    
    def count_images(self) -> int:
        """
        统计图片总数
        
        Returns:
            int: 图片总数
        """
        sql = "SELECT COUNT(*) FROM images"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_images_by_original_filename(self, original_filename: str) -> List[Image]:
        """
        根据原始文件名获取图片
        
        Args:
            original_filename: 原始文件名
            
        Returns:
            List[Image]: 图片列表
        """
        sql = f"SELECT * FROM {self.table_name} WHERE original_filename = ? ORDER BY time_stamp"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (original_filename,))
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def search_images_by_filename(self, filename_pattern: str) -> List[Image]:
        """
        根据文件名模式搜索图片
        
        Args:
            filename_pattern: 文件名模式（支持%通配符）
            
        Returns:
            List[Image]: 图片列表
        """
        pattern = f"%{filename_pattern}%"
        sql = f"SELECT * FROM {self.table_name} WHERE original_filename LIKE ? OR stored_filename LIKE ? ORDER BY time_stamp DESC"
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql, (pattern, pattern))
            rows = cursor.fetchall()
            
            return [self._row_to_model(row) for row in rows]
    
    def batch_create_images(self, images: List[ImageCreate]) -> bool:
        """
        批量创建图片
        
        Args:
            images: 图片创建模型列表
            
        Returns:
            bool: 批量创建是否成功
        """
        if not images:
            return True
        
        sql = """
        INSERT INTO images (uuid, original_filename, stored_filename, file_path, time_stamp, checksum_sha256)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        current_time = datetime.now().isoformat()
        values_list = [
            (
                image.uuid,
                image.original_filename,
                image.stored_filename,
                image.file_path,
                current_time,
                image.checksum_sha256
            )
            for image in images
        ]
        
        with self.connection_manager.cursor() as cursor:
            cursor.executemany(sql, values_list)
            return cursor.rowcount == len(images)
    
    def get_duplicate_images(self) -> List[Dict[str, Any]]:
        """
        获取重复的图片（基于SHA256校验和）
        
        Returns:
            List[Dict[str, Any]]: 重复图片信息列表
        """
        sql = """
        SELECT 
            checksum_sha256,
            COUNT(*) as duplicate_count,
            GROUP_CONCAT(uuid) as uuids,
            GROUP_CONCAT(original_filename) as original_filenames
        FROM images 
        GROUP BY checksum_sha256 
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
        """
        
        with self.connection_manager.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    "checksum_sha256": row["checksum_sha256"],
                    "duplicate_count": row["duplicate_count"],
                    "uuids": row["uuids"].split(",") if row["uuids"] else [],
                    "original_filenames": row["original_filenames"].split(",") if row["original_filenames"] else []
                })
            
            return result