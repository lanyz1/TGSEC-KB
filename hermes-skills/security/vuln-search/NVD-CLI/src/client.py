"""
HTTP 客户端模块

封装对 NVD API 的所有 HTTP 交互，包括：
- 令牌桶限流（有/无 API Key 不同策略）
- 指数退避重试
- 本地文件缓存
- 自动分页遍历

本模块通过构造函数接收 AppConfig，不直接读取配置文件，
与配置管理模块保持松耦合。
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

import httpx

from config import AppConfig
from models import CVEChange, CVEHistoryResponse, CVEResponse, CVE

logger = logging.getLogger(__name__)

# NVD API 基础 URL
CVE_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
HISTORY_API_BASE = "https://services.nvd.nist.gov/rest/json/cvehistory/2.0"

# NVD API 日期范围最大天数限制
_MAX_DATE_RANGE_DAYS = 120


def _split_date_range(
    start_str: str | None, end_str: str | None, max_days: int = _MAX_DATE_RANGE_DAYS
) -> list[tuple[str, str]]:
    """
    将日期范围按 max_days 拆分为多个不超限的子范围。

    NVD API 要求日期范围不超过 120 天。
    此函数自动将超长范围拆成多段，每段不超过 max_days。

    Args:
        start_str: 起始时间字符串，ISO-8601 格式
        end_str:   结束时间字符串，ISO-8601 格式
        max_days:  每段最大天数

    Returns:
        [(start, end), ...] 子范围列表；
        如果输入为 None 或范围未超限，返回单元素列表
    """
    if not start_str or not end_str:
        return [(start_str, end_str)]

    try:
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return [(start_str, end_str)]

    delta = end - start
    if delta.days <= max_days:
        return [(start_str, end_str)]

    # 需要拆分
    ranges: list[tuple[str, str]] = []
    current = start
    while current < end:
        next_end = min(current + timedelta(days=max_days), end)
        ranges.append((
            current.strftime("%Y-%m-%dT%H:%M:%S.000"),
            next_end.strftime("%Y-%m-%dT%H:%M:%S.000"),
        ))
        current = next_end

    logger.debug("日期范围拆分为 %d 段（每段最长 %d 天）", len(ranges), max_days)
    return ranges


class RateLimiter:
    """
    简易令牌桶限流器。

    NVD API 限流策略：
    - 无 API Key: 5 次 / 30 秒
    - 有 API Key: 50 次 / 30 秒

    本实现用固定窗口 + sleep 来保证不超过限额。
    线程安全：内部用 threading.Lock 保护时间戳列表。
    """

    def __init__(self, has_api_key: bool) -> None:
        if has_api_key:
            self._max_requests = 45  # 留一点余量
            self._window = 30.0
        else:
            self._max_requests = 4
            self._window = 30.0
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        """
        阻塞等待直到可以发送下一个请求。

        如果当前窗口内请求数已达上限，则 sleep 到窗口过期。
        线程安全：通过 Lock 保证多线程下限流正确。
        """
        with self._lock:
            now = time.monotonic()
            # 清理过期时间戳
            self._timestamps = [t for t in self._timestamps if now - t < self._window]

            if len(self._timestamps) >= self._max_requests:
                # 需要等到最早的那个时间戳过期
                oldest = self._timestamps[0]
                sleep_time = self._window - (now - oldest) + 0.1
            else:
                sleep_time = 0

            # 提前占位，防止其它线程同时通过
            self._timestamps.append(time.monotonic())

        # 在锁外 sleep，不阻塞其它线程的 wait 调用
        if sleep_time > 0:
            logger.debug("限流等待 %.1f 秒", sleep_time)
            time.sleep(sleep_time)


class CacheStore:
    """
    基于文件的 HTTP 响应缓存。

    以请求 URL 的 SHA256 哈希为文件名，存储 JSON 响应。
    每个 cache entry 包含 `_cached_at` 字段记录缓存时间。
    """

    def __init__(self, cache_dir: Path, ttl: int) -> None:
        """
        Args:
            cache_dir: 缓存文件存放目录
            ttl:       缓存过期时间（秒）
        """
        self._dir = cache_dir
        self._ttl = ttl
        self._lock = threading.Lock()

    def _cache_path(self, url: str, params: dict[str, Any] | None) -> Path:
        """根据 URL + 参数生成缓存文件路径。"""
        key = url
        if params:
            key += json.dumps(params, sort_keys=True)
        filename = hashlib.sha256(key.encode()).hexdigest() + ".json"
        return self._dir / filename

    def get(self, url: str, params: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        尝试从缓存读取响应。

        Returns:
            缓存的 JSON 字典，过期或不存在时返回 None
        """
        with self._lock:
            path = self._cache_path(url, params)
            if not path.exists():
                return None

            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                cached_at = data.get("_cached_at", 0)
                if time.time() - cached_at > self._ttl:
                    return None
                # 移除内部字段后返回
                data.pop("_cached_at", None)
                return data
            except (json.JSONDecodeError, OSError):
                return None

    def put(self, url: str, params: dict[str, Any] | None, data: dict[str, Any]) -> None:
        """将响应数据写入缓存。"""
        with self._lock:
            self._dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_path(url, params)
            store = {**data, "_cached_at": time.time()}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(store, f, ensure_ascii=False)


class NVDClient:
    """
    NVD API 客户端。

    通过组合 RateLimiter、CacheStore 和 httpx.Client，
    对外提供简洁的查询接口。调用者无需关心限流、重试、缓存细节。
    线程安全：httpx.Client 通过 threading.local 按线程创建，
    RateLimiter 和 CacheStore 内部加锁。

    Usage::

        config = AppConfig.load()
        client = NVDClient(config)
        cves = client.search_cves(keyword="log4j")
    """

    def __init__(
        self,
        config: AppConfig,
        *,
        no_cache: bool = False,
    ) -> None:
        """
        Args:
            config:   应用配置实例
            no_cache: 是否禁用缓存（命令行 --no-cache 传入）
        """
        self._config = config
        self._limiter = RateLimiter(bool(config.api_key))
        self._cache = (
            CacheStore(config.cache_dir, config.cache_ttl)
            if config.cache_enabled and not no_cache
            else None
        )
        # 线程本地存储：每个线程懒创建自己的 httpx.Client
        self._local = threading.local()

    @property
    def _http(self) -> httpx.Client:
        """
        每个线程懒创建自己的 httpx.Client 实例。

        httpx 的同步 Client 不是线程安全的，
        通过 threading.local 确保每线程独立实例。
        """
        if not hasattr(self._local, "http"):
            headers: dict[str, str] = {}
            if self._config.api_key:
                <REDACTED>"apiKey"] = self._config.api_key
            self._local.http = httpx.Client(
                timeout=self._config.timeout,
                headers=headers,
                follow_redirects=True,
            )
        return self._local.http

    def close(self) -> None:
        """
        关闭当前线程的 HTTP 连接。

        多线程场景下，各线程的 Client 随线程结束自动关闭，
        此方法主要用于单线程 with 语句兼容。
        """
        if hasattr(self._local, "http"):
            self._local.http.close()
            del self._local.http

    def __enter__(self) -> NVDClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        发送一次 GET 请求，带限流、缓存和重试。

        Args:
            url:    请求 URL
            params: 查询参数

        Returns:
            API 响应的 JSON 字典

        Raises:
            httpx.HTTPStatusError: 重试耗尽后仍然失败
        """
        # 尝试缓存
        if self._cache is not None:
            cached = self._cache.get(url, params)
            if cached is not None:
                logger.debug("缓存命中: %s", url)
                return cached

        last_exc: Exception | None = None

        for attempt in range(1, self._config.max_retries + 1):
            self._limiter.wait()
            try:
                resp = self._http.get(url, params=params)

                # NVD 在限流时返回 403
                if resp.status_code == 403:
                    logger.warning("请求被限流 (403)，第 %d 次重试", attempt)
                    last_exc = httpx.HTTPStatusError(
                        "403 Forbidden", request=resp.request, response=resp
                    )
                    time.sleep(2 ** attempt)
                    continue

                resp.raise_for_status()
                data = resp.json()

                # 写入缓存
                if self._cache is not None:
                    self._cache.put(url, params, data)

                return data

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code in (403, 429, 503):
                    wait = 2 ** attempt
                    logger.warning("HTTP %d，第 %d 次重试，等待 %ds", exc.response.status_code, attempt, wait)
                    time.sleep(wait)
                    continue
                raise

            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning("连接错误，第 %d 次重试，等待 %ds", attempt, wait)
                time.sleep(wait)
                continue

        # 所有重试失败
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Unexpected error: retries exhausted without exception")

    # ------------------------------------------------------------------
    # CVE API
    # ------------------------------------------------------------------

    def get_cve(self, cve_id: str) -> CVE | None:
        """
        查询单个 CVE 详情。

        Args:
            cve_id: CVE 编号，如 CVE-2021-44228

        Returns:
            CVE 模型实例；未找到时返回 None
        """
        data = self._request(CVE_API_BASE, {"cveId": cve_id})
        resp = CVEResponse.model_validate(data)
        cves = resp.parse_cves()
        return cves[0] if cves else None

    def get_cves_batch(self, cve_ids: list[str]) -> list[CVE]:
        """
        批量查询多个 CVE（使用 cveIds 参数，最多 100 个）。

        Args:
            cve_ids: CVE 编号列表

        Returns:
            CVE 模型列表
        """
        if not cve_ids:
            return []
        # NVD 限制最多 100 个
        batch = cve_ids[:100]
        data = self._request(CVE_API_BASE, {"cveIds": ",".join(batch)})
        resp = CVEResponse.model_validate(data)
        return resp.parse_cves()

    def search_cves(
        self,
        *,
        keyword: str | None = None,
        keyword_exact: bool = False,
        cpe_name: str | None = None,
        is_vulnerable: bool = False,
        cvss_v2_severity: str | None = None,
        cvss_v3_severity: str | None = None,
        cvss_v4_severity: str | None = None,
        cvss_v2_metrics: str | None = None,
        cvss_v3_metrics: str | None = None,
        cvss_v4_metrics: str | None = None,
        cwe_id: str | None = None,
        has_kev: bool = False,
        has_cert_alerts: bool = False,
        has_cert_notes: bool = False,
        pub_start: str | None = None,
        pub_end: str | None = None,
        mod_start: str | None = None,
        mod_end: str | None = None,
        kev_start: str | None = None,
        kev_end: str | None = None,
        vuln_statuses: list[str] | None = None,
        cve_tag: str | None = None,
        source_identifier: str | None = None,
        virtual_match_string: str | None = None,
        version_start: str | None = None,
        version_start_type: str | None = None,
        version_end: str | None = None,
        version_end_type: str | None = None,
        no_rejected: bool = False,
        results_per_page: int = 2000,
        start_index: int = 0,
    ) -> tuple[list[CVE], int]:
        """
        按条件搜索 CVE。

        所有参数均为可选，与 NVD CVE API 参数一一对应。
        仅将非 None 的参数加入请求。

        Returns:
            (CVE 列表, 总结果数) 元组。总结果数用于判断是否需要翻页。
        """
        params: dict[str, Any] = {}

        if keyword:
            params["keywordSearch"] = keyword
        if keyword_exact and keyword:
            params["keywordExactMatch"] = ""
        if cpe_name:
            params["cpeName"] = cpe_name
        if is_vulnerable and cpe_name:
            params["isVulnerable"] = ""
        if cvss_v2_severity:
            params["cvssV2Severity"] = cvss_v2_severity
        if cvss_v3_severity:
            params["cvssV3Severity"] = cvss_v3_severity
        if cvss_v4_severity:
            params["cvssV4Severity"] = cvss_v4_severity
        if cvss_v2_metrics:
            params["cvssV2Metrics"] = cvss_v2_metrics
        if cvss_v3_metrics:
            params["cvssV3Metrics"] = cvss_v3_metrics
        if cvss_v4_metrics:
            params["cvssV4Metrics"] = cvss_v4_metrics
        if cwe_id:
            params["cweId"] = cwe_id
        if has_kev:
            params["hasKev"] = ""
        if has_cert_alerts:
            params["hasCertAlerts"] = ""
        if has_cert_notes:
            params["hasCertNotes"] = ""
        if pub_start and pub_end:
            params["pubStartDate"] = pub_start
            params["pubEndDate"] = pub_end
        if mod_start and mod_end:
            params["lastModStartDate"] = mod_start
            params["lastModEndDate"] = mod_end
        if kev_start and kev_end:
            params["kevStartDate"] = kev_start
            params["kevEndDate"] = kev_end
        if vuln_statuses:
            params["vulnStatuses"] = ",".join(vuln_statuses)
        if cve_tag:
            params["cveTag"] = cve_tag
        if source_identifier:
            params["sourceIdentifier"] = source_identifier
        if virtual_match_string:
            params["virtualMatchString"] = virtual_match_string
        if version_start:
            params["versionStart"] = version_start
        if version_start_type:
            params["versionStartType"] = version_start_type
        if version_end:
            params["versionEnd"] = version_end
        if version_end_type:
            params["versionEndType"] = version_end_type
        if no_rejected:
            params["noRejected"] = ""

        params["resultsPerPage"] = results_per_page
        params["startIndex"] = start_index

        # 检查日期范围是否超过 120 天，超限则自动拆分
        pub_ranges = _split_date_range(pub_start, pub_end)
        mod_ranges = _split_date_range(mod_start, mod_end)
        kev_ranges = _split_date_range(kev_start, kev_end)

        # 如果只有单段范围（最常见情况），直接请求
        if len(pub_ranges) == 1 and len(mod_ranges) == 1 and len(kev_ranges) == 1:
            # 用拆分后的值覆盖（可能不变）
            if pub_start and pub_end:
                params["pubStartDate"] = pub_ranges[0][0]
                params["pubEndDate"] = pub_ranges[0][1]
            if mod_start and mod_end:
                params["lastModStartDate"] = mod_ranges[0][0]
                params["lastModEndDate"] = mod_ranges[0][1]
            if kev_start and kev_end:
                params["kevStartDate"] = kev_ranges[0][0]
                params["kevEndDate"] = kev_ranges[0][1]

            data = self._request(CVE_API_BASE, params)
            resp = CVEResponse.model_validate(data)
            return resp.parse_cves(), resp.total_results

        # 多段范围：逐段请求并合并结果
        all_cves: list[CVE] = []
        total_estimate = 0

        # 以 pub_ranges 为主循环（其它范围若也只有一段则不变）
        for p_start, p_end in pub_ranges:
            for m_start, m_end in mod_ranges:
                for k_start, k_end in kev_ranges:
                    chunk_params = dict(params)
                    if pub_start and pub_end:
                        chunk_params["pubStartDate"] = p_start
                        chunk_params["pubEndDate"] = p_end
                    if mod_start and mod_end:
                        chunk_params["lastModStartDate"] = m_start
                        chunk_params["lastModEndDate"] = m_end
                    if kev_start and kev_end:
                        chunk_params["kevStartDate"] = k_start
                        chunk_params["kevEndDate"] = k_end

                    data = self._request(CVE_API_BASE, chunk_params)
                    resp = CVEResponse.model_validate(data)
                    all_cves.extend(resp.parse_cves())
                    total_estimate += resp.total_results

        return all_cves, total_estimate

    def iter_all_cves(self, **kwargs: Any) -> Iterator[CVE]:
        """
        迭代器：自动翻页遍历所有匹配的 CVE。

        内部循环调用 search_cves，自动递增 startIndex 直到取完所有结果。

        Yields:
            逐条 CVE 模型实例
        """
        start = kwargs.pop("start_index", 0)
        per_page = kwargs.pop("results_per_page", 2000)

        while True:
            cves, total = self.search_cves(
                start_index=start, results_per_page=per_page, **kwargs
            )
            yield from cves
            start += per_page
            if start >= total:
                break

    # ------------------------------------------------------------------
    # CVE Change History API
    # ------------------------------------------------------------------

    def get_cve_history(
        self,
        cve_id: str | None = None,
        *,
        change_start: str | None = None,
        change_end: str | None = None,
        event_name: str | None = None,
        results_per_page: int = 5000,
        start_index: int = 0,
    ) -> tuple[list[CVEChange], int]:
        """
        查询 CVE 变更历史。

        Args:
            cve_id:          指定 CVE 编号
            change_start:    变更开始时间
            change_end:      变更结束时间
            event_name:      事件类型筛选
            results_per_page: 每页数量
            start_index:     分页偏移

        Returns:
            (CVEChange 列表, 总结果数) 元组
        """
        params: dict[str, Any] = {}

        if cve_id:
            params["cveId"] = cve_id
        if change_start and change_end:
            params["changeStartDate"] = change_start
            params["changeEndDate"] = change_end
        if event_name:
            params["eventName"] = event_name

        params["resultsPerPage"] = results_per_page
        params["startIndex"] = start_index

        # 拆分超限日期范围
        change_ranges = _split_date_range(change_start, change_end)

        if len(change_ranges) == 1:
            if change_start and change_end:
                params["changeStartDate"] = change_ranges[0][0]
                params["changeEndDate"] = change_ranges[0][1]

            data = self._request(HISTORY_API_BASE, params)
            resp = CVEHistoryResponse.model_validate(data)
            return resp.parse_changes(), resp.total_results

        # 多段范围
        all_changes: list[CVEChange] = []
        total_estimate = 0
        for c_start, c_end in change_ranges:
            chunk_params = dict(params)
            chunk_params["changeStartDate"] = c_start
            chunk_params["changeEndDate"] = c_end

            data = self._request(HISTORY_API_BASE, chunk_params)
            resp = CVEHistoryResponse.model_validate(data)
            all_changes.extend(resp.parse_changes())
            total_estimate += resp.total_results

        return all_changes, total_estimate

    def iter_all_history(self, **kwargs: Any) -> Iterator[CVEChange]:
        """
        迭代器：自动翻页遍历所有变更历史。

        Yields:
            逐条 CVEChange 模型实例
        """
        start = kwargs.pop("start_index", 0)
        per_page = kwargs.pop("results_per_page", 5000)

        while True:
            changes, total = self.get_cve_history(
                start_index=start, results_per_page=per_page, **kwargs
            )
            yield from changes
            start += per_page
            if start >= total:
                break
