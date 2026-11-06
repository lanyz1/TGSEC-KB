"""
输出格式化模块测试
"""

import csv
import io
import json

import pytest

from formatters import (
    OutputFormat, format_cve_json, format_cve_csv,
    format_history_json, format_history_csv,
    _cve_score_style, _cve_severity_style, _truncate,
)
from models import CVE, CVEChange, ChangeDetail, Description, Metrics, CVSSv3Metric, CVSSv3Data


def _make_cve(
    cve_id: str = "CVE-2024-3094",
    score: float = 9.8,
    severity: str = "CRITICAL",
    description: str = "Test vulnerability",
    vuln_status: str = "Analyzed",
    published: str = "2024-03-29T00:00:00.000",
) -> CVE:
    return CVE(
        id=cve_id,
        vuln_status=vuln_status,
        published=published,
        last_modified="2024-04-01T00:00:00.000",
        descriptions=[Description(lang="en", value=description)],
        metrics=Metrics(
            cvss_metric_v31=[
                CVSSv3Metric(
                    cvss_data=CVSSv3Data(baseScore=score, baseSeverity=severity)
                )
            ]
        ),
    )


def _make_change(
    cve_id: str = "CVE-2024-3094",
    event_name: str = "CVE Modified",
    created: str = "2024-03-29T10:00:00",
) -> CVEChange:
    return CVEChange(
        cve_id=cve_id,
        event_name=event_name,
        cve_change_id="change-123",
        source_identifier="<EMAIL-REDACTED>",
        created=created,
        details=[ChangeDetail(action="Added", type="description", newValue="Updated")],
    )


class TestOutputFormat:
    """OutputFormat 枚举测试"""

    def test_values(self):
        assert OutputFormat.TABLE.value == "table"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.CSV.value == "csv"

    def test_from_string(self):
        assert OutputFormat("json") == OutputFormat.JSON


class TestCveScoreStyle:
    """评分样式测试"""

    def test_critical(self):
        assert _cve_score_style(9.5) == "bold red"

    def test_high(self):
        assert _cve_score_style(7.5) == "red"

    def test_medium(self):
        assert _cve_score_style(5.0) == "yellow"

    def test_low(self):
        assert _cve_score_style(2.0) == "green"

    def test_zero(self):
        assert _cve_score_style(0.0) == "dim"


class TestCveSeverityStyle:
    """严重度样式测试"""

    def test_critical(self):
        assert _cve_severity_style("CRITICAL") == "bold red"

    def test_high(self):
        assert _cve_severity_style("HIGH") == "red"

    def test_medium(self):
        assert _cve_severity_style("MEDIUM") == "yellow"

    def test_low(self):
        assert _cve_severity_style("LOW") == "green"

    def test_unknown(self):
        assert _cve_severity_style("UNKNOWN") == "dim"

    def test_case_insensitive(self):
        assert _cve_severity_style("critical") == "bold red"


class TestTruncate:
    """文本截断测试"""

    def test_short_text_not_truncated(self):
        assert _truncate("hello", 80) == "hello"

    def test_long_text_truncated(self):
        long_text = "a" * 100
        result = _truncate(long_text, 80)
        assert len(result) == 80
        assert result.endswith("...")

    def test_exact_length_not_truncated(self):
        text = "a" * 80
        assert _truncate(text, 80) == text


class TestFormatCveJson:
    """CVE JSON 格式化测试"""

    def test_output_is_valid_json(self):
        cves = [_make_cve()]
        result = format_cve_json(cves)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_contains_cve_id(self):
        cves = [_make_cve(cve_id="CVE-2024-3094")]
        result = format_cve_json(cves)
        assert "CVE-2024-3094" in result

    def test_empty_list(self):
        result = format_cve_json([])
        assert json.loads(result) == []


class TestFormatCveCsv:
    """CVE CSV 格式化测试"""

    def test_has_header(self):
        cves = [_make_cve()]
        result = format_cve_csv(cves)
        reader = csv.reader(io.StringIO(result))
        header = next(reader)
        assert header == ["CVE-ID", "CVSS", "Severity", "Status", "Published", "Description"]

    def test_data_row(self):
        cves = [_make_cve(cve_id="CVE-2024-3094", score=9.8, severity="CRITICAL")]
        result = format_cve_csv(cves)
        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[0] == "CVE-2024-3094"
        assert row[1] == "9.8"
        assert row[2] == "CRITICAL"

    def test_empty_list_has_only_header(self):
        result = format_cve_csv([])
        reader = csv.reader(io.StringIO(result))
        header = next(reader)
        rows = list(reader)
        assert len(rows) == 0


class TestFormatHistoryJson:
    """变更历史 JSON 格式化测试"""

    def test_output_is_valid_json(self):
        changes = [_make_change()]
        result = format_history_json(changes)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_contains_event_name(self):
        changes = [_make_change(event_name="CVE Modified")]
        result = format_history_json(changes)
        assert "CVE Modified" in result


class TestFormatHistoryCsv:
    """变更历史 CSV 格式化测试"""

    def test_has_header(self):
        changes = [_make_change()]
        result = format_history_csv(changes)
        reader = csv.reader(io.StringIO(result))
        header = next(reader)
        assert "CVE-ID" in header
        assert "Event" in header

    def test_data_row(self):
        changes = [_make_change(cve_id="CVE-2024-3094")]
        result = format_history_csv(changes)
        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[0] == "CVE-2024-3094"

    def test_change_without_details(self):
        changes = [CVEChange(cve_id="CVE-2024-3094", event_name="Initial Analysis")]
        result = format_history_csv(changes)
        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[0] == "CVE-2024-3094"
