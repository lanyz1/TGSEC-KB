#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hermes 全档 cron 任务状态扫描 + executions.db mtime(停机核验用)。
用法: python3 jobs_check.py
判据: 禁用后某 job 的 next_run 已过而 last_run 不变 = 调度器已跳过;
      executions.db mtime 冻结 = 无执行,是"已停"的硬证据。
"""
import glob
import json
import os
import time
from datetime import datetime, timezone

ROOT = os.path.join(os.path.expanduser("~"), ".hermes")


def targets():
    yield "default", os.path.join(ROOT, "cron")
    for pdir in sorted(glob.glob(os.path.join(ROOT, "profiles", "*"))):
        yield os.path.basename(pdir), os.path.join(pdir, "cron")


print("now:", datetime.now(timezone.utc).isoformat())
for name, cdir in targets():
    jf = os.path.join(cdir, "jobs.json")
    if not os.path.exists(jf):
        continue
    print("\n== %s ==" % jf)
    try:
        data = json.load(open(jf))
    except Exception as e:
        print("  !! unreadable:", e)
        continue
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    for j in jobs:
        if not isinstance(j, dict):
            continue
        lr = j.get("last_run") or j.get("last_run_at") or "-"
        nr = j.get("next_run") or j.get("next_run_at") or "-"
        print("  %-28s enabled=%s state=%s" % (j.get("name", "?"), j.get("enabled"), j.get("state")))
        print("      last_run=%s" % lr)
        print("      next_run=%s" % nr)
    db = os.path.join(cdir, "executions.db")
    if os.path.exists(db):
        st = os.stat(db)
        print("  executions.db mtime=%s size=%d" % (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)), st.st_size))
