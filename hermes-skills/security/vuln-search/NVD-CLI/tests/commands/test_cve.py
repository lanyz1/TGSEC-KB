"""
cve 子命令测试
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from commands.cve import cve_app, _format_date, _search_single, _QUERY_KEY_MAP
from models import CVE, Description, Metrics, CVSSv3Metric, CVSSv3Data


def _make_cve(cve_id: str) -> CVE:
    return CVE(
        id=cve_id,
        vuln_status="Analyzed",
        published="2024-03-29T00:00:00.000",
        descriptions=[Description(lang="en", value="Test")],
        metrics=Metrics(
            cvss_metric_v31=[
                CVSSv3Metric(cvss_data=CVSSv3Data(baseScore=9.8, baseSeverity="CRITICAL"))
            ]
        ),
    )


runner = CliRunner()


class TestFormatDate:
    """_format_date 测试"""

    def test_converts_date_format(self):
        assert _format_date("2024-01-15") == "2024-01-15T00:00:00.000"

    def test_none_returns_none(self):
        assert _format_date(None) is None

    def test_empty_returns_none(self):
        assert _format_date("") is None


class TestQueryKeyMap:
    """_QUERY_KEY_MAP 映射完整性测试"""

    def test_all_json_fields_have_mapping(self):
        expected_json_fields = {
            "keyword", "exact", "cpe", "is_vulnerable",
            "severity_v2", "severity_v3", "severity_v4",
            "cvss_v2_metrics", "cvss_v3_metrics", "cvss_v4_metrics",
            "cwe", "has_kev", "has_cert_alerts", "has_cert_notes",
            "pub_start", "pub_end", "mod_start", "mod_end",
            "kev_start", "kev_end", "status", "cve_tag", "source",
            "virtual_match", "version_start", "version_start_type",
            "version_end", "version_end_type", "no_rejected",
        }
        assert expected_json_fields.issubset(set(_QUERY_KEY_MAP.keys()))

    def test_limit_is_not_in_map(self):
        assert "limit" not in _QUERY_KEY_MAP


class TestSearchSingle:
    """_search_single 测试"""

    def test_maps_json_keys_to_api_params(self):
        mock_client = MagicMock()
        mock_client.search_cves.return_value = ([_make_cve("CVE-1")], 1)

        query = {"keyword": "openssl", "severity_v3": "CRITICAL"}
        _search_single(mock_client, query, limit=5)

        call_kwargs = mock_client.search_cves.call_args[1]
        assert call_kwargs["keyword"] == "openssl"
        assert call_kwargs["cvss_v3_severity"] == "CRITICAL"
        assert "limit" not in call_kwargs

    def test_limit_from_json(self):
        mock_client = MagicMock()
        mock_client.search_cves.return_value = ([_make_cve("CVE-1")], 1)

        query = {"keyword": "openssl", "limit": 3}
        cves, total = _search_single(mock_client, query)
        assert len(cves) <= 3

    def test_unknown_json_key_ignored(self):
        mock_client = MagicMock()
        mock_client.search_cves.return_value = ([_make_cve("CVE-1")], 1)

        query = {"keyword": "openssl", "unknown_field": "value"}
        _search_single(mock_client, query)
        call_kwargs = mock_client.search_cves.call_args[1]
        assert "unknown_field" not in call_kwargs

    def test_date_fields_formatted(self):
        mock_client = MagicMock()
        mock_client.search_cves.return_value = ([_make_cve("CVE-1")], 1)

        query = {"keyword": "openssl", "pub_start": "2024-01-01", "pub_end": "2024-12-31"}
        _search_single(mock_client, query)
        call_kwargs = mock_client.search_cves.call_args[1]
        assert call_kwargs["pub_start"] == "2024-01-01T00:00:00.000"
        assert call_kwargs["pub_end"] == "2024-12-31T00:00:00.000"


class TestCveGetCommand:
    """cve get 命令行测试"""

    @patch("commands.cve.NVDClient")
    @patch("commands.cve.AppConfig.load")
    def test_get_single_cve(self, mock_load, mock_client_cls):
        mock_load.return_value = MagicMock(cache_enabled=False)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_cve.return_value = _make_cve("CVE-2024-3094")
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cve_app, ["get", "CVE-2024-3094", "-o", "json"])
        assert result.exit_code == 0

    @patch("commands.cve.NVDClient")
    @patch("commands.cve.AppConfig.load")
    def test_get_not_found(self, mock_load, mock_client_cls):
        mock_load.return_value = MagicMock(cache_enabled=False)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_cve.return_value = None
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cve_app, ["get", "CVE-9999-0000"])
        assert result.exit_code == 1

    def test_get_no_ids(self):
        result = runner.invoke(cve_app, ["get"])
        assert result.exit_code == 1


class TestCveSearchCommand:
    """cve search 命令行测试"""

    @patch("commands.cve.NVDClient")
    @patch("commands.cve.AppConfig.load")
    def test_search_with_keyword(self, mock_load, mock_client_cls):
        mock_load.return_value = MagicMock(cache_enabled=False)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.search_cves.return_value = ([_make_cve("CVE-1")], 1)
        mock_client.iter_all_cves.return_value = iter([_make_cve("CVE-1")])
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cve_app, ["search", "-k", "openssl", "-o", "json"])
        assert result.exit_code == 0

    @patch("commands.cve.NVDClient")
    @patch("commands.cve.AppConfig.load")
    def test_search_no_results(self, mock_load, mock_client_cls):
        mock_load.return_value = MagicMock(cache_enabled=False)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.search_cves.return_value = ([], 0)
        mock_client.iter_all_cves.return_value = iter([])
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cve_app, ["search", "-k", "nonexistent"])
        assert result.exit_code == 1
