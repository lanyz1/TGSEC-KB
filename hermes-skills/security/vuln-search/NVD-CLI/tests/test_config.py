"""
AppConfig 配置管理模块测试
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from config import AppConfig


class TestAppConfigDefaults:
    """默认值测试"""

    def test_default_values(self):
        config = AppConfig()
        assert config.api_key == ""
        assert config.cache_enabled is True
        assert config.cache_ttl == 1800
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.max_threads == 0
        assert config.thread_delay == 0.6

    def test_cache_dir_default_is_project_cache(self):
        config = AppConfig()
        assert str(config.cache_dir).endswith("cache")


class TestAppConfigToFromDict:
    """序列化/反序列化测试"""

    def test_to_dict_contains_all_fields(self):
        config = AppConfig()
        d = config.to_dict()
        expected_keys = {
            "api_key", "cache_enabled", "cache_dir", "cache_ttl",
            "timeout", "max_retries", "max_threads", "thread_delay",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_converts_path_to_relative_str(self):
        config = AppConfig()
        d = config.to_dict()
        assert isinstance(d["cache_dir"], str)
        assert d["cache_dir"] == "cache"

    def test_to_dict_absolute_path_outside_project_stays_absolute(self):
        config = AppConfig(cache_dir=Path("/tmp/cache"))
        d = config.to_dict()
        assert d["cache_dir"] == str(Path("/tmp/cache"))

    def test_from_dict_roundtrip(self):
        original = AppConfig(api_key="test-key", cache_ttl=3600, max_threads=8)
        d = original.to_dict()
        restored = AppConfig.from_dict(d)
        assert restored.api_key == "test-key"
        assert restored.cache_ttl == 3600
        assert restored.max_threads == 8

    def test_from_dict_relative_path_resolves_to_project_root(self):
        restored = AppConfig.from_dict({"cache_dir": "cache"})
        from config import _project_root
        assert restored.cache_dir == _project_root() / "cache"

    def test_from_dict_absolute_path_stays_absolute(self):
        abs_path = Path("C:/tmp/cache") if os.name == "nt" else Path("/tmp/cache")
        restored = AppConfig.from_dict({"cache_dir": str(abs_path)})
        assert restored.cache_dir == abs_path

    def test_from_dict_missing_keys_use_defaults(self):
        restored = AppConfig.from_dict({})
        assert restored.api_key == ""
        assert restored.cache_enabled is True
        assert restored.cache_ttl == 1800


class TestAppConfigLoadSave:
    """文件 I/O 测试"""

    def test_load_nonexistent_file_returns_defaults(self):
        config = AppConfig.load(Path("/nonexistent/config.toml"))
        assert config.api_key == ""
        assert config.cache_ttl == 1800

    def test_save_and_load_roundtrip(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_config.toml"
            original = AppConfig(api_key="my-key", cache_ttl=7200, max_threads=4)
            original.save(path)

            loaded = AppConfig.load(path)
            assert loaded.api_key == "my-key"
            assert loaded.cache_ttl == 7200
            assert loaded.max_threads == 4

    def test_save_creates_parent_directory(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "config.toml"
            config = AppConfig()
            config.save(path)
            assert path.exists()


class TestAppConfigSetValue:
    """动态设置字段测试"""

    def test_set_string_field(self):
        config = AppConfig()
        config.set_value("api_key", "new-key")
        assert config.api_key == "new-key"

    def test_set_int_field(self):
        config = AppConfig()
        config.set_value("cache_ttl", "3600")
        assert config.cache_ttl == 3600

    def test_set_float_field(self):
        config = AppConfig()
        config.set_value("thread_delay", "1.5")
        assert config.thread_delay == 1.5

    def test_set_bool_field_true(self):
        config = AppConfig()
        config.set_value("cache_enabled", "true")
        assert config.cache_enabled is True

    def test_set_bool_field_false(self):
        config = AppConfig()
        config.set_value("cache_enabled", "false")
        assert config.cache_enabled is False

    def test_set_bool_field_yes(self):
        config = AppConfig()
        config.set_value("cache_enabled", "yes")
        assert config.cache_enabled is True

    def test_set_bool_field_zero(self):
        config = AppConfig()
        config.set_value("cache_enabled", "0")
        assert config.cache_enabled is False

    def test_set_path_field(self):
        config = AppConfig()
        config.set_value("cache_dir", "/tmp/cache")
        assert config.cache_dir == Path("/tmp/cache")

    def test_set_unknown_field_raises(self):
        config = AppConfig()
        with pytest.raises(AttributeError, match="Unknown config key"):
            config.set_value("nonexistent", "value")

    def test_set_invalid_int_raises(self):
        config = AppConfig()
        with pytest.raises(ValueError):
            config.set_value("cache_ttl", "not-a-number")


class TestAppConfigGetValue:
    """动态获取字段测试"""

    def test_get_existing_field(self):
        config = AppConfig(api_key="test")
        assert config.get_value("api_key") == "test"

    def test_get_unknown_field_raises(self):
        config = AppConfig()
        with pytest.raises(AttributeError, match="Unknown config key"):
            config.get_value("nonexistent")


class TestEffectiveMaxThreads:
    """effective_max_threads 测试"""

    def test_zero_returns_auto(self):
        config = AppConfig(max_threads=0)
        expected = (os.cpu_count() or 1) * 4
        assert config.effective_max_threads() == expected

    def test_positive_returns_value(self):
        config = AppConfig(max_threads=8)
        assert config.effective_max_threads() == 8

    def test_negative_returns_auto(self):
        config = AppConfig(max_threads=-1)
        expected = (os.cpu_count() or 1) * 4
        assert config.effective_max_threads() == expected
