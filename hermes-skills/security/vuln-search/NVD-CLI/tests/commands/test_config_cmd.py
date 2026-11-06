"""
config 子命令测试
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from commands.config_cmd import config_app
from config import AppConfig


runner = CliRunner()


class TestConfigSetCommand:
    """config set 命令行测试"""

    @patch("commands.config_cmd.AppConfig.load")
    def test_set_api_key(self, mock_load):
        config = AppConfig()
        mock_load.return_value = config

        with patch.object(config, "save"):
            result = runner.invoke(config_app, ["set", "api_key", "test-key-123"])
            assert result.exit_code == 0
            assert "Set" in result.output
            assert config.api_key == "test-key-123"

    @patch("commands.config_cmd.AppConfig.load")
    def test_set_cache_ttl(self, mock_load):
        config = AppConfig()
        mock_load.return_value = config

        with patch.object(config, "save"):
            result = runner.invoke(config_app, ["set", "cache_ttl", "3600"])
            assert result.exit_code == 0
            assert config.cache_ttl == 3600

    @patch("commands.config_cmd.AppConfig.load")
    def test_set_unknown_key_fails(self, mock_load):
        config = AppConfig()
        mock_load.return_value = config

        result = runner.invoke(config_app, ["set", "nonexistent", "value"])
        assert result.exit_code == 1
        assert "Error" in result.output


class TestConfigGetCommand:
    """config get 命令行测试"""

    @patch("commands.config_cmd.AppConfig.load")
    def test_get_api_key(self, mock_load):
        config = AppConfig(api_key="my-key")
        mock_load.return_value = config

        result = runner.invoke(config_app, ["get", "api_key"])
        assert result.exit_code == 0
        assert "my-key" in result.output

    @patch("commands.config_cmd.AppConfig.load")
    def test_get_unknown_key_fails(self, mock_load):
        config = AppConfig()
        mock_load.return_value = config

        result = runner.invoke(config_app, ["get", "nonexistent"])
        assert result.exit_code == 1


class TestConfigShowCommand:
    """config show 命令行测试"""

    @patch("commands.config_cmd.AppConfig.load")
    def test_show_displays_all_fields(self, mock_load):
        config = AppConfig(api_key="<REDACTED>")
        mock_load.return_value = config

        result = runner.invoke(config_app, ["show"])
        assert result.exit_code == 0
        assert "api_key" in result.output
        assert "cache_enabled" in result.output
        assert "cache_ttl" in result.output

    @patch("commands.config_cmd.AppConfig.load")
    def test_show_masks_api_key(self, mock_load):
        config = AppConfig(api_key="<REDACTED>")
        mock_load.return_value = config

        result = runner.invoke(config_app, ["show"])
        assert result.exit_code == 0
        assert "a9a3" in result.output
        assert "63d5" in result.output
        assert "a9a30619-9294-423d-9286-1f79037f63d5" not in result.output

    @patch("commands.config_cmd.AppConfig.load")
    def test_show_max_threads_auto(self, mock_load):
        config = AppConfig(max_threads=0)
        mock_load.return_value = config

        result = runner.invoke(config_app, ["show"])
        assert "auto" in result.output
