from .imports import *

class GroupConfigsBase(BaseModel):
    """群自定义配置基础模型"""
    group_id: str = Field(..., description="群号")
    toml_config: str = Field(..., description="TOML 格式的配置内容")

class GroupConfigsCreate(GroupConfigsBase):
    """创建群自定义配置模型"""
    pass

class GroupConfigsUpdate(BaseModel):
    """更新群自定义配置模型"""
    toml_config: Optional[str] = Field(None, description="TOML 格式的配置内容")

class GroupConfigs(GroupConfigsBase):
    """完整群自定义配置模型"""
    class Config:
        from_attributes = True
        