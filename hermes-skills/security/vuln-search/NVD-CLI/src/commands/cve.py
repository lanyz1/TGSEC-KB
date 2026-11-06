"""
CVE 查询子命令

定义 `nvd cve get` / `nvd cve search` / `nvd cve latest` 三个子命令。
本模块只负责参数解析和调用 client/formatters/batch，不包含业务逻辑。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer

from batch import deduplicate_cves, read_ids_from_file, read_ids_from_stdin, read_queries_from_file, run_batch
from client import NVDClient
from config import AppConfig
from formatters import OutputFormat, output_cves
from models import CVE

cve_app = typer.Typer(
    help=(
        "CVE vulnerability queries\n\n"
        "Subcommands:\n"
        "  get     Get CVE details by ID (supports batch)\n"
        "  search  Search CVEs by keyword, severity, date, etc.\n"
        "  latest  Show CVEs published in the last N days"
    ),
    no_args_is_help=True,
)


# ------------------------------------------------------------------
# nvd cve get
# ------------------------------------------------------------------


@cve_app.command("get")
def cve_get(
    cve_ids: Annotated[
        Optional[list[str]],
        typer.Argument(help="CVE ID(s), or use - to read from stdin"),
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
    Get details for one or more CVEs.

    Supports three input methods: command-line args, file, or stdin.
    Small batches are queried directly; 3+ IDs use multi-threaded batch query.

    Examples:

        nvd cve get CVE-2021-44228                          Single query

        nvd cve get CVE-2021-44228 CVE-2021-45046           Multiple queries

        nvd cve get --file ids.txt                          Batch from file

        cat ids.txt | nvd cve get -                         Batch from stdin

        nvd cve get CVE-2021-44228 -o json                  JSON output

    File format (one CVE ID per line, # comments supported):

        CVE-2021-44228
        CVE-2021-45046
        # This is a comment
        CVE-2023-44487
    """
    # 收集 ID 列表
    ids = _collect_ids(cve_ids, file)
    if not ids:
        typer.echo("No CVE IDs provided", err=True)
        raise typer.Exit(code=1)

    config = _load_config(api_key, no_cache)

    # 分批：每批 ≤100 个走 cveIds 参数
    batches = [ids[i:i + 100] for i in range(0, len(ids), 100)]

    with NVDClient(config, no_cache=no_cache) as client:
        if len(batches) == 1 and len(batches[0]) <= 2:
            # 少量 ID 直接查，无需线程池
            if len(batches[0]) == 1:
                cve = client.get_cve(batches[0][0])
                if cve is None:
                    typer.echo(f"Not found: {batches[0][0]}", err=True)
                    raise typer.Exit(code=1)
                output_cves([cve], output, detail=True)
            else:
                cves = client.get_cves_batch(batches[0])
                if not cves:
                    typer.echo("No matching CVEs found", err=True)
                    raise typer.Exit(code=1)
                output_cves(cves, output, detail=True)
        else:
            # 多批次走线程池
            all_cves = run_batch(
                items=batches,
                handler=lambda batch: client.get_cves_batch(batch),
                max_threads=config.effective_max_threads(),
                thread_delay=config.thread_delay,
                progress_callback=lambda i, t, item: typer.echo(
                    f"[{i + 1}/{t}] Querying {len(item)} CVEs...", err=True
                ),
            )
            all_cves = deduplicate_cves(all_cves)
            if not all_cves:
                typer.echo("No matching CVEs found", err=True)
                raise typer.Exit(code=1)
            typer.echo(f"Found {len(all_cves)} CVEs", err=True)
            output_cves(all_cves, output, detail=True)


# ------------------------------------------------------------------
# nvd cve search
# ------------------------------------------------------------------


@cve_app.command("search")
def cve_search(
    keyword: Annotated[
        Optional[str],
        typer.Option("--keyword", "-k", help="Keyword to search CVE descriptions"),
    ] = None,
    exact: Annotated[
        bool,
        typer.Option("--exact", help="Exact match for keyword phrase"),
    ] = False,
    cpe: Annotated[
        Optional[str],
        typer.Option("--cpe", help="Filter by CPE name"),
    ] = None,
    is_vulnerable: Annotated[
        bool,
        typer.Option("--is-vulnerable", help="Only return CPEs marked as vulnerable (requires --cpe)"),
    ] = False,
    severity_v2: Annotated[
        Optional[str],
        typer.Option("--severity-v2", help="CVSSv2 severity: LOW/MEDIUM/HIGH"),
    ] = None,
    severity_v3: Annotated[
        Optional[str],
        typer.Option("--severity-v3", help="CVSSv3 severity: LOW/MEDIUM/HIGH/CRITICAL"),
    ] = None,
    severity_v4: Annotated[
        Optional[str],
        typer.Option("--severity-v4", help="CVSSv4 severity: LOW/MEDIUM/HIGH/CRITICAL"),
    ] = None,
    cvss_v2_metrics: Annotated[
        Optional[str],
        typer.Option("--cvss-v2-metrics", help="CVSSv2 vector string"),
    ] = None,
    cvss_v3_metrics: Annotated[
        Optional[str],
        typer.Option("--cvss-v3-metrics", help="CVSSv3 vector string"),
    ] = None,
    cvss_v4_metrics: Annotated[
        Optional[str],
        typer.Option("--cvss-v4-metrics", help="CVSSv4 vector string"),
    ] = None,
    cwe: Annotated[
        Optional[str],
        typer.Option("--cwe", help="Filter by CWE ID, e.g. CWE-287"),
    ] = None,
    has_kev: Annotated[
        bool,
        typer.Option("--has-kev", help="Only CVEs in CISA KEV catalog"),
    ] = False,
    has_cert_alerts: Annotated[
        bool,
        typer.Option("--has-cert-alerts", help="Include US-CERT alerts"),
    ] = False,
    has_cert_notes: Annotated[
        bool,
        typer.Option("--has-cert-notes", help="Include CERT/CC vulnerability notes"),
    ] = False,
    pub_start: Annotated[
        Optional[str],
        typer.Option("--pub-start", help="Published start date (YYYY-MM-DD)"),
    ] = None,
    pub_end: Annotated[
        Optional[str],
        typer.Option("--pub-end", help="Published end date (YYYY-MM-DD)"),
    ] = None,
    mod_start: Annotated[
        Optional[str],
        typer.Option("--mod-start", help="Last modified start date (YYYY-MM-DD)"),
    ] = None,
    mod_end: Annotated[
        Optional[str],
        typer.Option("--mod-end", help="Last modified end date (YYYY-MM-DD)"),
    ] = None,
    kev_start: Annotated[
        Optional[str],
        typer.Option("--kev-start", help="KEV added start date (YYYY-MM-DD)"),
    ] = None,
    kev_end: Annotated[
        Optional[str],
        typer.Option("--kev-end", help="KEV added end date (YYYY-MM-DD)"),
    ] = None,
    status: Annotated[
        Optional[list[str]],
        typer.Option("--status", help="Vulnerability status: Analyzed/Modified/Deferred/..."),
    ] = None,
    cve_tag: Annotated[
        Optional[str],
        typer.Option("--cve-tag", help="CVE tag: disputed/unsupported-when-assigned/..."),
    ] = None,
    source: Annotated[
        Optional[str],
        typer.Option("--source", help="Source identifier"),
    ] = None,
    virtual_match: Annotated[
        Optional[str],
        typer.Option("--virtual-match", help="CPE virtual match string"),
    ] = None,
    version_start: Annotated[
        Optional[str],
        typer.Option("--version-start", help="Version range start (requires --virtual-match)"),
    ] = None,
    version_start_type: Annotated[
        Optional[str],
        typer.Option("--version-start-type", help="Start version type: including/excluding"),
    ] = None,
    version_end: Annotated[
        Optional[str],
        typer.Option("--version-end", help="Version range end (requires --virtual-match)"),
    ] = None,
    version_end_type: Annotated[
        Optional[str],
        typer.Option("--version-end-type", help="End version type: including/excluding"),
    ] = None,
    no_rejected: Annotated[
        bool,
        typer.Option("--no-rejected", help="Exclude rejected CVEs"),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Max results, 0 for all"),
    ] = 0,
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Read query conditions from JSON file"),
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
    Search CVEs by conditions.

    Supports keyword, severity, CPE, CWE, date range and other filters.
    Also supports batch search from a JSON file.
    Date ranges exceeding 120 days are automatically split.

    Examples:

        nvd cve search -k log4j                             Keyword search

        nvd cve search -k log4j --severity-v3 CRITICAL     Keyword + severity

        nvd cve search --cwe CWE-79 --severity-v3 HIGH    Filter by CWE

        nvd cve search --pub-start 2024-01-01 --pub-end 2024-12-31

        nvd cve search --cpe "cpe:2.3:a:apache:log4j" --is-vulnerable

        nvd cve search --has-kev --no-rejected -o csv     CISA KEV + CSV output

        nvd cve search --file queries.json                 Batch search

    Batch search JSON file format:

        [
          {"keyword": "openssl", "severity_v3": "CRITICAL", "limit": 5},
          {"keyword": "nginx", "pub_start": "2024-01-01", "pub_end": "2024-12-31"},
          {"cwe": "CWE-79", "severity_v3": "HIGH", "limit": 10}
        ]

    Supported JSON field names (correspond to CLI options):

        keyword, exact, cpe, is_vulnerable, severity_v2, severity_v3,
        severity_v4, cvss_v2_metrics, cvss_v3_metrics, cvss_v4_metrics,
        cwe, has_kev, has_cert_alerts, has_cert_notes, pub_start, pub_end,
        mod_start, mod_end, kev_start, kev_end, status, cve_tag, source,
        virtual_match, version_start, version_start_type, version_end,
        version_end_type, no_rejected, limit
    """
    config = _load_config(api_key, no_cache)

    with NVDClient(config, no_cache=no_cache) as client:
        # 从文件读取多组查询条件
        if file is not None:
            try:
                queries = read_queries_from_file(file)
            except FileNotFoundError:
                typer.echo(f"File not found: {file}", err=True)
                raise typer.Exit(code=1)
            if not queries:
                typer.echo("Query file is empty", err=True)
                raise typer.Exit(code=1)

            all_cves = run_batch(
                items=queries,
                handler=lambda q: _search_single(client, q, limit)[0],
                max_threads=config.effective_max_threads(),
                thread_delay=config.thread_delay,
                progress_callback=lambda i, t, item: typer.echo(
                    f"[{i + 1}/{t}] Executing query...", err=True
                ),
            )
            all_cves = deduplicate_cves(all_cves)
            if not all_cves:
                typer.echo("No matching CVEs found", err=True)
                raise typer.Exit(code=1)
            typer.echo(f"Found {len(all_cves)} results (deduplicated)", err=True)
            output_cves(all_cves, output)
            return

        # 单次查询（原有逻辑）
        pub_start_fmt = _format_date(pub_start)
        pub_end_fmt = _format_date(pub_end)
        mod_start_fmt = _format_date(mod_start)
        mod_end_fmt = _format_date(mod_end)
        kev_start_fmt = _format_date(kev_start)
        kev_end_fmt = _format_date(kev_end)

        if limit > 0:
            cves, total = client.search_cves(
                keyword=keyword,
                keyword_exact=exact,
                cpe_name=cpe,
                is_vulnerable=is_vulnerable,
                cvss_v2_severity=severity_v2,
                cvss_v3_severity=severity_v3,
                cvss_v4_severity=severity_v4,
                cvss_v2_metrics=cvss_v2_metrics,
                cvss_v3_metrics=cvss_v3_metrics,
                cvss_v4_metrics=cvss_v4_metrics,
                cwe_id=cwe,
                has_kev=has_kev,
                has_cert_alerts=has_cert_alerts,
                has_cert_notes=has_cert_notes,
                pub_start=pub_start_fmt,
                pub_end=pub_end_fmt,
                mod_start=mod_start_fmt,
                mod_end=mod_end_fmt,
                kev_start=kev_start_fmt,
                kev_end=kev_end_fmt,
                vuln_statuses=status,
                cve_tag=cve_tag,
                source_identifier=source,
                virtual_match_string=virtual_match,
                version_start=version_start,
                version_start_type=version_start_type,
                version_end=version_end,
                version_end_type=version_end_type,
                no_rejected=no_rejected,
                results_per_page=min(limit, 2000),
                start_index=0,
            )
            cves = cves[:limit]
        else:
            cves = list(
                client.iter_all_cves(
                    keyword=keyword,
                    keyword_exact=exact,
                    cpe_name=cpe,
                    is_vulnerable=is_vulnerable,
                    cvss_v2_severity=severity_v2,
                    cvss_v3_severity=severity_v3,
                    cvss_v4_severity=severity_v4,
                    cvss_v2_metrics=cvss_v2_metrics,
                    cvss_v3_metrics=cvss_v3_metrics,
                    cvss_v4_metrics=cvss_v4_metrics,
                    cwe_id=cwe,
                    has_kev=has_kev,
                    has_cert_alerts=has_cert_alerts,
                    has_cert_notes=has_cert_notes,
                    pub_start=pub_start_fmt,
                    pub_end=pub_end_fmt,
                    mod_start=mod_start_fmt,
                    mod_end=mod_end_fmt,
                    kev_start=kev_start_fmt,
                    kev_end=kev_end_fmt,
                    vuln_statuses=status,
                    cve_tag=cve_tag,
                    source_identifier=source,
                    virtual_match_string=virtual_match,
                    version_start=version_start,
                    version_start_type=version_start_type,
                    version_end=version_end,
                    version_end_type=version_end_type,
                    no_rejected=no_rejected,
                )
            )

    if not cves:
        typer.echo("No matching CVEs found", err=True)
        raise typer.Exit(code=1)

    cves = _filter_by_severity(cves, severity_v2, severity_v3, severity_v4)

    if not cves:
        typer.echo("No matching CVEs found", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Found {len(cves)} results", err=True)
    output_cves(cves, output)


# ------------------------------------------------------------------
# nvd cve latest
# ------------------------------------------------------------------


@cve_app.command("latest")
def cve_latest(
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="CVEs published in the last N days"),
    ] = 7,
    severity: Annotated[
        Optional[str],
        typer.Option("--severity", "-s", help="Filter by severity: LOW/MEDIUM/HIGH/CRITICAL"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Max results"),
    ] = 50,
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
    Show CVEs published in the last N days.

    A shortcut for cve search that auto-calculates the date range.
    Defaults to the last 7 days; can filter by severity.

    Examples:

        nvd cve latest                               Last 7 days

        nvd cve latest -d 30                         Last 30 days

        nvd cve latest -d 7 -s CRITICAL              Critical CVEs in last 7 days

        nvd cve latest -d 30 -s CRITICAL -l 20       Limit to 20 results

        nvd cve latest -d 90 -o csv > latest.csv     Export as CSV
    """
    config = _load_config(api_key, no_cache)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    pub_start = _format_datetime(start)
    pub_end = _format_datetime(now)

    with NVDClient(config, no_cache=no_cache) as client:
        cves, total = client.search_cves(
            pub_start=pub_start,
            pub_end=pub_end,
            cvss_v3_severity=severity,
            no_rejected=True,
            results_per_page=min(limit, 2000),
            start_index=0,
        )
        cves = cves[:limit]

    cves = _filter_by_severity(cves, None, severity, None)

    if not cves:
        typer.echo(f"No new CVEs in the last {days} days", err=True)
        raise typer.Exit(code=0)

    typer.echo(f"{total} CVEs published in the last {days} days (showing top {len(cves)})", err=True)
    output_cves(cves, output)


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------


def _filter_by_severity(
    cves: list[CVE],
    severity_v2: str | None,
    severity_v3: str | None,
    severity_v4: str | None,
) -> list[CVE]:
    """
    客户端二次过滤严重度。

    NVD API 的 cvssV2/V3/V4Severity 参数不严格过滤，
    会返回不符合指定严重度的结果，因此需要在客户端再次筛选。

    Args:
        cves:         API 返回的 CVE 列表
        severity_v2:  用户指定的 CVSSv2 严重度
        severity_v3:  用户指定的 CVSSv3 严重度
        severity_v4:  用户指定的 CVSSv4 严重度

    Returns:
        过滤后的 CVE 列表
    """
    if not severity_v2 and not severity_v3 and not severity_v4:
        return cves

    filtered: list[CVE] = []
    for cve in cves:
        score, severity = cve.metrics.best_score()
        if severity_v3 and severity.upper() != severity_v3.upper():
            continue
        if severity_v2 and severity.upper() != severity_v2.upper():
            continue
        if severity_v4 and severity.upper() != severity_v4.upper():
            continue
        filtered.append(cve)
    return filtered


def _collect_ids(
    cve_ids: list[str] | None,
    file: Path | None,
) -> list[str]:
    """
    从命令行参数、文件或 stdin 收集 CVE ID 列表。

    优先级：--file > stdin(-) > 命令行参数

    Args:
        cve_ids: 命令行传入的 CVE ID 列表
        file:    --file 指定的文件路径

    Returns:
        合并后的 ID 列表
    """
    if file is not None:
        try:
            return read_ids_from_file(file)
        except FileNotFoundError:
            typer.echo(f"File not found: {file}", err=True)
            raise typer.Exit(code=1)

    if cve_ids and "-" in cve_ids:
        # 从 stdin 读取
        ids = read_ids_from_stdin()
        # 也可能同时传了其它 ID
        other = [i for i in cve_ids if i != "-"]
        return other + ids

    return cve_ids or []


_QUERY_KEY_MAP: dict[str, str] = {
    "keyword": "keyword",
    "exact": "keyword_exact",
    "cpe": "cpe_name",
    "is_vulnerable": "is_vulnerable",
    "severity_v2": "cvss_v2_severity",
    "severity_v3": "cvss_v3_severity",
    "severity_v4": "cvss_v4_severity",
    "cvss_v2_metrics": "cvss_v2_metrics",
    "cvss_v3_metrics": "cvss_v3_metrics",
    "cvss_v4_metrics": "cvss_v4_metrics",
    "cwe": "cwe_id",
    "has_kev": "has_kev",
    "has_cert_alerts": "has_cert_alerts",
    "has_cert_notes": "has_cert_notes",
    "pub_start": "pub_start",
    "pub_end": "pub_end",
    "mod_start": "mod_start",
    "mod_end": "mod_end",
    "kev_start": "kev_start",
    "kev_end": "kev_end",
    "status": "vuln_statuses",
    "cve_tag": "cve_tag",
    "source": "source_identifier",
    "virtual_match": "virtual_match_string",
    "version_start": "version_start",
    "version_start_type": "version_start_type",
    "version_end": "version_end",
    "version_end_type": "version_end_type",
    "no_rejected": "no_rejected",
}


def _search_single(
    client: NVDClient, query: dict, limit: int = 0
) -> tuple[list[CVE], int]:
    """
    用单组查询条件执行搜索。

    将 JSON 文件中的键名映射为 search_cves 的参数名。

    Args:
        client: NVDClient 实例
        query:  查询条件字典
        limit:  最大返回数量

    Returns:
        (CVE 列表, 总结果数)
    """
    mapped: dict = {}
    for key, value in query.items():
        if key == "limit":
            continue
        mapped_key = _QUERY_KEY_MAP.get(key)
        if mapped_key is None:
            continue
        mapped[mapped_key] = value

    for key in ("pub_start", "pub_end", "mod_start", "mod_end", "kev_start", "kev_end"):
        if key in mapped and mapped[key]:
            mapped[key] = _format_date(mapped[key])

    query_limit = limit or query.get("limit", 0)

    if query_limit > 0:
        mapped.setdefault("results_per_page", min(query_limit, 2000))
        mapped.setdefault("start_index", 0)
        cves, total = client.search_cves(**mapped)
        return cves[:query_limit], total

    return client.search_cves(**mapped)


def _load_config(api_key: str | None, no_cache: bool) -> AppConfig:
    """
    加载配置，并用命令行参数覆盖。

    Args:
        api_key:  命令行传入的 API Key，优先级高于配置文件
        no_cache: 是否禁用缓存

    Returns:
        合并后的 AppConfig 实例
    """
    config = AppConfig.load()
    if api_key:
        <REDACTED> = api_key
    if no_cache:
        config.cache_enabled = False
    return config


def _format_date(date_str: str | None) -> str | None:
    """
    将 YYYY-MM-DD 格式转为 NVD 要求的 ISO-8601 完整格式。

    Args:
        date_str: 日期字符串，如 "2024-01-01"

    Returns:
        如 "2024-01-01T00:00:00.000"，输入为 None 时返回 None
    """
    if not date_str:
        return None
    return f"{date_str}T00:00:00.000"


def _format_datetime(dt: datetime) -> str:
    """
    将 datetime 转为 NVD 要求的 ISO-8601 格式字符串。

    Args:
        dt: datetime 实例

    Returns:
        如 "2024-01-01T00:00:00.000"
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000")
