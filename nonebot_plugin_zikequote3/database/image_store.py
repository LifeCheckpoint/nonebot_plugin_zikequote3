"""
图像文件存储管理类
"""

import hashlib
import io
import shutil
import uuid
from pathlib import Path
from typing import Union, Optional
from PIL import Image as PILImage
from PIL.Image import Image as PILImageType


class ImageStore:
    """
    图像文件存储管理类
    
    功能：
    - 上传图像文件，生成UUID并按照两层目录结构存储
    - 根据UUID获取图像文件路径
    - 根据UUID删除图像文件
    """
    
    def __init__(self, storage_path: Path) -> None:
        """
        初始化图像存储管理器
        
        Args:
            storage_path: 图像存储根目录路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_storage_path_for_uuid(self, uuid_str: str) -> Path:
        """
        根据UUID生成存储路径
        
        Args:
            uuid_str: UUID字符串
            
        Returns:
            存储目录路径
        """
        # 使用UUID的前4个字符创建两层目录结构
        dir1 = uuid_str[:2]
        dir2 = uuid_str[2:4]
        
        directory = self.storage_path / dir1 / dir2
        directory.mkdir(parents=True, exist_ok=True)
        
        return directory
    
    def _determine_extension(self,
                           image_data: Union[bytes, Path, PILImageType],
                           filename: Optional[str] = None) -> str:
        """
        确定图像文件扩展名
        
        Args:
            image_data: 图像数据
            filename: 原始文件名（可选）
            
        Returns:
            文件扩展名（包含点号，如 ".png"）
        """
        # 如果有文件名，优先使用文件名的扩展名
        if filename:
            suffix = Path(filename).suffix.lower()
            return suffix if suffix else ".png"
        
        # 如果是PIL图像对象，根据格式确定扩展名
        if isinstance(image_data, PILImageType):
            format_name = image_data.format or "PNG"
            return f".{format_name.lower()}"
        
        # 如果是字节数据，尝试检测图像格式
        if isinstance(image_data, bytes):
            try:
                with PILImage.open(io.BytesIO(image_data)) as img:
                    format_name = img.format or "PNG"
                    return f".{format_name.lower()}"
            except Exception:
                # 如果检测失败，默认使用PNG
                return ".png"
        
        # 如果是文件路径，尝试从文件扩展名获取
        if isinstance(image_data, Path):
            suffix = image_data.suffix.lower()
            return suffix if suffix else ".png"
        
        # 默认使用PNG格式
        return ".png"
    
    def upload(self,
               image_data: Union[bytes, Path, PILImageType],
               filename: Optional[str] = None) -> str:
        """
        上传图像文件
        
        Args:
            image_data: 图像数据，可以是字节、文件路径或PIL图像对象
            filename: 原始文件名（可选，用于确定扩展名）
            
        Returns:
            生成的UUID字符串
            
        Raises:
            ValueError: 图像数据格式不支持
            IOError: 文件读写错误
        """
        # 生成UUID
        image_uuid = str(uuid.uuid4()).replace("-", "").lower()
        
        # 确定文件扩展名
        extension = self._determine_extension(image_data, filename)
        
        # 获取存储路径
        storage_dir = self._get_storage_path_for_uuid(image_uuid)
        file_path = storage_dir / f"{image_uuid}{extension}"
        
        try:
            # 处理不同类型的图像数据
            if isinstance(image_data, bytes):
                # 字节数据直接写入
                with open(file_path, "wb") as f:
                    f.write(image_data)
                    
            elif isinstance(image_data, Path):
                # 文件路径，复制文件
                shutil.copy2(image_data, file_path)
                
            elif isinstance(image_data, PILImageType):
                # PIL图像对象，保存为文件
                image_data.save(file_path)
                
            else:
                raise ValueError(f"不支持的图像数据类型: {type(image_data)}")
                
        except Exception as e:
            # 如果上传失败，尝试删除可能已经创建的文件
            if file_path.exists():
                file_path.unlink()
            raise e
        
        return image_uuid
    
    def get_path(self, image_uuid: str) -> Path:
        """
        根据UUID获取图像文件路径
        
        Args:
            image_uuid: 图像UUID
            
        Returns:
            图像文件的完整路径
            
        Note:
            不检查文件是否存在，只是构建路径
        """
        storage_dir = self._get_storage_path_for_uuid(image_uuid)
        
        # 查找该目录下以UUID开头的文件
        for file_path in storage_dir.glob(f"{image_uuid}.*"):
            return file_path
        
        # 如果没有找到，返回预期的路径（基于常见扩展名）
        return storage_dir / f"{image_uuid}.png"
    
    def delete(self, image_uuid: str) -> bool:
        """
        根据UUID删除图像文件
        
        Args:
            image_uuid: 图像UUID
            
        Returns:
            是否成功删除（文件存在并成功删除返回True，文件不存在返回False）
        """
        file_path = self.get_path(image_uuid)
        
        if file_path.exists():
            file_path.unlink()
            return True
        
        return False
    
    def exists(self, image_uuid: str) -> bool:
        """
        检查图像文件是否存在
        
        Args:
            image_uuid: 图像UUID
            
        Returns:
            文件是否存在
        """
        return self.get_path(image_uuid).exists()
    
    def get_sha256(self, image_uuid: str) -> str:
        """
        根据UUID获取图像文件的SHA256哈希值
        
        Args:
            image_uuid: 图像UUID
            
        Returns:
            SHA256哈希值的十六进制字符串
            
        Raises:
            FileNotFoundError: 图像文件不存在
            IOError: 文件读取错误
        """
        file_path = self.get_path(image_uuid)
        
        if not file_path.exists():
            raise FileNotFoundError(f"图像文件不存在: {image_uuid}")
        
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
                return hashlib.sha256(file_data).hexdigest()
        except Exception as e:
            raise IOError(f"读取图像文件失败: {e}")