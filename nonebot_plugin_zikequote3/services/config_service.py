"""
ConfigService —— 群组配置领域服务。

合并原模块：
- ``setting_service.py``     配置读取
- ``validation_service.py``  配置验证

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

from ast import literal_eval
from typing import Any, Optional, Sequence

import tomlkit
from nonebot import logger
from pydantic import ValidationError
from tomlkit.exceptions import TOMLKitError

from ..config import ConfigSchema, EmbeddingConfig, parse_config_from_toml
from ..database.models.group_configs import GroupConfigs
from ..database.repositories.group_config_repository import GroupConfigRepository
from ..database.repositories.group_repository import GroupRepository
from ..exceptions import ResourceNotFoundError, ValidationException

_EMBEDDING_GLOBAL_ONLY_ITEMS = frozenset(
    f"embedding.{field_name}"
    for field_name in EmbeddingConfig.model_fields
    if field_name != "enabled"
)


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
        group_repo: GroupRepository,
        default_config: ConfigSchema | None = None,
    ) -> None:
        self._group_config_repo = group_config_repo
        self._group_repo = group_repo
        self._default_config = (default_config or ConfigSchema()).model_copy(deep=True)

    def _copy_default_config(self) -> ConfigSchema:
        """返回启动期全局配置的深拷贝。"""
        return self._default_config.model_copy(deep=True)

    def _build_default_doc(self) -> tomlkit.TOMLDocument:
        """将启动期全局配置序列化为 TOML 文档。"""
        return tomlkit.parse(
            tomlkit.dumps(self._default_config.model_dump(exclude_none=True))  # type: ignore[arg-type]
        )

    def _get_nonreloadable_items(self) -> set[str]:
        """获取群级热更新禁止覆盖的配置项路径集合。"""
        return {
            *self._default_config.configure.nonreloadable_items,
            *_EMBEDDING_GLOBAL_ONLY_ITEMS,
        }

    def _raise_nonreloadable_error(self, schema_str: str) -> None:
        """针对不可热更新项抛出稳定错误。"""
        if schema_str in _EMBEDDING_GLOBAL_ONLY_ITEMS:
            raise ValidationException(
                f"配置项 '{schema_str}' 仅支持启动期全局配置，不支持群级热更新"
            )
        raise ValidationException(f"配置项 '{schema_str}' 不可修改")

    def _iter_group_doc_items(
        self,
        doc: tomlkit.TOMLDocument,
    ) -> list[tuple[str, str, Any]]:
        """遍历群配置文档中的 ``section.key`` 项，并做结构校验。"""
        result: list[tuple[str, str, Any]] = []
        schema_model = self._default_config

        for section_name in doc:
            if not hasattr(schema_model, section_name):
                raise ValidationException(f"配置节 '{section_name}' 不存在")

            section_value = doc[section_name]
            if not hasattr(section_value, "keys"):
                raise ValidationException(f"配置节 '{section_name}' 必须为 table 结构")

            section_model = getattr(schema_model, section_name)
            for key_name in section_value:
                if not hasattr(section_model, key_name):
                    raise ValidationException(
                        f"配置项 '{key_name}' 在节 '{section_name}' 中不存在"
                    )
                result.append((section_name, key_name, section_value[key_name]))

        return result

    def _ensure_group_doc_structure(
        self,
        doc: tomlkit.TOMLDocument,
        *,
        reject_nonreloadable: bool,
    ) -> None:
        """校验群配置文档结构是否合法。"""
        nonreloadable_items = self._get_nonreloadable_items()
        for section_name, key_name, _ in self._iter_group_doc_items(doc):
            schema_str = f"{section_name}.{key_name}"
            if reject_nonreloadable and schema_str in nonreloadable_items:
                self._raise_nonreloadable_error(schema_str)

    def _build_effective_config_doc(
        self,
        group_doc: tomlkit.TOMLDocument | None,
    ) -> tomlkit.TOMLDocument:
        """将群级可覆盖项叠加到启动期全局配置上，生成运行时生效配置。"""
        effective_doc = self._build_default_doc()
        if group_doc is None:
            return effective_doc

        nonreloadable_items = self._get_nonreloadable_items()
        for section_name, key_name, value in self._iter_group_doc_items(group_doc):
            schema_str = f"{section_name}.{key_name}"
            if schema_str in nonreloadable_items:
                continue
            effective_doc[section_name][key_name] = value  # type: ignore[index]

        return effective_doc

    def _validate_effective_config(
        self,
        group_doc: tomlkit.TOMLDocument | None,
        *,
        context: str,
    ) -> ConfigSchema:
        """校验群配置叠加后的最终生效配置。"""
        try:
            return parse_config_from_toml(self._build_effective_config_doc(group_doc))
        except ValidationError as exc:
            raise ValidationException(f"{context}不符合配置 schema: {exc}") from exc

    def _normalize_group_doc(
        self,
        group_doc: tomlkit.TOMLDocument,
    ) -> tomlkit.TOMLDocument:
        """规范化群配置，仅保留允许覆盖且与全局配置不同的项。"""
        normalized_doc = tomlkit.document()
        nonreloadable_items = self._get_nonreloadable_items()

        for section_name, key_name, value in self._iter_group_doc_items(group_doc):
            schema_str = f"{section_name}.{key_name}"
            if schema_str == "configure.cfg_version":
                continue
            if schema_str in nonreloadable_items:
                continue

            default_value = getattr(getattr(self._default_config, section_name), key_name)
            if value == default_value:
                continue

            if section_name not in normalized_doc:
                normalized_doc[section_name] = tomlkit.table()
            normalized_doc[section_name][key_name] = value  # type: ignore[index]

        if "configure" not in normalized_doc:
            normalized_doc["configure"] = tomlkit.table()
        normalized_doc["configure"]["cfg_version"] = (  # type: ignore[index]
            self._default_config.configure.cfg_version
        )
        return normalized_doc

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
        try:
            doc = tomlkit.parse(config_toml)
        except TOMLKitError as exc:
            raise ValidationException("TOML 配置格式无效") from exc

        self._ensure_group_doc_structure(doc, reject_nonreloadable=True)
        self._validate_effective_config(doc, context="群组配置")
        normalized_toml = tomlkit.dumps(self._normalize_group_doc(doc))

        result = await self._group_config_repo.update_or_create_group_config(
            group_id, normalized_toml
        )
        logger.info("群组 {} 配置已更新", group_id)
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
        logger.info("群组 {} 配置已删除", group_id)

    async def modify_single_value(
        self,
        group_id: str,
        schema_str: str,
        new_value: Any,
    ) -> None:
        """
        按 ``section.key`` 路径修改群组配置中的单个值并持久化。

        如果群组尚无自定义配置，则基于启动期全局配置创建最小覆盖配置。

        :param group_id: 群组 ID
        :type group_id: str
        :param schema_str: 形如 ``"collecting.pickup_interval"`` 的路径
        :type schema_str: str
        :param new_value: 新值（已经过 Python 类型解析）
        :type new_value: Any
        :raises ValidationException: 路径格式错误、section/key 不存在或属于不可修改项
        """
        parts = schema_str.split(".")
        if len(parts) != 2:
            raise ValidationException(
                f"配置项路径必须为 'section.key' 格式，收到: '{schema_str}'"
            )
        section, key = parts

        if not hasattr(self._default_config, section):
            raise ValidationException(f"配置节 '{section}' 不存在")
        section_model = getattr(self._default_config, section)
        if not hasattr(section_model, key):
            raise ValidationException(
                f"配置项 '{key}' 在节 '{section}' 中不存在"
            )

        if schema_str in self._get_nonreloadable_items():
            self._raise_nonreloadable_error(schema_str)

        toml_str = await self._group_config_repo.get_toml_config_by_group_id(group_id)
        if toml_str:
            try:
                doc = tomlkit.parse(toml_str)
            except TOMLKitError as exc:
                raise ValidationException(
                    "现有群组配置 TOML 配置格式无效，请先修复或删除后再修改"
                ) from exc
            self._ensure_group_doc_structure(doc, reject_nonreloadable=False)
        else:
            doc = tomlkit.document()

        if section not in doc:
            doc[section] = tomlkit.table()
        doc[section][key] = new_value  # type: ignore[index]

        self._validate_effective_config(doc, context=f"配置项 '{schema_str}' ")
        normalized_toml = tomlkit.dumps(self._normalize_group_doc(doc))

        await self._group_repo.ensure_group_exists(group_id)
        await self._group_config_repo.update_or_create_group_config(
            group_id, normalized_toml
        )
        logger.info(
            "群组 {} 配置项 '{}' 已更新为 {!r}", group_id, schema_str, new_value
        )

    async def get_parsed_config(self, group_id: str) -> ConfigSchema:
        """
        获取群组的结构化配置（Pydantic 模型）。

        如果群组无自定义配置，返回启动期已加载的全局配置。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 解析后的 ``ConfigSchema`` 实例
        :rtype: ConfigSchema
        """
        toml_str = await self._group_config_repo.get_toml_config_by_group_id(group_id)
        if toml_str is None:
            return self._copy_default_config()

        try:
            doc = tomlkit.parse(toml_str)
            self._ensure_group_doc_structure(doc, reject_nonreloadable=False)
            return self._validate_effective_config(doc, context=f"群组 {group_id} 配置")
        except Exception:
            logger.warning(
                "群组 {} 的 TOML 配置解析或校验失败，回退到启动期全局配置",
                group_id,
                exc_info=True,
            )
            return self._copy_default_config()

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
            raw_value = args[1].strip()
            _bool_map = {"true": "True", "false": "False"}
            raw_value = _bool_map.get(raw_value.lower(), raw_value)
            new_value = literal_eval(raw_value)
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
        default_version = self._default_config.configure.cfg_version

        all_configs: Sequence[GroupConfigs] = (
            await self._group_config_repo.get_all_group_configs()
        )

        fixed_count = 0
        for gc in all_configs:
            try:
                group_doc = tomlkit.parse(gc.toml_config)
                self._ensure_group_doc_structure(group_doc, reject_nonreloadable=False)
                self._validate_effective_config(
                    group_doc,
                    context=f"群组 {gc.group_id} 配置",
                )
            except (TOMLKitError, ValidationException):
                logger.warning(
                    "群组 {} 的 TOML 配置解析或校验失败，跳过完整性修复",
                    gc.group_id,
                    exc_info=True,
                )
                continue

            group_version = group_doc.get("configure", {}).get("cfg_version", -1)
            new_toml = tomlkit.dumps(self._normalize_group_doc(group_doc))

            if group_version == default_version and new_toml == gc.toml_config:
                continue

            if group_version != default_version:
                logger.info(
                    "群组 {} 配置版本 v{} → v{}，执行迁移",
                    gc.group_id,
                    group_version,
                    default_version,
                )
            else:
                logger.info(
                    "群组 {} 配置与启动期真源不一致，执行规范化",
                    gc.group_id,
                )

            await self._group_config_repo.update_or_create_group_config(
                gc.group_id, new_toml
            )
            fixed_count += 1
            logger.info("群组 {} 配置已规范化到 v{}", gc.group_id, default_version)

        if fixed_count:
            logger.info("共修复 {} 个群组的配置完整性", fixed_count)
        return fixed_count
