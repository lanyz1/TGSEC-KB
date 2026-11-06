#!/usr/bin/env python3
"""事件 id 连续性审计 — seen 集合的缺口 = 漏收条数（前提: id 全局连续自增）
用法: python3 audit_alert_gaps.py <state.json> [since_id]
state.json 需含 {"seen": [ids...]}（多连接合并采集器的去重集合）
"""
import json, sys

path = sys.argv[1]
since = int(sys.argv[2]) if len(sys.argv) > 2 else None
d = json.load(open(path))
seen = sorted(set(x for x in d.get("seen", []) if isinstance(x, int)))
if since:
    seen = [x for x in seen if x >= since]
if not seen:
    print("no data in seen set")
    sys.exit(0)

lo, hi = seen[0], seen[-1]
total = hi - lo + 1
missing = sorted(set(range(lo, hi + 1)) - set(seen))
print(f"审计窗口 #{lo}~#{hi} 共 {total} | 见到 {len(seen)} | 缺口 {len(missing)} | 覆盖 {len(seen)/total*100:.2f}%")
if missing:
    print("缺口:", missing if len(missing) <= 80 else str(missing[:80]) + " ...")
else:
    print("无缺口, 100% 覆盖 ✓")
