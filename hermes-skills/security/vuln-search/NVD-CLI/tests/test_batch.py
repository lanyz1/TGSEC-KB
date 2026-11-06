"""
批量查询模块测试
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from batch import (
    read_ids_from_file, read_ids_from_stdin,
    read_queries_from_file, deduplicate_cves, deduplicate_changes,
    run_batch, _item_label,
)
from models import CVE, CVEChange, ChangeDetail, Description, Metrics


def _make_cve(cve_id: str) -> CVE:
    return CVE(id=cve_id, descriptions=[Description(lang="en", value="test")])


def _make_change(cve_id: str, change_id: str = "ch-1") -> CVEChange:
    return CVEChange(
        cve_id=cve_id,
        event_name="Modified",
        cve_change_id=change_id,
        details=[ChangeDetail(action="Added", type="description")],
    )


class TestReadIdsFromFile:
    """从文件读取 ID 测试"""

    def test_reads_valid_ids(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ids.txt"
            path.write_text("CVE-2024-3094\nCVE-2023-44487\n", encoding="utf-8")
            result = read_ids_from_file(path)
            assert result == ["CVE-2024-3094", "CVE-2023-44487"]

    def test_ignores_comments(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ids.txt"
            path.write_text("CVE-2024-3094\n# comment\nCVE-2023-44487\n", encoding="utf-8")
            result = read_ids_from_file(path)
            assert result == ["CVE-2024-3094", "CVE-2023-44487"]

    def test_ignores_blank_lines(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ids.txt"
            path.write_text("CVE-2024-3094\n\n  \nCVE-2023-44487\n", encoding="utf-8")
            result = read_ids_from_file(path)
            assert result == ["CVE-2024-3094", "CVE-2023-44487"]

    def test_empty_file(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ids.txt"
            path.write_text("", encoding="utf-8")
            assert read_ids_from_file(path) == []


class TestReadQueriesFromFile:
    """从 JSON 文件读取查询条件测试"""

    def test_reads_valid_queries(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "queries.json"
            data = [{"keyword": "openssl"}, {"keyword": "nginx"}]
            path.write_text(json.dumps(data), encoding="utf-8")
            result = read_queries_from_file(path)
            assert len(result) == 2
            assert result[0]["keyword"] == "openssl"

    def test_non_array_raises(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "queries.json"
            path.write_text('{"keyword": "openssl"}', encoding="utf-8")
            with pytest.raises(ValueError, match="JSON array"):
                read_queries_from_file(path)


class TestDeduplicateCves:
    """CVE 去重测试"""

    def test_no_duplicates(self):
        cves = [_make_cve("CVE-1"), _make_cve("CVE-2")]
        result = deduplicate_cves(cves)
        assert len(result) == 2

    def test_with_duplicates_keeps_last(self):
        cve_a = _make_cve("CVE-1")
        cve_a.vuln_status = "Analyzed"
        cve_b = _make_cve("CVE-1")
        cve_b.vuln_status = "Modified"
        result = deduplicate_cves([cve_a, cve_b])
        assert len(result) == 1
        assert result[0].vuln_status == "Modified"

    def test_empty_list(self):
        assert deduplicate_cves([]) == []


class TestDeduplicateChanges:
    """CVEChange 去重测试"""

    def test_no_duplicates(self):
        changes = [_make_change("CVE-1", "ch-1"), _make_change("CVE-2", "ch-2")]
        result = deduplicate_changes(changes)
        assert len(result) == 2

    def test_with_duplicates_keeps_last(self):
        ch1 = _make_change("CVE-1", "ch-1")
        ch1.event_name = "Initial"
        ch2 = _make_change("CVE-1", "ch-1")
        ch2.event_name = "Modified"
        result = deduplicate_changes([ch1, ch2])
        assert len(result) == 1
        assert result[0].event_name == "Modified"

    def test_different_change_ids_not_deduplicated(self):
        changes = [_make_change("CVE-1", "ch-1"), _make_change("CVE-1", "ch-2")]
        result = deduplicate_changes(changes)
        assert len(result) == 2


class TestRunBatch:
    """线程池批量执行测试"""

    def test_empty_items_returns_empty(self):
        result = run_batch([], handler=lambda x: [x], max_threads=1, thread_delay=0)
        assert result == []

    def test_single_item(self):
        result = run_batch(
            items=["CVE-1"],
            handler=lambda x: [_make_cve(x)],
            max_threads=1,
            thread_delay=0,
        )
        assert len(result) == 1
        assert result[0].id == "CVE-1"

    def test_multiple_items(self):
        result = run_batch(
            items=["CVE-1", "CVE-2", "CVE-3"],
            handler=lambda x: [_make_cve(x)],
            max_threads=2,
            thread_delay=0,
        )
        ids = {cve.id for cve in result}
        assert ids == {"CVE-1", "CVE-2", "CVE-3"}

    def test_failed_item_does_not_stop_others(self, capsys):
        def handler(x):
            if x == "fail":
                raise RuntimeError("boom")
            return [_make_cve(x)]

        result = run_batch(
            items=["CVE-1", "fail", "CVE-3"],
            handler=handler,
            max_threads=1,
            thread_delay=0,
        )
        ids = {cve.id for cve in result}
        assert "CVE-1" in ids
        assert "CVE-3" in ids

    def test_progress_callback(self):
        calls = []
        run_batch(
            items=["CVE-1"],
            handler=lambda x: [_make_cve(x)],
            max_threads=1,
            thread_delay=0,
            progress_callback=lambda i, t, item: calls.append((i, t, item)),
        )
        assert len(calls) == 1
        assert calls[0][0] == 0


class TestItemLabel:
    """_item_label 测试"""

    def test_string(self):
        assert _item_label("CVE-1") == "CVE-1"

    def test_list(self):
        assert _item_label(["a", "b"]) == "[2 items]"

    def test_dict(self):
        label = _item_label({"key": "value"})
        assert "key" in label

    def test_other(self):
        assert _item_label(42) == "42"
