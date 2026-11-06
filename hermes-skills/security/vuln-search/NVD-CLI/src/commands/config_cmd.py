"""
配置管理子命令

定义 `nvd config set` / `nvd config get` / `nvd config show` 三个子命令。
直接操作 AppConfig，不依赖 client 或 formatters。
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from config import AppConfig

config_app = typer.Typer(
    help=(
        "Configuration management\n\n"
        "Subcommands:\n"
        "  set <key> <value>   Set a config value\n"
        "  get <key>           Get a config value\n"
        "  show                Show all config values"
    ),
    no_args_is_help=True,
)


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Config key, e.g. api_key, cache_ttl")],
    value: Annotated[str, typer.Argument(help="Config value")],
) -> None:
    """
    Set a config value.

    Available config keys:
      api_key          NVD API Key (increases rate limit from 5/30s to 50/30s)
      cache_enabled    Enable local cache (true/false)
      cache_dir        Cache file directory
      cache_ttl        Cache TTL in seconds, default 1800
      timeout          HTTP request timeout in seconds, default 30
      max_retries      Max retries on failure, default 3
      max_threads      Max threads for batch queries, 0 = auto (CPU*4)
      thread_delay     Delay between thread launches in seconds, default 0.6

    Examples:

        nvd config set api_key your-api-key-here

        nvd config set cache_ttl 3600

        nvd config set cache_enabled false

        nvd config set max_threads 8
    """
    config = AppConfig.load()
    try:
        config.set_value(key, value)
    except (AttributeError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    config.save()
    typer.echo(f"Set {key} = {value}")


@config_app.command("get")
def config_get(
    key: Annotated[str, typer.Argument(help="Config key")],
) -> None:
    """
    Get a config value.

    Examples:

        nvd config get api_key

        nvd config get max_threads
    """
    config = AppConfig.load()
    try:
        val = config.get_value(key)
    except AttributeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"{key} = {val}")


@config_app.command("show")
def config_show() -> None:
    """
    Show all config values.

    API Key is masked (only first 4 and last 4 chars shown).
    max_threads=0 shows the auto-calculated value.

    Examples:

        nvd config show
    """
    config = AppConfig.load()

    console = Console()
    table = Table(title="NVD CLI Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    for key, value in config.to_dict().items():
        display_val = str(value)
        if key == "api_key" and display_val:
            display_val = display_val[:4] + "*" * (len(display_val) - 8) + display_val[-4:]
            if len(display_val) < 8:
                display_val = "*" * len(display_val)
        elif key == "max_threads" and value == 0:
            display_val = f"0 (auto = {config.effective_max_threads()})"

        table.add_row(key, display_val)

    console.print(table)
