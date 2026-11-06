"""
history 子命令测试
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from commands.history import history_app, _format_date
from models import CVEChange, ChangeDetail


def _make_change(cve_id: str = "CVE-2024-3094") -> CVEChange:
    return CVEChange(
        cve_id=cve_id,
        event_name="CVE Modified",
        cve_change_id="ch-123",
        source_identifier="<EMAIL-REDACTED>",
        created="2024-03-29T10:00:00",
        details=[ChangeDetail(action="Added", type="description", newValue="Updated")],
    )


runner = CliRunner()


class TestFormatDate:
    """_format_date 测试"""

    def test_converts_date_format(self):
        assert _format_date("2024-01-15") == "2024-01-15T00:00:00.000"

    def test_none_returns_none(self):
        assert _format_date(None) is None


class TestHistoryGetCommand:
    """history get 命令行测试"""

    @patch("commands.history.NVDClient")
    @patch("commands.history.AppConfig.load")
    def test_get_single(self, mock_load, mock_client_cls):
        mock_load.return_value = MagicMock(cache_enabled=False)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_cve_history.return_value = ([_make_change()], 1)
        mock_client_cls.return_value = mock_client

        result = runner.invoke(history_app, ["get", "CVE-2024-3094", "-o", "json"])
        assert result.exit_code == 0

    @patch("commands.history.NVDClient")
    @patch("commands.history.AppConfig.load")
    def test_get_not_found(self, mock_load, mock_client_cls):
        mock_load.return_value = MagicMock(cache_enabled=False)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_cve_history.return_value = ([], 0)
        mock_client_cls.return_value = mock_client

        result = runner.invoke(history_app, ["get", "CVE-9999-0000"])
        assert result.exit_code == 1

    def test_get_no_id(self):
        result = runner.invoke(history_app, ["get"])
        assert result.exit_code == 1


class TestHistorySearchCommand:
    """history search 命令行测试"""

    @patch("commands.history.NVDClient")
    @patch("commands.history.AppConfig.load")
    def test_search_with_date_range(self, mock_load, mock_client_cls):
        mock_load.return_value = MagicMock(cache_enabled=False)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_cve_history.return_value = ([_make_change()], 1)
        mock_client.iter_all_history.return_value = iter([_make_change()])
        mock_client_cls.return_value = mock_client

        result = runner.invoke(
            history_app,
            ["search", "--start", "2024-01-01", "--end", "2024-01-31", "-o", "json"],
        )
        assert result.exit_code == 0

    @patch("commands.history.NVDClient")
    @patch("commands.history.AppConfig.load")
    def test_search_no_results(self, mock_load, mock_client_cls):
        mock_load.return_value = MagicMock(cache_enabled=False)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_cve_history.return_value = ([], 0)
        mock_client.iter_all_history.return_value = iter([])
        mock_client_cls.return_value = mock_client

        result = runner.invoke(
            history_app,
            ["search", "--start", "2024-01-01", "--end", "2024-01-31"],
        )
        assert result.exit_code == 1
