"""
ORM 模型：group_configs 表。
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from nonebot_plugin_zikequote3.database.sa.base import Base


class GroupConfigModel(Base):
    """群聊自定义配置 ORM 模型，对应 ``group_configs`` 表。"""

    __tablename__ = "group_configs"

    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.group_id", ondelete="CASCADE"), primary_key=True
    )
    toml_config: Mapped[str] = mapped_column(Text, nullable=False)

    # ---- DTO 转换 ----
    def to_dto(self):
        """转换为 Pydantic Full DTO ``GroupConfigs``。"""
        from ...models.group_configs import GroupConfigs

        return GroupConfigs(
            group_id=self.group_id,
            toml_config=self.toml_config,
        )

    @classmethod
    def from_create_dto(cls, dto) -> GroupConfigModel:
        """从 Pydantic ``GroupConfigsCreate`` DTO 创建 ORM 实例。"""
        return cls(
            group_id=dto.group_id,
            toml_config=dto.toml_config,
        )
