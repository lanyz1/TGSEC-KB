#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""闪窗观测器 —— 跨触发点实测"到底有没有可见控制台窗口弹出"。

用法（用 pythonw 启动，观测器自身不弹窗）：
    pythonw console_flash_watch.py [持续分钟=25] [结果文件=flashwatch_result.txt]

三路互证（单靠任一路都会误判）：
  A 每 2s 枚举**可见**顶层控制台窗口（EnumWindows + ConsoleWindowClass / CASCADIA / mintty）
    —— 只有它证明"屏幕上真的闪了窗"；conhost 被创建不等于窗口可见。
  B 4688 进程创建审计：cmd.exe / conhost / wscript / cscript / cygwin-console-helper / .bat / .vbs
    及其父进程 —— 证明"谁拉起了控制台程序"。
  C TaskScheduler/Operational 事件：哪个计划任务被拉起（该日志默认未启用，读到空是正常现象）。

设计要点：
  * 结束时自动把 4688 审计还原成 No Auditing（系统默认态）——系统级改动必须有还原。
  * 全程只写文件、从不 print —— pythonw.exe 下 sys.stdout 是 None，print 会炸。
  * 采样窗口必须**跨过被怀疑任务的触发点**（每 30 分钟的任务至少要覆盖一个 :00/:30 边界）。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import datetime
import subprocess
import sys
import threading
import time

MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 25
OUT = sys.argv[2] if len(sys.argv) > 2 else "flashwatch_result.txt"
GUID_4688 = "{0CCE922B-69AE-11D9-BED3-505054503030}"
LOCK = threading.Lock()


def log(msg: str) -> None:
    with LOCK:
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(msg + "\n")


def run(cmd: list[str], timeout: int = 120) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout)
        return (r.stdout or r.stderr or "").strip()
    except Exception as e:  # noqa: BLE001
        return f"(err {e})"


def ps(script: str) -> str:
    return run(["powershell", "-NoProfile", "-Command", script], timeout=180)


# ---------- A. 可见控制台窗口枚举 ----------
user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
GetClassNameW = user32.GetClassNameW
GetWindowTextW = user32.GetWindowTextW
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId

CONSOLE_CLASSES = ("ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS",
                   "PseudoConsoleWindow", "mintty")


def snapshot_windows() -> list[tuple[int, str, str]]:
    found: list[tuple[int, str, str]] = []

    def cb(hwnd, _):
        if not IsWindowVisible(hwnd):
            return True
        cbuf = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, cbuf, 256)
        cls = cbuf.value
        if cls in CONSOLE_CLASSES:
            tbuf = ctypes.create_unicode_buffer(512)
            GetWindowTextW(hwnd, tbuf, 512)
            pid = wt.DWORD(0)
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            found.append((int(pid.value), cls, tbuf.value))
        return True

    EnumWindows(EnumWindowsProc(cb), 0)
    return found


def window_watch(stop_evt: threading.Event) -> None:
    seen: set[tuple[int, str, str]] = set()
    while not stop_evt.is_set():
        now = datetime.datetime.now().strftime("%H:%M:%S")
        for pid, cls, title in snapshot_windows():
            key = (pid, cls, title)
            if key not in seen:
                seen.add(key)
                log(f"[WINDOW {now}] 可见控制台窗口 pid={pid} class={cls} title={title!r}")
        stop_evt.wait(2)


# ---------- main ----------
STATE = ("foreach($n in (Get-ScheduledTask | Where-Object {"
         "$_.Actions.Execute -match 'cmd|python|wscript|powershell|\\.bat|\\.vbs'}).TaskName){"
         "$t=Get-ScheduledTask -TaskName $n;$i=Get-ScheduledTaskInfo -TaskName $n;"
         "$n+' State='+$t.State+' LastRun='+$i.LastRunTime+' NextRun='+$i.NextRunTime"
         "+' Result='+$i.LastTaskResult}")

log("")
log("=" * 72)
log(f"闪窗观测开始 {datetime.datetime.now():%Y-%m-%d %H:%M:%S}（{MIN} 分钟）")
log("基线：可能拉起控制台程序的计划任务（State / LastRun / NextRun / Result）")
log(ps(STATE))
log("4688 审计: " + run(["auditpol", "/set", f"/subcategory:{GUID_4688}", "/success:enable"]) +
    " | " + run(["auditpol", "/get", f"/subcategory:{GUID_4688}"]).replace("\n", " "))

stop_evt = threading.Event()
threading.Thread(target=window_watch, args=(stop_evt,), daemon=True).start()
log("[窗口巡检] 每 2s 枚举可见控制台窗口，已启动")

t0 = time.time()
while time.time() - t0 < MIN * 60:
    time.sleep(15)
log(f"采样结束，时长实到 {int(time.time() - t0)}s")
stop_evt.set()
time.sleep(3)

log("---- B. 4688 进程创建（过滤控制台相关）----")
log(ps(r"""
$ev = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4688;
        StartTime=(Get-Date).AddMinutes(-30)} -MaxEvents 8000 -ErrorAction SilentlyContinue
$ev | ForEach-Object {
  $x=[xml]$_.ToXml(); $d=@{}
  $x.Event.EventData.Data | ForEach-Object { $d[$_.Name]=$_.'#text' }
  [PSCustomObject]@{ t=$_.TimeCreated.ToString('HH:mm:ss'); c=$d['NewProcessName']; p=$d['ParentProcessName'] }
} | Where-Object { $_.c -match 'cmd\.exe|conhost\.exe|wscript|cscript|cygwin-console-helper|\.bat|\.vbs' } |
  Format-Table -AutoSize | Out-String -Width 250
""") or "(无匹配)")

log("---- C. TaskScheduler 事件（任务启动/结束；日志未启用时为空）----")
log(ps(r"""
'IsEnabled=' + (Get-WinEvent -ListLog 'Microsoft-Windows-TaskScheduler/Operational'
                -ErrorAction SilentlyContinue).IsEnabled
Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -MaxEvents 1200 -ErrorAction SilentlyContinue |
  Where-Object { $_.Id -in 100,102,110,200,201,329 } |
  Select-Object -First 40 TimeCreated,Id,@{n='T';e={$_.Properties[0].Value}} |
  Format-Table -AutoSize | Out-String -Width 200
""") or "(无事件)")

log("观测结束时任务状态:")
log(ps(STATE))

# ---------- 还原 ----------
run(["auditpol", "/set", f"/subcategory:{GUID_4688}", "/success:disable"])
log("4688 审计已还原: " + run(["auditpol", "/get", f"/subcategory:{GUID_4688}"]).replace("\n", " "))
log(f"闪窗观测完成 {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
log("=" * 72)
