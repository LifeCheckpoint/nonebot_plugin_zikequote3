"""
ConfigService 单元测试。
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from nonebot_plugin_zikequote3.database.models.group_configs import GroupConfigs
from nonebot_plugin_zikequote3.exceptions import ResourceNotFoundError, ValidationException
from nonebot_plugin_zikequote3.services.config_service import ConfigService


# ---------------------------------------------------------------------------
# get_group_config / get_group_toml / group_config_exists
# ---------------------------------------------------------------------------


class TestConfigQuery:
    """配置查询测试。"""

    async def test_get_group_config(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        fake = GroupConfigs(group_id="g1", toml_config="[test]\nkey = 1")
        mock_group_config_repo.get_group_config_by_id.return_value = fake
        result = await config_service.get_group_config("g1")
        assert result is not None
        assert result.group_id == "g1"

    async def test_get_group_config_not_found(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.get_group_config_by_id.return_value = None
        result = await config_service.get_group_config("g1")
        assert result is None

    async def test_get_group_toml(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.get_toml_config_by_group_id.return_value = "[x]\ny = 2"
        result = await config_service.get_group_toml("g1")
        assert result == "[x]\ny = 2"

    async def test_group_config_exists(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.group_config_exists.return_value = True
        assert await config_service.group_config_exists("g1") is True


# ---------------------------------------------------------------------------
# set_group_config
# ---------------------------------------------------------------------------


class TestSetGroupConfig:
    async def test_set_valid_config(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        toml_str = '[section]\nkey = "value"'
        fake = GroupConfigs(group_id="g1", toml_config=toml_str)
        mock_group_config_repo.update_or_create_group_config.return_value = fake

        result = await config_service.set_group_config("g1", toml_str)
        assert result.group_id == "g1"
        mock_group_config_repo.update_or_create_group_config.assert_awaited_once_with(
            "g1", toml_str
        )

    async def test_set_invalid_toml_raises(
        self, config_service: ConfigService
    ) -> None:
        with pytest.raises(ValidationException, match="TOML 配置格式无效"):
            await config_service.set_group_config("g1", "[invalid toml =")


# ---------------------------------------------------------------------------
# delete_group_config
# ---------------------------------------------------------------------------


class TestDeleteGroupConfig:
    async def test_delete_existing(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.group_config_exists.return_value = True
        mock_group_config_repo.delete_group_config.return_value = True
        await config_service.delete_group_config("g1")
        mock_group_config_repo.delete_group_config.assert_awaited_once_with("g1")

    async def test_delete_nonexistent_raises(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.group_config_exists.return_value = False
        with pytest.raises(ResourceNotFoundError):
            await config_service.delete_group_config("g1")


# ---------------------------------------------------------------------------
# validate_toml (static)
# ---------------------------------------------------------------------------


class TestValidateToml:
    def test_valid_toml(self) -> None:
        assert ConfigService.validate_toml('[section]\nkey = "value"') is True

    def test_invalid_toml(self) -> None:
        assert ConfigService.validate_toml("[broken =") is False

    def test_empty_string(self) -> None:
        assert ConfigService.validate_toml("") is True


# ---------------------------------------------------------------------------
# parse_config_param (static)
# ---------------------------------------------------------------------------


class TestParseConfigParam:
    def test_valid_params(self) -> None:
        schema, value = ConfigService.parse_config_param(["showcase.max_quotes", "10"])
        assert schema == "showcase.max_quotes"
        assert value == 10

    def test_string_value(self) -> None:
        schema, value = ConfigService.parse_config_param(["key", "'hello'"])
        assert value == "hello"

    def test_insufficient_args_raises(self) -> None:
        with pytest.raises(ValidationException):
            ConfigService.parse_config_param(["only_one"])

    def test_bool_true_lowercase(self) -> None:
        _, value = ConfigService.parse_config_param(["embedding.enabled", "true"])
        assert value is True

    def test_bool_false_lowercase(self) -> None:
        _, value = ConfigService.parse_config_param(["embedding.enabled", "false"])
        assert value is False

    def test_bool_mixed_case(self) -> None:
        _, value = ConfigService.parse_config_param(["key", "TRUE"])
        assert value is True

    def test_bool_python_style(self) -> None:
        """Python 风格的 True/False 仍然正常工作。"""
        _, value = ConfigService.parse_config_param(["key", "True"])
        assert value is True

    def test_invalid_literal_raises(self) -> None:
        with pytest.raises(ValidationException):
            ConfigService.parse_config_param(["key", "not_a_literal"])


# ---------------------------------------------------------------------------
# get_parsed_config
# ---------------------------------------------------------------------------


class TestGetParsedConfig:
    """get_parsed_config 测试。"""

    async def test_returns_default_when_no_config(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.get_toml_config_by_group_id.return_value = None
        result = await config_service.get_parsed_config("g1")
        # 应返回默认 ConfigSchema
        assert result.collecting.pickup_interval == 80
        assert result.collecting.msg_max_length == 35

    async def test_returns_parsed_config(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        toml_str = "[collecting]\npickup_interval = 200\nmsg_max_length = 50"
        mock_group_config_repo.get_toml_config_by_group_id.return_value = toml_str
        result = await config_service.get_parsed_config("g1")
        assert result.collecting.pickup_interval == 200
        assert result.collecting.msg_max_length == 50

    async def test_returns_default_on_invalid_toml(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.get_toml_config_by_group_id.return_value = "[broken ="
        result = await config_service.get_parsed_config("g1")
        # 解析失败应回退到默认值
        assert result.collecting.pickup_interval == 80


# ---------------------------------------------------------------------------
# get_config_value
# ---------------------------------------------------------------------------


class TestGetConfigValue:
    """get_config_value 测试。"""

    async def test_get_existing_value(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        toml_str = "[collecting]\npickup_interval = 120"
        mock_group_config_repo.get_toml_config_by_group_id.return_value = toml_str
        result = await config_service.get_config_value("g1", "collecting", "pickup_interval")
        assert result == 120

    async def test_get_default_value_when_no_config(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.get_toml_config_by_group_id.return_value = None
        result = await config_service.get_config_value("g1", "collecting", "pickup_interval")
        assert result == 80  # 默认值

    async def test_invalid_section_raises(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.get_toml_config_by_group_id.return_value = None
        with pytest.raises(ValidationException, match="配置节"):
            await config_service.get_config_value("g1", "nonexistent", "key")

    async def test_invalid_key_raises(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.get_toml_config_by_group_id.return_value = None
        with pytest.raises(ValidationException, match="配置项"):
            await config_service.get_config_value("g1", "collecting", "nonexistent_key")


# ---------------------------------------------------------------------------
# modify_single_value
# ---------------------------------------------------------------------------


class TestModifySingleValue:
    """modify_single_value 测试。"""

    async def test_modify_existing_config(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        toml_str = "[collecting]\npickup_interval = 80"
        mock_group_config_repo.get_toml_config_by_group_id.return_value = toml_str
        fake = GroupConfigs(group_id="g1", toml_config="")
        mock_group_config_repo.update_or_create_group_config.return_value = fake

        await config_service.modify_single_value("g1", "collecting.pickup_interval", 200)
        mock_group_config_repo.update_or_create_group_config.assert_awaited_once()
        call_args = mock_group_config_repo.update_or_create_group_config.call_args
        assert call_args[0][0] == "g1"
        assert "200" in call_args[0][1]

    async def test_modify_creates_config_when_none(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        mock_group_config_repo.get_toml_config_by_group_id.return_value = None
        fake = GroupConfigs(group_id="g1", toml_config="")
        mock_group_config_repo.update_or_create_group_config.return_value = fake

        await config_service.modify_single_value("g1", "collecting.pickup_interval", 150)
        mock_group_config_repo.update_or_create_group_config.assert_awaited_once()

    async def test_invalid_path_format_raises(
        self, config_service: ConfigService
    ) -> None:
        with pytest.raises(ValidationException, match="section.key"):
            await config_service.modify_single_value("g1", "only_one_part", 10)

    async def test_invalid_section_raises(
        self, config_service: ConfigService
    ) -> None:
        with pytest.raises(ValidationException, match="配置节"):
            await config_service.modify_single_value("g1", "nonexistent.key", 10)

    async def test_invalid_key_raises(
        self, config_service: ConfigService
    ) -> None:
        with pytest.raises(ValidationException, match="配置项"):
            await config_service.modify_single_value("g1", "collecting.nonexistent", 10)

    async def test_nonreloadable_item_raises(
        self, config_service: ConfigService
    ) -> None:
        with pytest.raises(ValidationException, match="不可修改"):
            await config_service.modify_single_value("g1", "llm.api_key_path", "new")


# ---------------------------------------------------------------------------
# fix_config_integrity
# ---------------------------------------------------------------------------


class TestFixConfigIntegrity:
    """fix_config_integrity 配置完整性修复测试。"""

    async def test_no_configs_returns_zero(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        """没有群组配置时应返回 0。"""
        mock_group_config_repo.get_all_group_configs.return_value = []
        result = await config_service.fix_config_integrity()
        assert result == 0
        mock_group_config_repo.update_or_create_group_config.assert_not_awaited()

    async def test_up_to_date_config_not_modified(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        """版本一致的配置不应被修改。"""
        import tomlkit
        from nonebot_plugin_zikequote3.config import ConfigSchema

        current_version = ConfigSchema().configure.cfg_version
        toml_str = f"[configure]\ncfg_version = {current_version}\n"
        fake = GroupConfigs(group_id="g1", toml_config=toml_str)
        mock_group_config_repo.get_all_group_configs.return_value = [fake]

        result = await config_service.fix_config_integrity()
        assert result == 0
        mock_group_config_repo.update_or_create_group_config.assert_not_awaited()

    async def test_outdated_config_gets_migrated(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        """版本不一致的配置应被迁移，保留旧值但更新版本号。"""
        import tomlkit
        from nonebot_plugin_zikequote3.config import ConfigSchema

        current_version = ConfigSchema().configure.cfg_version
        old_toml = (
            "[collecting]\npickup_interval = 200\n"
            "[configure]\ncfg_version = 1\n"
        )
        fake = GroupConfigs(group_id="g1", toml_config=old_toml)
        mock_group_config_repo.get_all_group_configs.return_value = [fake]
        mock_group_config_repo.update_or_create_group_config.return_value = fake

        result = await config_service.fix_config_integrity()
        assert result == 1
        mock_group_config_repo.update_or_create_group_config.assert_awaited_once()

        # 验证写回的 TOML 包含旧的自定义值和新版本号
        call_args = mock_group_config_repo.update_or_create_group_config.call_args
        written_toml = call_args[0][1]
        doc = tomlkit.parse(written_toml)
        assert doc["collecting"]["pickup_interval"] == 200 # type: ignore
        assert doc["configure"]["cfg_version"] == current_version # type: ignore

    async def test_multiple_groups_partial_migration(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        """多个群组中只有版本不一致的才被迁移。"""
        from nonebot_plugin_zikequote3.config import ConfigSchema

        current_version = ConfigSchema().configure.cfg_version
        up_to_date = GroupConfigs(
            group_id="g1",
            toml_config=f"[configure]\ncfg_version = {current_version}\n",
        )
        outdated = GroupConfigs(
            group_id="g2",
            toml_config="[configure]\ncfg_version = 0\n",
        )
        mock_group_config_repo.get_all_group_configs.return_value = [
            up_to_date, outdated
        ]
        mock_group_config_repo.update_or_create_group_config.return_value = outdated

        result = await config_service.fix_config_integrity()
        assert result == 1
        mock_group_config_repo.update_or_create_group_config.assert_awaited_once()

    async def test_invalid_toml_skipped(
        self, config_service: ConfigService, mock_group_config_repo: AsyncMock
    ) -> None:
        """无法解析的 TOML 配置应被跳过，不影响其他群组。"""
        broken = GroupConfigs(group_id="g1", toml_config="[broken =")
        mock_group_config_repo.get_all_group_configs.return_value = [broken]

        result = await config_service.fix_config_integrity()
        assert result == 0
        mock_group_config_repo.update_or_create_group_config.assert_not_awaited()
