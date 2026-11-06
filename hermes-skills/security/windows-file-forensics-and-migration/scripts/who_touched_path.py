#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""那一刻谁碰了这个路径: 进程表 + 所有 Hermes profile 的会话库。

用法:
  python who_touched_path.py Desktop 20          # 最近 20 分钟, 关键字 Desktop
  python who_touched_path.py 95306凭据 30
  python who_touched_path.py touliu 15 --procs   # 只看进程表

会话库结构: <hermes>/profiles/*/state.db 的 messages 表
  session_id / role / tool_name / content / tool_calls / timestamp(epoch 秒)
能回答的问题: "文件在 12:36:53 被删 —— 那一刻哪个 agent 会话在跑、跑的是哪条命令?"

注意: 外部进程(Explorer / 同步客户端 / 杀软 / 第三方清理工具)完全不经过 Hermes,
会话库里必然查不到。必须与进程表和回收站 $I 的删除时间戳交叉验证后才能下结论。
"""
import os
import sys
import time
import glob
import sqlite3
import datetime
import subprocess


def procs(keyword):
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*{0}*' "
          "-or $_.ExecutablePath -like '*{0}*' } | "
          "Select-Object ProcessId,Name,CommandLine | Format-List").format(keyword)
    try:
        out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=90)
        body = (out.stdout or "").strip()
        print("=== 进程表命中 ===")
        print(body if body else "(无)")
    except Exception as exc:
        print("=== 进程表查询失败: %s ===" % exc)


def sessions(root, keyword, minutes):
    now = time.time()
    lo = now - minutes * 60
    dbs = glob.glob(os.path.join(root, "profiles", "*", "state.db"))
    dbs.append(os.path.join(root, "state.db"))
    print("\n=== 会话库 (最近 %d 分钟, 关键字 %r) ===" % (minutes, keyword))
    print("窗口: %s ~ %s" % (datetime.datetime.fromtimestamp(lo).strftime("%H:%M:%S"),
                             datetime.datetime.fromtimestamp(now).strftime("%H:%M:%S")))
    found_any = False
    for db in dbs:
        if not os.path.exists(db):
            continue
        try:
            con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        except Exception as exc:
            print("%s 打不开: %s" % (db, exc))
            continue
        try:
            # state.db 可能很大且无时间索引 —— 限定时间窗 + LIMIT, 不要全表扫
            rows = con.execute(
                "SELECT session_id, role, tool_name, timestamp, "
                "substr(COALESCE(tool_calls,'') || ' | ' || COALESCE(content,''),1,300) "
                "FROM messages WHERE timestamp > ? AND "
                "(COALESCE(tool_calls,'') LIKE ? OR COALESCE(content,'')) "
                "AND (COALESCE(tool_calls,'') LIKE ? OR COALESCE(content,'') LIKE ?) "
                "ORDER BY timestamp DESC LIMIT 40",
                (lo, "%" + keyword + "%", "%" + keyword + "%", "%" + keyword + "%")).fetchall()
        except Exception as exc:
            print("%s 查询失败: %s" % (db, exc))
            con.close()
            continue
        if rows:
            found_any = True
            print("\n--- %s" % db)
            seen = set()
            for sid, role, tname, ts, txt = rows:
                stamp = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                key = (stamp, sid, txt[:80])
                if key in seen:
                    continue
                seen.add(key)
                print("[%s] %s %s/%s" % (stamp, sid, role, tname))
                print("    " + txt.replace("\n", " ")[:260])
        con.close()
    if not found_any:
        print("(无命中 —— 若回收站 $I 证明文件确实被删, 则删除方来自 Hermes 之外)")


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "Desktop"
    mins = 20
    for a in sys.argv[2:]:
        if a.isdigit():
            mins = int(a)
    hermes_root = os.path.join(
        os.environ.get("LOCALAPPDATA", r"C:\Users\Administrator\AppData\Local"), "hermes")
    if "--sessions" not in sys.argv:
        procs(kw)
    sessions(hermes_root, kw, mins)
