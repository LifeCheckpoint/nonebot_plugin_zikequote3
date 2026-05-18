"""
ConfigService —— 群组配置领域服务。

合并原模块：
- ``setting_service.py``     配置读取
- ``validation_service.py``  配置验证

所有方法均为 async，不引用 NoneBot 对象、全局变量。
"""

from __future__ import annotations

import asyncio
from ast import literal_eval
from dataclasses import dataclass
from typing import Any, Literal, Optional, Sequence

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


@dataclass(frozen=True, slots=True)
class ConfigDiagnostic:
    """单条群配置诊断信息。"""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ParsedConfigResult:
    """群配置解析结果，兼容返回生效配置并显式暴露诊断信息。"""

    config: ConfigSchema
    source: Literal["default", "group", "repaired"]
    diagnostics: tuple[ConfigDiagnostic, ...] = ()
    stored_toml: str | None = None
    normalized_group_toml: str | None = None

    @property
    def has_diagnostics(self) -> bool:
        """是否存在需要暴露的诊断信息。"""
        return bool(self.diagnostics)

    @property
    def needs_repair(self) -> bool:
        """当前结果是否需要写回修复后的配置。"""
        if self.stored_toml is None:
            return False
        if self.source == "repaired":
            return True
        return (
            self.normalized_group_toml is not None
            and self.normalized_group_toml != self.stored_toml
        )

    def format_diagnostics(self) -> str:
        """格式化诊断信息，便于日志或用户提示输出。"""
        if not self.diagnostics:
            return "无"
        return "；".join(item.message for item in self.diagnostics)


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
        self._config_locks: dict[str, asyncio.Lock] = {}

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
            "configure.cfg_version",
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

    def _set_group_doc_value(
        self,
        doc: tomlkit.TOMLDocument,
        section_name: str,
        key_name: str,
        value: Any,
    ) -> None:
        """向群配置文档安全写入单个 ``section.key`` 项。"""
        if section_name not in doc:
            doc[section_name] = tomlkit.table()
        doc[section_name][key_name] = value  # type: ignore[index]

    def _remove_group_doc_value(
        self,
        doc: tomlkit.TOMLDocument,
        section_name: str,
        key_name: str,
    ) -> None:
        """从群配置文档移除单个 ``section.key`` 项，并清理空节。"""
        if section_name not in doc:
            return

        section = doc[section_name]
        if key_name in section:
            del section[key_name]
        if hasattr(section, "keys") and len(list(section.keys())) == 0:
            del doc[section_name]

    def _sanitize_group_doc(
        self,
        raw_doc: tomlkit.TOMLDocument,
        *,
        group_id: str,
    ) -> tuple[tomlkit.TOMLDocument, tuple[ConfigDiagnostic, ...]]:
        """清洗群配置文档，仅保留可用的群级覆盖项。"""
        diagnostics: list[ConfigDiagnostic] = []
        candidate_doc = tomlkit.document()
        nonreloadable_items = self._get_nonreloadable_items()

        for section_name in raw_doc:
            if not hasattr(self._default_config, section_name):
                diagnostics.append(ConfigDiagnostic(
                    code="unknown_section",
                    message=f"群组 {group_id} 配置包含未知配置节 '{section_name}'，已忽略",
                ))
                continue

            section_value = raw_doc[section_name]
            if not hasattr(section_value, "keys"):
                diagnostics.append(ConfigDiagnostic(
                    code="invalid_section",
                    message=f"群组 {group_id} 配置节 '{section_name}' 不是合法 table，已回退为默认值",
                ))
                continue

            section_model = getattr(self._default_config, section_name)
            for key_name in section_value:
                schema_str = f"{section_name}.{key_name}"
                if schema_str == "configure.cfg_version":
                    continue
                if not hasattr(section_model, key_name):
                    diagnostics.append(ConfigDiagnostic(
                        code="unknown_key",
                        message=f"群组 {group_id} 配置包含未知配置项 '{schema_str}'，已忽略",
                    ))
                    continue
                if schema_str in nonreloadable_items:
                    diagnostics.append(ConfigDiagnostic(
                        code="nonreloadable_item",
                        message=f"群组 {group_id} 配置项 '{schema_str}' 仅支持启动期全局配置，已忽略群级覆盖",
                    ))
                    continue

                self._set_group_doc_value(
                    candidate_doc,
                    section_name,
                    key_name,
                    section_value[key_name],
                )

        sanitized_doc = tomlkit.document()
        for section_name, key_name, value in self._iter_group_doc_items(candidate_doc):
            schema_str = f"{section_name}.{key_name}"
            self._set_group_doc_value(sanitized_doc, section_name, key_name, value)
            try:
                self._validate_effective_config(
                    sanitized_doc,
                    context=f"群组 {group_id} 配置",
                )
            except ValidationException as exc:
                self._remove_group_doc_value(sanitized_doc, section_name, key_name)
                diagnostics.append(ConfigDiagnostic(
                    code="invalid_value",
                    message=f"群组 {group_id} 配置项 '{schema_str}' 校验失败，已回退为默认值: {exc}",
                ))

        return sanitized_doc, tuple(diagnostics)

    def _inspect_group_config_toml(
        self,
        group_id: str,
        toml_str: str | None,
    ) -> ParsedConfigResult:
        """分析群配置 TOML，返回兼容配置与显式诊断结果。"""
        if toml_str is None:
            return ParsedConfigResult(
                config=self._copy_default_config(),
                source="default",
            )

        try:
            raw_doc = tomlkit.parse(toml_str)
        except TOMLKitError as exc:
            diagnostics = (
                ConfigDiagnostic(
                    code="toml_parse_failed",
                    message=f"群组 {group_id} 配置 TOML 解析失败，已回退到默认配置: {exc}",
                ),
            )
            normalized_toml = tomlkit.dumps(
                self._normalize_group_doc(tomlkit.document())
            )
            return ParsedConfigResult(
                config=self._copy_default_config(),
                source="repaired",
                diagnostics=diagnostics,
                stored_toml=toml_str,
                normalized_group_toml=normalized_toml,
            )

        sanitized_doc, diagnostics = self._sanitize_group_doc(raw_doc, group_id=group_id)
        try:
            config = self._validate_effective_config(
                sanitized_doc,
                context=f"群组 {group_id} 配置",
            )
        except ValidationException as exc:
            diagnostics = (
                *diagnostics,
                ConfigDiagnostic(
                    code="schema_repair_failed",
                    message=f"群组 {group_id} 配置整体校验失败，已回退到默认配置: {exc}",
                ),
            )
            sanitized_doc = tomlkit.document()
            config = self._copy_default_config()
            source: Literal["default", "group", "repaired"] = "repaired"
        else:
            source = "group" if not diagnostics else "repaired"

        normalized_toml = tomlkit.dumps(self._normalize_group_doc(sanitized_doc))
        return ParsedConfigResult(
            config=config,
            source=source,
            diagnostics=diagnostics,
            stored_toml=toml_str,
            normalized_group_toml=normalized_toml,
        )

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

        lock = self._config_locks.setdefault(group_id, asyncio.Lock())
        async with lock:
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

        lock = self._config_locks.setdefault(group_id, asyncio.Lock())
        async with lock:
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

    async def get_parsed_config_result(self, group_id: str) -> ParsedConfigResult:
        """
        获取群组的结构化配置结果，并显式携带诊断信息。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 包含生效配置与诊断结果的解析对象
        :rtype: ParsedConfigResult
        """
        toml_str = await self._group_config_repo.get_toml_config_by_group_id(group_id)
        return self._inspect_group_config_toml(group_id, toml_str)

    async def get_parsed_config(self, group_id: str) -> ConfigSchema:
        """
        获取群组的结构化配置（兼容入口）。

        当群配置损坏时，仍返回可用配置，但会通过日志显式暴露诊断结果。

        :param group_id: 群组 ID
        :type group_id: str
        :returns: 解析后的 ``ConfigSchema`` 实例
        :rtype: ConfigSchema
        """
        result = await self.get_parsed_config_result(group_id)
        if result.has_diagnostics:
            logger.warning(
                "群组 {} 配置使用兼容读取结果；诊断信息：{}",
                group_id,
                result.format_diagnostics(),
            )
        return result.config

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
        检查所有群组配置的完整性，并将损坏配置修复为可用状态。

        :returns: 被修复（迁移/规范化）的群组数量
        :rtype: int
        """
        all_configs: Sequence[GroupConfigs] = (
            await self._group_config_repo.get_all_group_configs()
        )

        fixed_count = 0
        for gc in all_configs:
            result = self._inspect_group_config_toml(gc.group_id, gc.toml_config)
            if not result.needs_repair or result.normalized_group_toml is None:
                continue

            if result.has_diagnostics:
                logger.warning(
                    "群组 {} 的配置存在损坏，启动期将自动修复；诊断信息：{}",
                    gc.group_id,
                    result.format_diagnostics(),
                )
            else:
                logger.info(
                    "群组 {} 配置与启动期真源不一致，执行规范化",
                    gc.group_id,
                )

            await self._group_config_repo.update_or_create_group_config(
                gc.group_id,
                result.normalized_group_toml,
            )
            fixed_count += 1
            logger.info("群组 {} 配置已修复为可用状态", gc.group_id)

        if fixed_count:
            logger.info("共修复 {} 个群组的配置完整性", fixed_count)
        return fixed_count
