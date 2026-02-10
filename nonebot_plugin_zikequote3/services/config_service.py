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
from typing import Any, Optional, Sequence

import tomlkit
from tomlkit.exceptions import TOMLKitError

from ..config import ConfigSchema, parse_config_from_toml
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

    :param group_config_repo: 群组配置仓储实例
    :type group_config_repo: GroupConfigRepository
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

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 群组配置对象，不存在返回 ``None``
        :rtype: Optional[GroupConfigs]
        """
        return await self._group_config_repo.get_group_config_by_id(group_id)

    async def get_group_toml(self, group_id: str) -> Optional[str]:
        """
        获取群组的 TOML 配置内容。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: TOML 字符串，不存在返回 ``None``
        :rtype: Optional[str]
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

        :param group_id: 群组 ID
        :type group_id: str
        :param config_toml: TOML 格式的配置字符串
        :type config_toml: str
        :returns: 更新后的群组配置对象
        :rtype: GroupConfigs
        :raises ValidationException: TOML 格式无效
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

        :param group_id: 群组 ID
        :type group_id: str
        :raises ResourceNotFoundError: 配置不存在
        """
        exists = await self._group_config_repo.group_config_exists(group_id)
        if not exists:
            raise ResourceNotFoundError(f"群组 {group_id} 配置不存在")

        await self._group_config_repo.delete_group_config(group_id)
        logger.info("群组 %s 配置已删除", group_id)

    async def modify_single_value(
        self,
        group_id: str,
        schema_str: str,
        new_value: Any,
    ) -> None:
        """
        按 ``section.key`` 路径修改群组配置中的单个值并持久化。

        如果群组尚无自定义配置，则基于 ``ConfigSchema`` 默认值创建。

        :param group_id: 群组 ID
        :type group_id: str
        :param schema_str: 形如 ``"collecting.pickup_interval"`` 的路径
        :type schema_str: str
        :param new_value: 新值（已经过 Python 类型解析）
        :type new_value: Any
        :raises ValidationException: 路径格式错误、section/key 不存在或属于不可修改项
        """
        # 校验路径格式
        parts = schema_str.split(".")
        if len(parts) != 2:
            raise ValidationException(
                f"配置项路径必须为 'section.key' 格式，收到: '{schema_str}'"
            )
        section, key = parts

        # 校验 section/key 是否存在于 ConfigSchema
        default_cfg = ConfigSchema()
        if not hasattr(default_cfg, section):
            raise ValidationException(f"配置节 '{section}' 不存在")
        section_model = getattr(default_cfg, section)
        if not hasattr(section_model, key):
            raise ValidationException(
                f"配置项 '{key}' 在节 '{section}' 中不存在"
            )

        # 校验不可修改项
        nonreloadable = default_cfg.configure.nonreloadable_items
        if schema_str in nonreloadable:
            raise ValidationException(f"配置项 '{schema_str}' 不可修改")

        # 获取或创建 TOML 文档
        toml_str = await self._group_config_repo.get_toml_config_by_group_id(
            group_id
        )
        if toml_str:
            doc = tomlkit.parse(toml_str)
        else:
            # 基于默认值创建完整 TOML 文档
            doc = tomlkit.parse(
                tomlkit.dumps(default_cfg.model_dump())  # type: ignore[arg-type]
            )

        # 确保 section 存在
        if section not in doc:
            doc[section] = tomlkit.table()

        doc[section][key] = new_value  # type: ignore[index]

        new_toml = tomlkit.dumps(doc)
        await self._group_config_repo.update_or_create_group_config(
            group_id, new_toml
        )
        logger.info(
            "群组 %s 配置项 '%s' 已更新为 %r", group_id, schema_str, new_value
        )

    async def get_parsed_config(self, group_id: str) -> ConfigSchema:
        """
        获取群组的结构化配置（Pydantic 模型）。

        如果群组无自定义配置，返回全局默认值。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 解析后的 ``ConfigSchema`` 实例
        :rtype: ConfigSchema
        """
        toml_str = await self._group_config_repo.get_toml_config_by_group_id(
            group_id
        )
        if toml_str is None:
            return ConfigSchema()
        try:
            doc = tomlkit.parse(toml_str)
            return parse_config_from_toml(doc)
        except Exception:
            logger.warning(
                "群组 %s 的 TOML 配置解析失败，使用默认配置", group_id
            )
            return ConfigSchema()

    async def get_config_value(
        self, group_id: str, section: str, key: str
    ) -> Any:
        """
        获取群组配置中指定 ``section.key`` 的值。

        :param group_id: 群组 ID
        :type group_id: str
        :param section: 配置节名称，如 ``"collecting"``
        :type section: str
        :param key: 配置项名称，如 ``"pickup_interval"``
        :type key: str
        :returns: 配置值
        :rtype: Any
        :raises ValidationException: section 或 key 不存在
        """
        cfg = await self.get_parsed_config(group_id)
        if not hasattr(cfg, section):
            raise ValidationException(f"配置节 '{section}' 不存在")
        section_model = getattr(cfg, section)
        if not hasattr(section_model, key):
            raise ValidationException(
                f"配置项 '{key}' 在节 '{section}' 中不存在"
            )
        return getattr(section_model, key)

    # ------------------------------------------------------------------ #
    #  验证
    # ------------------------------------------------------------------ #

    @staticmethod
    def validate_toml(config_str: str) -> bool:
        """
        验证 TOML 配置格式是否合法。

        :param config_str: TOML 格式字符串
        :type config_str: str
        :returns: ``True`` 表示格式合法
        :rtype: bool
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

        :param args: 长度为 2 的列表，``[schema_path, value_literal]``
        :type args: list[str]
        :returns: ``(schema_path, parsed_value)``
        :rtype: tuple[str, object]
        :raises ValidationException: 参数格式不正确
        """
        if len(args) < 2:
            raise ValidationException("配置参数需要至少 2 个值: schema_path 和 value")
        try:
            schema_str = args[0].strip()
            new_value = literal_eval(args[1].strip())
            return schema_str, new_value
        except (ValueError, SyntaxError) as e:
            raise ValidationException(f"配置参数解析失败: {e}") from e

    # ------------------------------------------------------------------ #
    #  配置完整性修复（版本迁移）
    # ------------------------------------------------------------------ #

    async def fix_config_integrity(self) -> int:
        """
        检查所有群组配置的版本，将旧版本配置迁移到当前默认模板。

        :returns: 被修复（迁移）的群组数量
        :rtype: int
        """
        default_cfg = ConfigSchema()
        default_doc = tomlkit.parse(
            tomlkit.dumps(default_cfg.model_dump())  # type: ignore[arg-type]
        )
        default_version = default_cfg.configure.cfg_version

        all_configs: Sequence[GroupConfigs] = (
            await self._group_config_repo.get_all_group_configs()
        )

        fixed_count = 0
        for gc in all_configs:
            try:
                group_doc = tomlkit.parse(gc.toml_config)
            except TOMLKitError:
                logger.warning(
                    "群组 %s 的 TOML 配置解析失败，跳过完整性修复",
                    gc.group_id,
                )
                continue

            group_version = (
                group_doc.get("configure", {}).get("cfg_version", -1)
            )
            if group_version == default_version:
                continue

            # 版本不一致 → 迁移
            logger.info(
                "群组 %s 配置版本 v%s → v%s，执行迁移",
                gc.group_id,
                group_version,
                default_version,
            )
            new_doc = default_doc.copy()
            for section_name in default_doc:
                if section_name in group_doc:
                    for key_name in default_doc[section_name]:  # type: ignore[union-attr]
                        if key_name in group_doc[section_name]:  # type: ignore[operator]
                            new_doc[section_name][key_name] = (  # type: ignore[index]
                                group_doc[section_name][key_name]  # type: ignore[index]
                            )
            # 强制使用新版本号
            new_doc["configure"]["cfg_version"] = default_version  # type: ignore[index]

            new_toml = tomlkit.dumps(new_doc)
            await self._group_config_repo.update_or_create_group_config(
                gc.group_id, new_toml
            )
            fixed_count += 1
            logger.info("群组 %s 配置已迁移到 v%s", gc.group_id, default_version)

        if fixed_count:
            logger.info("共修复 %d 个群组的配置完整性", fixed_count)
        return fixed_count
