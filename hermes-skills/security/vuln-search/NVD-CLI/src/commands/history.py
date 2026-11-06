"""
CVE 变更历史子命令

定义 `nvd history get` / `nvd history search` 两个子命令。
本模块只负责参数解析和调用 client/formatters/batch，不包含业务逻辑。
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from batch import deduplicate_changes, read_ids_from_file, read_ids_from_stdin, run_batch
from client import NVDClient
from config import AppConfig
from formatters import OutputFormat, output_history

history_app = typer.Typer(
    help=(
        "CVE change history queries\n\n"
        "Subcommands:\n"
        "  get     Get change history for a CVE (supports batch)\n"
        "  search  Search change records by date or event type"
    ),
    no_args_is_help=True,
)


# ------------------------------------------------------------------
# nvd history get
# ------------------------------------------------------------------


@history_app.command("get")
def history_get(
    cve_id: Annotated[
        Optional[str],
        typer.Argument(help="CVE ID, or use - to read from stdin"),
    ] = None,
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Read CVE IDs from file (one per line)"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.TABLE,
    api_key: <REDACTED>
        Optional[str],
        typer.Option("--api-key", help="NVD API Key (overrides config file)"),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Disable cache"),
    ] = False,
) -> None:
    """
    Get the full change history for a CVE.

    Supports batch queries from file or stdin.
    Multiple IDs automatically use multi-threaded concurrent queries.

    Examples:

        nvd history get CVE-2021-44228                       Single query

        nvd history get --file ids.txt                       Batch from file

        cat ids.txt | nvd history get -                      Batch from stdin

        nvd history get CVE-2021-44228 -o json               JSON output

    File format (one CVE ID per line, # comments supported):

        CVE-2021-44228
        CVE-2024-3094
        # This is a comment
        CVE-2023-44487
    """
    # 收集 ID 列表
    ids = _collect_ids(cve_id, file)
    if not ids:
        typer.echo("No CVE IDs provided", err=True)
        raise typer.Exit(code=1)

    config = _load_config(api_key, no_cache)

    with NVDClient(config, no_cache=no_cache) as client:
        if len(ids) == 1:
            # 单个 ID 直接查
            changes, total = client.get_cve_history(ids[0])
            if not changes:
                typer.echo(f"No change history found for {ids[0]}", err=True)
                raise typer.Exit(code=1)
            typer.echo(f"{total} change records", err=True)
            output_history(changes, output)
        else:
            # 多个 ID 走线程池
            all_changes = run_batch(
                items=ids,
                handler=lambda cve_id: client.get_cve_history(cve_id)[0],
                max_threads=config.effective_max_threads(),
                thread_delay=config.thread_delay,
                progress_callback=lambda i, t, item: typer.echo(
                    f"[{i + 1}/{t}] Querying change history for {item}...", err=True
                ),
            )
            all_changes = deduplicate_changes(all_changes)
            if not all_changes:
                typer.echo("No change records found", err=True)
                raise typer.Exit(code=1)
            typer.echo(f"Found {len(all_changes)} change records (deduplicated)", err=True)
            output_history(all_changes, output)


# ------------------------------------------------------------------
# nvd history search
# ------------------------------------------------------------------


@history_app.command("search")
def history_search(
    change_start: Annotated[
        Optional[str],
        typer.Option("--start", help="Change start date (YYYY-MM-DD)"),
    ] = None,
    change_end: Annotated[
        Optional[str],
        typer.Option("--end", help="Change end date (YYYY-MM-DD)"),
    ] = None,
    event_name: Annotated[
        Optional[str],
        typer.Option("--event", help="Event type filter, e.g. 'Initial Analysis', 'CVE Rejected'"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Max results, 0 for all"),
    ] = 0,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.TABLE,
    api_key: <REDACTED>
        Optional[str],
        typer.Option("--api-key", help="NVD API Key (overrides config file)"),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Disable cache"),
    ] = False,
) -> None:
    """
    Search CVE change history by conditions.

    Filter by date range and/or event type. Date ranges exceeding 120 days are automatically split.
    Without --start/--end, all change records will be queried (may be very large).

    Common event types: Initial Analysis, CVE Modified, CVE Rejected,
    New CVE Received, CVE Translated, etc.

    Examples:

        nvd history search --start 2024-01-01 --end 2024-01-31

        nvd history search --event "CVE Rejected" --start 2024-06-01 --end 2024-06-30

        nvd history search --event "Initial Analysis" --start 2024-01-01 --end 2024-03-31 -l 50

        nvd history search --start 2024-01-01 --end 2024-12-31 -o csv > history.csv
    """
    config = _load_config(api_key, no_cache)

    # 日期格式转换
    start_fmt = _format_date(change_start)
    end_fmt = _format_date(change_end)

    with NVDClient(config, no_cache=no_cache) as client:
        if limit > 0:
            changes, total = client.get_cve_history(
                change_start=start_fmt,
                change_end=end_fmt,
                event_name=event_name,
                results_per_page=min(limit, 5000),
                start_index=0,
            )
            changes = changes[:limit]
        else:
            changes = list(
                client.iter_all_history(
                    change_start=start_fmt,
                    change_end=end_fmt,
                    event_name=event_name,
                )
            )

    if not changes:
        typer.echo("No matching change records found", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Found {len(changes)} change records", err=True)
    output_history(changes, output)


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------


def _collect_ids(
    cve_id: str | None,
    file: Path | None,
) -> list[str]:
    """
    从命令行参数、文件或 stdin 收集 CVE ID 列表。

    Args:
        cve_id: 命令行传入的单个 CVE ID，或 "-" 表示 stdin
        file:   --file 指定的文件路径

    Returns:
        ID 列表
    """
    if file is not None:
        try:
            return read_ids_from_file(file)
        except FileNotFoundError:
            typer.echo(f"File not found: {file}", err=True)
            raise typer.Exit(code=1)

    if cve_id == "-":
        return read_ids_from_stdin()

    if cve_id is not None:
        return [cve_id]

    return []


def _load_config(api_key: str | None, no_cache: bool) -> AppConfig:
    """加载配置，并用命令行参数覆盖。"""
    config = AppConfig.load()
    if api_key:
        <REDACTED> = api_key
    if no_cache:
        config.cache_enabled = False
    return config


def _format_date(date_str: str | None) -> str | None:
    """将 YYYY-MM-DD 转为 NVD ISO-8601 格式。"""
    if not date_str:
        return None
    return f"{date_str}T00:00:00.000"
