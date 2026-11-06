"""
NVDClient HTTP 客户端测试

使用 mock 测试限流、缓存、重试、日期拆分等逻辑，
不发送真实网络请求。
"""

import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import httpx
import pytest

from client import NVDClient, RateLimiter, CacheStore, _split_date_range, CVE_API_BASE
from config import AppConfig
from models import CVE


class TestSplitDateRange:
    """日期范围拆分测试"""

    def test_none_inputs_return_as_is(self):
        assert _split_date_range(None, None) == [(None, None)]

    def test_single_none_returns_as_is(self):
        assert _split_date_range("2024-01-01T00:00:00.000", None) == [
            ("2024-01-01T00:00:00.000", None)
        ]

    def test_within_limit_not_split(self):
        result = _split_date_range(
            "2024-01-01T00:00:00.000",
            "2024-03-01T00:00:00.000",
        )
        assert len(result) == 1

    def test_over_120_days_split(self):
        result = _split_date_range(
            "2024-01-01T00:00:00.000",
            "2024-12-31T00:00:00.000",
        )
        assert len(result) > 1
        for start, end in result:
            assert start is not None
            assert end is not None

    def test_custom_max_days(self):
        result = _split_date_range(
            "2024-01-01T00:00:00.000",
            "2024-02-01T00:00:00.000",
            max_days=10,
        )
        assert len(result) > 1

    def test_invalid_date_returns_as_is(self):
        result = _split_date_range("not-a-date", "also-not-a-date")
        assert result == [("not-a-date", "also-not-a-date")]


class TestRateLimiter:
    """限流器测试"""

    def test_no_wait_when_under_limit(self):
        limiter = RateLimiter(has_api_key=True)
        limiter.wait()
        limiter.wait()

    def test_without_api_key_lower_limit(self):
        limiter_no_key = RateLimiter(has_api_key=False)
        limiter_with_key = RateLimiter(has_api_key=True)
        assert limiter_no_key._max_requests < limiter_with_key._max_requests


class TestCacheStore:
    """缓存存储测试"""

    def test_miss_returns_none(self):
        with TemporaryDirectory() as tmpdir:
            store = CacheStore(Path(tmpdir), ttl=3600)
            assert store.get("https://example.com", None) is None

    def test_put_and_get(self):
        with TemporaryDirectory() as tmpdir:
            store = CacheStore(Path(tmpdir), ttl=3600)
            data = {"key": "value"}
            store.put("https://example.com", {"q": "test"}, data)
            result = store.get("https://example.com", {"q": "test"})
            assert result == data

    def test_expired_returns_none(self):
        with TemporaryDirectory() as tmpdir:
            store = CacheStore(Path(tmpdir), ttl=0)
            store.put("https://example.com", None, {"key": "value"})
            time.sleep(0.1)
            assert store.get("https://example.com", None) is None

    def test_different_params_different_cache(self):
        with TemporaryDirectory() as tmpdir:
            store = CacheStore(Path(tmpdir), ttl=3600)
            store.put("https://example.com", {"a": "1"}, {"result": "a1"})
            store.put("https://example.com", {"a": "2"}, {"result": "a2"})
            assert store.get("https://example.com", {"a": "1"})["result"] == "a1"
            assert store.get("https://example.com", {"a": "2"})["result"] == "a2"

    def test_cache_dir_created_automatically(self):
        with TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "nested" / "cache"
            store = CacheStore(cache_dir, ttl=3600)
            store.put("https://example.com", None, {"key": "value"})
            assert cache_dir.exists()

    def test_corrupted_cache_returns_none(self):
        with TemporaryDirectory() as tmpdir:
            store = CacheStore(Path(tmpdir), ttl=3600)
            cache_path = Path(tmpdir) / "corrupt.json"
            cache_path.write_text("not valid json{{{", encoding="utf-8")
            result = store.get("https://example.com", None)
            assert result is None


class TestNVDClientGetCve:
    """NVDClient.get_cve 测试"""

    def _make_client(self, mock_response: dict) -> NVDClient:
        config = AppConfig(api_key="test-key", cache_enabled=False)
        client = NVDClient(config, no_cache=True)
        mock_http = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_resp
        client._local.http = mock_http
        return client

    def test_get_cve_found(self):
        mock_data = {
            "vulnerabilities": [
                {"cve": {"cveId": "CVE-2024-3094", "vulnStatus": "Analyzed"}}
            ],
            "totalResults": 1,
        }
        client = self._make_client(mock_data)
        cve = client.get_cve("CVE-2024-3094")
        assert cve is not None
        assert cve.id == "CVE-2024-3094"

    def test_get_cve_not_found(self):
        mock_data = {"vulnerabilities": [], "totalResults": 0}
        client = self._make_client(mock_data)
        cve = client.get_cve("CVE-9999-0000")
        assert cve is None


class TestNVDClientGetCvesBatch:
    """NVDClient.get_cves_batch 测试"""

    def test_batch_query(self):
        config = AppConfig(api_key="test-key", cache_enabled=False)
        client = NVDClient(config, no_cache=True)
        mock_http = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "vulnerabilities": [
                {"cve": {"cveId": "CVE-2024-3094"}},
                {"cve": {"cveId": "CVE-2023-44487"}},
            ],
            "totalResults": 2,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_resp
        client._local.http = mock_http

        cves = client.get_cves_batch(["CVE-2024-3094", "CVE-2023-44487"])
        assert len(cves) == 2

    def test_empty_batch_returns_empty(self):
        config = AppConfig(cache_enabled=False)
        client = NVDClient(config, no_cache=True)
        assert client.get_cves_batch([]) == []


class TestNVDClientContextManager:
    """NVDClient 上下文管理器测试"""

    def test_with_statement(self):
        config = AppConfig(cache_enabled=False)
        with NVDClient(config, no_cache=True) as client:
            assert client is not None


class TestNVDClientRetry:
    """NVDClient 重试逻辑测试"""

    def test_retry_on_403(self):
        config = AppConfig(api_key="test-key", cache_enabled=False, max_retries=2)
        client = NVDClient(config, no_cache=True)
        mock_http = MagicMock()

        resp_403 = MagicMock()
        resp_403.status_code = 403
        resp_403.request = MagicMock()
        resp_403.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403", request=resp_403.request, response=resp_403
        )

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"vulnerabilities": [], "totalResults": 0}
        resp_200.raise_for_status = MagicMock()

        mock_http.get.side_effect = [resp_403, resp_200]
        client._local.http = mock_http

        with patch("client.time.sleep"):
            data = client._request(CVE_API_BASE, {"cveId": "CVE-2024-3094"})
            assert data["totalResults"] == 0
