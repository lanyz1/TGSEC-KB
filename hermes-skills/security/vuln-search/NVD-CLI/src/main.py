"""
CLI 入口模块

创建 typer 应用并注册所有子命令。
本模块是整个应用的组装层，负责将各独立模块连接在一起，
自身不包含任何业务逻辑。
"""

from __future__ import annotations

import logging
from typing import Optional

import typer

from __init__ import __version__
from commands.cve import cve_app
from commands.config_cmd import config_app
from commands.history import history_app

# 创建顶层 typer 应用
app = typer.Typer(
    name="nvd",
    help=(
        "NVD (National Vulnerability Database) CLI query tool\n\n"
        "Query CVE vulnerability info and change history via NVD REST API v2.0, "
        "with batch queries, multi-threading, auto rate-limiting and local caching.\n\n"
        "Subcommands:\n"
        "  cve get <CVE-ID>            Get one or more CVE details\n"
        "  cve search -k <keyword>     Search CVEs by keyword/conditions\n"
        "  cve latest -d <days>        Show CVEs published in the last N days\n"
        "  history get <CVE-ID>        Get change history for a CVE\n"
        "  history search --start ...  Search change records by date/event type\n"
        "  config set <key> <value>    Set a config value\n"
        "  config get <key>            Get a config value\n"
        "  config show                 Show all config values\n\n"
        "Quick start:\n"
        "  nvd cve get CVE-2021-44228\n"
        "  nvd cve search -k log4j --severity-v3 CRITICAL\n"
        "  nvd cve latest -d 7 -s CRITICAL\n"
        "  nvd history get CVE-2021-44228\n"
        "  nvd config set api_key <your-key>\n\n"
        "API rate limits: No Key 5 req/30s | With Key 50 req/30s"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# ------------------------------------------------------------------
# 注册子命令
# ------------------------------------------------------------------

app.add_typer(cve_app, name="cve")
app.add_typer(history_app, name="history")
app.add_typer(config_app, name="config")


# ------------------------------------------------------------------
# 版本命令
# ------------------------------------------------------------------


def _version_callback(value: bool) -> None:
    """打印版本号并退出。"""
    if value:
        typer.echo(f"nvd-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version",
        callback=_version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose logging",
    ),
) -> None:
    """
    NVD (National Vulnerability Database) CLI query tool.

    Query CVE vulnerability info and change history via NVD REST API v2.0,
    with batch queries, multi-threading, auto rate-limiting and local caching.

    Subcommands:
      cve get <CVE-ID>              Get one or more CVE details
      cve search -k <keyword>       Search CVEs by keyword/conditions
      cve latest -d <days>          Show CVEs published in the last N days
      history get <CVE-ID>          Get change history for a CVE
      history search --start ...    Search change records by date/event type
      config set <key> <value>      Set a config value
      config get <key>              Get a config value
      config show                   Show all config values

    Quick start:

        nvd cve get CVE-2021-44228

        nvd cve search -k log4j --severity-v3 CRITICAL

        nvd cve latest -d 7 -s CRITICAL

        nvd history get CVE-2021-44228

        nvd config set api_key <your-key>

    API rate limits:

        No API Key: 5 req/30s | With API Key: 50 req/30s
    """
    # 配置日志级别
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.WARNING,
            format="%(message)s",
        )
