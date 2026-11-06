"""
批量查询模块

负责：输入解析、线程池调度、结果去重。
不依赖 client 或 formatters，通过回调函数与上层解耦，
确保批量调度逻辑与具体查询逻辑分离。
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, TypeVar

from models import CVE, CVEChange

T = TypeVar("T")


# ======================================================================
# 输入解析
# ======================================================================


def read_ids_from_file(path: Path) -> list[str]:
    """
    从文本文件读取 ID 列表。

    每行一个 ID，忽略空行和 # 开头的注释行，自动去除首尾空白。

    Args:
        path: 文本文件路径

    Returns:
        ID 字符串列表
    """
    ids: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)
    return ids


def read_ids_from_stdin() -> list[str]:
    """
    从标准输入读取 ID 列表。

    每行一个 ID，忽略空行，支持管道输入。

    Returns:
        ID 字符串列表
    """
    ids: list[str] = []
    for line in sys.stdin:
        line = line.strip()
        if line and not line.startswith("#"):
            ids.append(line)
    return ids


def read_queries_from_file(path: Path) -> list[dict[str, Any]]:
    """
    从 JSON 文件读取多组查询条件。

    JSON 格式为对象数组，每个对象的键名与 search_cves 参数名对应。

    Args:
        path: JSON 文件路径

    Returns:
        查询条件字典列表
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Query file must be a JSON array")
    return data


# ======================================================================
# 结果去重
# ======================================================================


def deduplicate_cves(cves: list[CVE]) -> list[CVE]:
    """
    按 CVE-ID 去重，保留最后一条。

    多线程并发查询可能返回重复的 CVE 记录，
    此函数确保最终结果中每个 CVE-ID 只出现一次。

    Args:
        cves: CVE 列表（可能含重复）

    Returns:
        去重后的 CVE 列表
    """
    seen: dict[str, CVE] = {}
    for cve in cves:
        seen[cve.id] = cve
    return list(seen.values())


def deduplicate_changes(changes: list[CVEChange]) -> list[CVEChange]:
    """
    按 (cve_id, cve_change_id) 去重，保留最后一条。

    Args:
        changes: CVEChange 列表（可能含重复）

    Returns:
        去重后的 CVEChange 列表
    """
    seen: dict[tuple[str, str], CVEChange] = {}
    for ch in changes:
        key = (ch.cve_id, ch.cve_change_id)
        seen[key] = ch
    return list(seen.values())


# ======================================================================
# 线程池调度
# ======================================================================


def run_batch(
    items: list[Any],
    handler: Callable[[Any], list[T]],
    max_threads: int,
    thread_delay: float,
    progress_callback: Callable[[int, int, Any], None] | None = None,
) -> list[T]:
    """
    线程池批量执行查询任务。

    流程：
    1. 创建 ThreadPoolExecutor(max_workers=max_threads)
    2. 逐个 submit 任务，每 submit 一个后 sleep(thread_delay)
       避免瞬间打满限流窗口
    3. 收集所有 future 结果，合并返回
    4. 单个任务异常不中断整体，记录到 stderr

    Args:
        items:             待处理的任务列表（ID 列表或查询条件列表）
        handler:           处理单个任务的回调，接收一个 item，返回结果列表
        max_threads:       最大线程数
        thread_delay:      线程启动间隔（秒）
        progress_callback: 进度回调 (current_index, total, item)

    Returns:
        所有任务结果的合并列表
    """
    if not items:
        return []

    results: list[T] = []
    lock = threading_lock()
    total = len(items)

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {}
        for i, item in enumerate(items):
            future = executor.submit(handler, item)
            futures[future] = (i, item)
            # 每提交一个任务后间歇，避免瞬间打满限流窗口
            if thread_delay > 0 and i < total - 1:
                time.sleep(thread_delay)

        for future in as_completed(futures):
            idx, item = futures[future]
            try:
                result = future.result()
                with lock:
                    results.extend(result)
                if progress_callback:
                    progress_callback(idx, total, item)
            except Exception as exc:
                # 单个任务失败不中断整体
                print(
                    f"[{idx + 1}/{total}] Query failed: {_item_label(item)} - {exc}",
                    file=sys.stderr,
                )

    return results


def threading_lock() -> Any:
    """
    返回一个 threading.Lock 实例。

    封装为函数以延迟 import，避免在模块级别强制依赖 threading。
    """
    import threading
    return threading.Lock()


def _item_label(item: Any) -> str:
    """生成任务项的可读标签，用于进度和错误提示。"""
    if isinstance(item, str):
        return item
    if isinstance(item, list):
        return f"[{len(item)} items]"
    if isinstance(item, dict):
        return json.dumps(item, ensure_ascii=False)[:80]
    return str(item)
