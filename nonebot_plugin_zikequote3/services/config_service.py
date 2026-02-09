"""
ConfigService —— 群组配置领域服务。

合并原模块：
- ``setting_service.py``     配置读取
- ``validation_service.py``  配置验证

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

import logging
from ast import literal_eval
from typing import Optional

import tomlkit
from tomlkit.exceptions import TOMLKitError

from ..database.models.group_configs import GroupConfigs
from ..database.repositories.group_config_repository import GroupConfigRepository
from ..exceptions import ResourceNotFoundError, ValidationException

logger = logging.getLogger(__name__)


class ConfigService:
    """
    群组配置领域服务，通过构造函数注入 Repository 依赖。

    职责：
    1. 获取群组配置
    2. 设置 / 更新群组配置
    3. 验证配置格式
    4. 解析配置参数
    """

    def __init__(
        self,
        group_config_repo: GroupConfigRepository,
    ) -> None:
        self._group_config_repo = group_config_repo

    # ------------------------------------------------------------------ #
    #  查询
    # ------------------------------------------------------------------ #

    async def get_group_config(self, group_id: str) -> Optional[GroupConfigs]:
        """
        获取群组配置。

        Args:
            group_id: 群组 ID。

        Returns:
            群组配置对象，不存在返回 ``None``。
        """
        return await self._group_config_repo.get_group_config_by_id(group_id)

    async def get_group_toml(self, group_id: str) -> Optional[str]:
        """
        获取群组的 TOML 配置内容。

        Args:
            group_id: 群组 ID。

        Returns:
            TOML 字符串，不存在返回 ``None``。
        """
        return await self._group_config_repo.get_toml_config_by_group_id(group_id)

    async def group_config_exists(self, group_id: str) -> bool:
        """检查群组配置是否存在。"""
        return await self._group_config_repo.group_config_exists(group_id)

    # ------------------------------------------------------------------ #
    #  设置 / 更新
    # ------------------------------------------------------------------ #

    async def set_group_config(self, group_id: str, config_toml: str) -> GroupConfigs:
        """
        设置群组配置（创建或更新）。

        Args:
            group_id: 群组 ID。
            config_toml: TOML 格式的配置字符串。

        Returns:
            更新后的群组配置对象。

        Raises:
            ValidationException: TOML 格式无效。
        """
        if not self.validate_toml(config_toml):
            raise ValidationException("TOML 配置格式无效")

        result = await self._group_config_repo.update_or_create_group_config(
            group_id, config_toml
        )
        logger.info("群组 %s 配置已更新", group_id)
        return result

    async def delete_group_config(self, group_id: str) -> None:
        """
        删除群组配置。

        Raises:
            ResourceNotFoundError: 配置不存在。
        """
        exists = await self._group_config_repo.group_config_exists(group_id)
        if not exists:
            raise ResourceNotFoundError(f"群组 {group_id} 配置不存在")

        await self._group_config_repo.delete_group_config(group_id)
        logger.info("群组 %s 配置已删除", group_id)

    # ------------------------------------------------------------------ #
    #  验证
    # ------------------------------------------------------------------ #

    @staticmethod
    def validate_toml(config_str: str) -> bool:
        """
        验证 TOML 配置格式是否合法。

        Args:
            config_str: TOML 格式字符串。

        Returns:
            ``True`` 表示格式合法。
        """
        try:
            tomlkit.parse(config_str)
            return True
        except TOMLKitError:
            return False

    @staticmethod
    def parse_config_param(args: list[str]) -> tuple[str, object]:
        """
        解析配置参数（schema_path + value）。

        原 ``validation_service.s_validate_parse_param`` 逻辑。

        Args:
            args: 长度为 2 的列表，``[schema_path, value_literal]``。

        Returns:
            ``(schema_path, parsed_value)``

        Raises:
            ValidationException: 参数格式不正确。
        """
        if len(args) < 2:
            raise ValidationException("配置参数需要至少 2 个值: schema_path 和 value")
        try:
            schema_str = args[0].strip()
            new_value = literal_eval(args[1].strip())
            return schema_str, new_value
        except (ValueError, SyntaxError) as e:
            raise ValidationException(f"配置参数解析失败: {e}") from e
