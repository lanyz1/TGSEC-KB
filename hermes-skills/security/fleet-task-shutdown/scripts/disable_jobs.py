#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""禁用 Hermes 全部 cron 任务(跨 default + profiles/*,自动备份)。
用法:
  python3 disable_jobs.py            # 禁所有档
  python3 disable_jobs.py bot2 bot3  # 只禁指定档
核验: 记下禁用时刻;跑 jobs_check.py,过了 next_run 而 last_run 不变 = 已被调度器跳过。
"""
import glob
import json
import os
import shutil
import sys
import time

ROOT = os.path.join(os.path.expanduser("~"), ".hermes")
want = set(sys.argv[1:])

pairs = [("default", os.path.join(ROOT, "cron"))]
for pdir in sorted(glob.glob(os.path.join(ROOT, "profiles", "*"))):
    pairs.append((os.path.basename(pdir), os.path.join(pdir, "cron")))

for name, cdir in pairs:
    if want and name not in want:
        continue
    jf = os.path.join(cdir, "jobs.json")
    if not os.path.exists(jf):
        continue
    try:
        data = json.load(open(jf))
    except Exception as e:
        print("%s: unreadable %s" % (name, e))
        continue
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    changed = 0
    for j in jobs:
        if isinstance(j, dict) and j.get("enabled") is not False:
            j["enabled"] = False
            if "state" in j:
                j["state"] = "paused"
            changed += 1
    if changed:
        bak = jf + ".bak." + time.strftime("%Y%m%d_%H%M%S")
        shutil.copy2(jf, bak)
        with open(jf, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("%s: disabled=%d backup=%s" % (name, changed, bak))
    still = sum(1 for j in jobs if isinstance(j, dict) and j.get("enabled") is not False)
    print("%s: still_enabled=%d" % (name, still))
