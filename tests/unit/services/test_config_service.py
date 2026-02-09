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

    def test_invalid_literal_raises(self) -> None:
        with pytest.raises(ValidationException):
            ConfigService.parse_config_param(["key", "not_a_literal"])
