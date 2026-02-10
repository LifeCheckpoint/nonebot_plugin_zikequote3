"""图片 Pydantic DTO 定义。"""

from .imports import *


class ImageBase(BaseModel):
    """图片基础模型。"""
    uuid: str = Field(..., description="图片 UUID，主键")
    original_filename: Optional[str] = Field(None, description="原始文件名")
    stored_filename: str = Field(..., description="存储文件名")
    file_path: str = Field(..., description="文件路径")
    checksum_sha256: str = Field(..., description="SHA256 校验和")


class ImageCreate(ImageBase):
    """创建图片模型。"""
    pass


class ImageUpdate(BaseModel):
    """更新图片模型。"""
    original_filename: Optional[str] = Field(None, description="原始文件名")
    stored_filename: Optional[str] = Field(None, description="存储文件名")
    file_path: Optional[str] = Field(None, description="文件路径")
    checksum_sha256: Optional[str] = Field(None, description="SHA256 校验和")


class Image(ImageBase):
    """完整图片模型。"""
    time_stamp: datetime = Field(..., description="创建时间")