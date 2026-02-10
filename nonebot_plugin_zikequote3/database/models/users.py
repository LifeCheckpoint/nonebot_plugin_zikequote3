from .imports import *

class UserBase(BaseModel):
    """用户基础模型"""
    qq_id: str = Field(..., description="QQ 号，主键")
    avatar: Optional[bytes] = Field(None, description="头像数据")

class UserCreate(UserBase):
    """创建用户模型"""
    pass

class UserUpdate(BaseModel):
    """更新用户模型"""
    avatar: Optional[bytes] = Field(None, description="头像数据")

class User(UserBase):
    """完整用户模型"""
    model_config = ConfigDict(from_attributes=True)
