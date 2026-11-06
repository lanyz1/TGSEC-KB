"""
输出格式化模块

提供统一的输出接口，支持 table / json / csv 三种格式。
本模块只依赖 models 和 rich，不依赖 client 或 config，
确保格式化逻辑与数据获取逻辑完全分离。

每种数据类型（CVE、CVEChange）对应一组格式化函数，
通过 OutputFormat 枚举选择具体实现。
"""

from __future__ import annotations

import csv
import io
import json
from enum import Enum
from typing import Any, Sequence

from rich.console import Console
from rich.table import Table

from models import CVE, CVEChange


class OutputFormat(str, Enum):
    """支持的输出格式"""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"


# ======================================================================
# CVE 格式化
# ======================================================================


def _cve_score_style(score: float) -> str:
    """根据 CVSS 评分返回 rich 样式标记颜色。"""
    if score >= 9.0:
        return "bold red"
    if score >= 7.0:
        return "red"
    if score >= 4.0:
        return "yellow"
    if score > 0.0:
        return "green"
    return "dim"


def _cve_severity_style(severity: str) -> str:
    """根据严重度返回 rich 样式标记颜色。"""
    mapping = {
        "CRITICAL": "bold red",
        "HIGH": "red",
        "MEDIUM": "yellow",
        "LOW": "green",
    }
    return mapping.get(severity.upper(), "dim")


def _truncate(text: str, max_len: int = 80) -> str:
    """截断过长文本，添加省略号。"""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_cve_table(cves: Sequence[CVE], *, console: Console | None = None) -> None:
    """
    以 Rich 表格格式输出 CVE 列表。

    Args:
        cves:    CVE 模型列表
        console: Rich Console 实例，默认创建新的
    """
    console = console or Console()

    table = Table(
        title="CVE Query Results",
        show_lines=True,
        expand=False,
    )
    table.add_column("CVE-ID", style="cyan", no_wrap=True, min_width=18)
    table.add_column("CVSS", justify="center", width=6)
    table.add_column("Severity", justify="center", width=8)
    table.add_column("Status", width=12)
    table.add_column("Published", width=12)
    table.add_column("Description", min_width=40)

    for cve in cves:
        score, severity = cve.metrics.best_score()
        score_str = f"{score:.1f}" if score > 0 else "-"
        severity_str = severity if severity != "N/A" else "-"

        table.add_row(
            cve.id,
            f"[{_cve_score_style(score)}]{score_str}[/]",
            f"[{_cve_severity_style(severity_str)}]{severity_str}[/]",
            cve.vuln_status,
            cve.published[:10] if cve.published else "-",
            _truncate(cve.en_description()),
        )

    console.print(table)


def format_cve_detail(cve: CVE, *, console: Console | None = None) -> None:
    """
    以详细格式输出单个 CVE 的完整信息。

    Args:
        cve:    CVE 模型实例
        console: Rich Console 实例
    """
    console = console or Console()

    score, severity = cve.metrics.best_score()

    console.print(f"\n[bold cyan]{cve.id}[/]")
    console.print(f"  Status:       {cve.vuln_status}")
    console.print(f"  Published:    {cve.published[:10] if cve.published else '-'}")
    console.print(f"  Modified:     {cve.last_modified[:10] if cve.last_modified else '-'}")

    if score > 0:
        console.print(
            f"  CVSS Score:   [{_cve_score_style(score)}]{score:.1f}[/] "
            f"[{_cve_severity_style(severity)}]({severity})[/]"
        )

    # 描述
    if cve.descriptions:
        console.print("\n  [bold]Description:[/]")
        for desc in cve.descriptions:
            console.print(f"    [{desc.lang}] {desc.value}")

    # CWE
    cwe_ids = cve.cwe_ids()
    if cwe_ids:
        console.print(f"\n  [bold]CWE:[/] {', '.join(cwe_ids)}")

    # CISA KEV
    if cve.cisa_exploit_add:
        console.print(f"\n  [bold red]CISA KEV:[/] Known Exploited")
        console.print(f"    Added: {cve.cisa_exploit_add}")
        if cve.cisa_required_action:
            console.print(f"    Required Action: {cve.cisa_required_action}")

    # CPE 配置
    if cve.configurations:
        console.print("\n  [bold]Affected Products:[/]")
        for cfg in cve.configurations:
            for node in cfg.nodes:
                for match in node.cpe_match:
                    console.print(f"    - {match.criteria}")

    # 参考
    if cve.references:
        console.print("\n  [bold]References:[/]")
        for ref in cve.references[:10]:
            tag_str = f" [{', '.join(ref.tags)}]" if ref.tags else ""
            console.print(f"    {ref.url}{tag_str}")
        if len(cve.references) > 10:
            console.print(f"    ... {len(cve.references)} total")

    console.print()


def format_cve_json(cves: Sequence[CVE]) -> str:
    """
    将 CVE 列表序列化为 JSON 字符串。

    Args:
        cves: CVE 模型列表

    Returns:
        格式化的 JSON 字符串
    """
    data = [cve.model_dump(by_alias=True, exclude_none=True) for cve in cves]
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_cve_csv(cves: Sequence[CVE]) -> str:
    """
    将 CVE 列表导出为 CSV 字符串。

    包含核心字段：CVE-ID、CVSS评分、严重度、状态、发布日期、描述。

    Args:
        cves: CVE 模型列表

    Returns:
        CSV 格式字符串
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["CVE-ID", "CVSS", "Severity", "Status", "Published", "Description"])

    for cve in cves:
        score, severity = cve.metrics.best_score()
        writer.writerow([
            cve.id,
            f"{score:.1f}" if score > 0 else "",
            severity,
            cve.vuln_status,
            cve.published[:10] if cve.published else "",
            cve.en_description().replace("\n", " "),
        ])

    return output.getvalue()


def output_cves(
    cves: Sequence[CVE],
    fmt: OutputFormat,
    *,
    detail: bool = False,
    console: Console | None = None,
) -> None:
    """
    CVE 输出的统一入口。

    根据格式枚举选择对应的格式化函数并输出。

    Args:
        cves:    CVE 模型列表
        fmt:     输出格式
        detail:  是否显示详情（仅 table 模式有效）
        console: Rich Console 实例
    """
    if fmt == OutputFormat.JSON:
        print(format_cve_json(cves))
    elif fmt == OutputFormat.CSV:
        print(format_cve_csv(cves), end="")
    else:
        # TABLE 模式
        if detail and len(cves) == 1:
            format_cve_detail(cves[0], console=console)
        else:
            format_cve_table(cves, console=console)


# ======================================================================
# CVE Change History 格式化
# ======================================================================


def format_history_table(
    changes: Sequence[CVEChange], *, console: Console | None = None
) -> None:
    """
    以 Rich 表格格式输出变更历史列表。

    Args:
        changes: CVEChange 模型列表
        console: Rich Console 实例
    """
    console = console or Console()

    table = Table(title="CVE Change History", show_lines=True)
    table.add_column("CVE-ID", style="cyan", no_wrap=True, min_width=18)
    table.add_column("Event", width=20)
    table.add_column("Time", width=20)
    table.add_column("Source", width=20)
    table.add_column("Details", min_width=40)

    for change in changes:
        details_str = "; ".join(
            f"{d.action} {d.type}" + (f": {d.new_value}" if d.new_value else "")
            for d in change.details[:3]
        )
        if len(change.details) > 3:
            details_str += f" ... (+{len(change.details) - 3})"

        table.add_row(
            change.cve_id,
            change.event_name,
            change.created[:19] if change.created else "-",
            change.source_identifier,
            _truncate(details_str, 100),
        )

    console.print(table)


def format_history_json(changes: Sequence[CVEChange]) -> str:
    """将变更历史列表序列化为 JSON 字符串。"""
    data = [ch.model_dump(by_alias=True, exclude_none=True) for ch in changes]
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_history_csv(changes: Sequence[CVEChange]) -> str:
    """将变更历史列表导出为 CSV 字符串。"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["CVE-ID", "Event", "Time", "Source", "Action", "Type", "OldValue", "NewValue"])

    for change in changes:
        if change.details:
            for d in change.details:
                writer.writerow([
                    change.cve_id,
                    change.event_name,
                    change.created[:19] if change.created else "",
                    change.source_identifier,
                    d.action,
                    d.type,
                    d.old_value,
                    d.new_value,
                ])
        else:
            writer.writerow([
                change.cve_id,
                change.event_name,
                change.created[:19] if change.created else "",
                change.source_identifier,
                "", "", "", "",
            ])

    return output.getvalue()


def output_history(
    changes: Sequence[CVEChange],
    fmt: OutputFormat,
    *,
    console: Console | None = None,
) -> None:
    """
    变更历史输出的统一入口。

    Args:
        changes: CVEChange 模型列表
        fmt:     输出格式
        console: Rich Console 实例
    """
    if fmt == OutputFormat.JSON:
        print(format_history_json(changes))
    elif fmt == OutputFormat.CSV:
        print(format_history_csv(changes), end="")
    else:
        format_history_table(changes, console=console)
