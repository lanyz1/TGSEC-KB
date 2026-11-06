"""
配置管理模块

负责读写项目目录下 config.toml 配置文件，提供统一的配置访问接口。
与其它模块完全解耦：其它模块只通过 AppConfig 的实例获取配置，不直接操作文件。
所有配置和缓存文件均存放在项目目录下，不写入用户主目录。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w


def _project_root() -> Path:
    """
    获取项目根目录。

    以 main.py 所在目录为项目根目录。
    src/config.py -> 往上一级就是项目根目录。
    """
    return Path(__file__).resolve().parent.parent


# 配置文件和缓存目录（均在项目根目录下）
_DEFAULT_FILE = _project_root() / "config.toml"
_DEFAULT_CACHE_DIR = _project_root() / "cache"


@dataclass
class AppConfig:
    """
    应用配置的内存表示。

    Attributes:
        api_key:        NVD API Key，为空则使用匿名限流策略
        cache_enabled:  是否启用本地 HTTP 缓存
        cache_dir:      缓存文件存放目录
        cache_ttl:      缓存过期时间（秒），默认 1800 = 30 分钟
        timeout:        HTTP 请求超时（秒）
        max_retries:    请求失败最大重试次数
        max_threads:    批量查询最大线程数，0 表示自动 = CPU核数*4
        thread_delay:   每启动两个线程间的间歇（秒）
    """

    api_key: str = ""
    cache_enabled: bool = True
    cache_dir: Path = field(default_factory=lambda: _DEFAULT_CACHE_DIR)
    cache_ttl: int = 1800
    timeout: int = 30
    max_retries: int = 3
    max_threads: int = 0
    thread_delay: float = 0.6

    # ------------------------------------------------------------------
    # 序列化 / 反序列化
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """将配置转为可写入 TOML 的字典，Path 转为相对路径字符串。"""
        try:
            rel = self.cache_dir.resolve().relative_to(_project_root())
            cache_dir_str = str(rel)
        except ValueError:
            cache_dir_str = str(self.cache_dir)
        return {
            "api_key": self.api_key,
            "cache_enabled": self.cache_enabled,
            "cache_dir": cache_dir_str,
            "cache_ttl": self.cache_ttl,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "max_threads": self.max_threads,
            "thread_delay": self.thread_delay,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        """从字典（通常来自 TOML 解析）构建 AppConfig。相对路径自动拼项目根目录。"""
        raw_dir = data.get("cache_dir", str(_DEFAULT_CACHE_DIR))
        p = Path(raw_dir)
        if not p.is_absolute():
            p = _project_root() / p
        return cls(
            api_key=data.get("api_key", ""),
            cache_enabled=data.get("cache_enabled", True),
            cache_dir=p,
            cache_ttl=data.get("cache_ttl", 1800),
            timeout=data.get("timeout", 30),
            max_retries=data.get("max_retries", 3),
            max_threads=data.get("max_threads", 0),
            thread_delay=data.get("thread_delay", 0.6),
        )

    # ------------------------------------------------------------------
    # 文件 I/O
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        """
        从 TOML 文件加载配置。

        如果文件不存在，返回默认配置而不报错。

        Args:
            path: 配置文件路径，默认项目目录下 config.toml

        Returns:
            解析后的 AppConfig 实例
        """
        path = path or _DEFAULT_FILE
        if not path.exists():
            return cls()
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.from_dict(data)

    def save(self, path: Path | None = None) -> None:
        """
        将当前配置写入 TOML 文件。

        自动创建父目录。

        Args:
            path: 配置文件路径，默认项目目录下 config.toml
        """
        path = path or _DEFAULT_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            tomli_w.dump(self.to_dict(), f)

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------

    def set_value(self, key: str, value: str) -> None:
        """
        动态设置一个配置字段。

        Args:
            key:   字段名（与 dataclass 字段对应）
            value: 字段值的字符串表示，会自动做类型转换

        Raises:
            AttributeError: 字段名不存在
            ValueError:     类型转换失败
        """
        if not hasattr(self, key):
            raise AttributeError(f"Unknown config key: {key}")

        field_type = self.__dataclass_fields__[key].type

        # 根据字段类型做转换
        if field_type is bool or field_type == "bool":
            parsed = value.lower() in ("true", "1", "yes")
        elif field_type is int or field_type == "int":
            parsed = int(value)
        elif field_type is float or field_type == "float":
            parsed = float(value)
        elif field_type is Path or field_type == "Path":
            parsed = Path(value)
        else:
            parsed = value

        setattr(self, key, parsed)

    def get_value(self, key: str) -> Any:
        """
        获取一个配置字段的值。

        Args:
            key: 字段名

        Returns:
            字段值

        Raises:
            AttributeError: 字段名不存在
        """
        if not hasattr(self, key):
            raise AttributeError(f"Unknown config key: {key}")
        return getattr(self, key)

    def effective_max_threads(self) -> int:
        """
        获取实际最大线程数。

        如果 max_threads 为 0，则自动计算为 CPU 核数 * 4。

        Returns:
            实际最大线程数
        """
        if self.max_threads <= 0:
            return (os.cpu_count() or 1) * 4
        return self.max_threads
