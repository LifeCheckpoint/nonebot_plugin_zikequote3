from typing import TypedDict
from pathlib import Path
from pydantic import BaseModel, Field

class Config(BaseModel):
    config_toml: str = Field(
        default_factory=lambda: str(Path(__file__).parent / "config.toml"),
        description="配置文件路径"
    )