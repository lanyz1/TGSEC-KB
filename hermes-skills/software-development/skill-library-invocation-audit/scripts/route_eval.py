#!/usr/bin/env python3
"""现场口语评测：用渗透现场的说法（不是卡片名）测路由命中率。

用法：
  python3 route_eval.py eval.json [skill_find.py] [--phase recon]

eval.json:
  [{"q": "盲注 没回显 怎么判真假", "expect": ["sqli-manual", "sqli-sql-injection"]}, ...]
  expect 可给多个候选（同族卡都算对）。

输出每条 rank + 前三名，末行 TOP1/TOP3/MISS。
判读：TOP3 必须 100%，TOP1 <90% 说明元数据补词不够或同族卡互抢。
**评测集里必须放同族对照**（宝塔 vs 自建面板、sqli vs ldap），否则补词把邻卡顶掉也看不出来。
"""
import json, subprocess, sys, os

argv = [a for a in sys.argv[1:] if not a.startswith("--")]
phase = "recon"
phase_val = None
for a in sys.argv[1:]:
    if a.startswith("--phase="):
        phase = a.split("=", 1)[1]
        phase_val = phase
    elif a == "--phase":
        phase = sys.argv[sys.argv.index(a) + 1]
        phase_val = phase
# `--phase recon` 的取值会被上面的过滤器留下，误当 finder 路径 -> 全部 MISS 假象
if phase_val in argv:
    argv.remove(phase_val)
if not argv:
    sys.exit("usage: route_eval.py eval.json [skill_find.py] [--phase recon]")

eval_path = argv[0]
finder = argv[1] if len(argv) > 1 else os.path.expanduser("~/.hermes/arsenal/skill_find.py")
cases = json.load(open(eval_path, encoding="utf-8"))

rows = []
for c in cases:
    r = subprocess.run([sys.executable, finder, c["q"], "--phase", phase, "--top", "10", "--json"],
                       capture_output=True, text=True,
                       env={**os.environ, "SKILL_FIND_NOLOG": "1"})
    try:
        hits = json.loads(r.stdout)
    except Exception:
        hits = []
    names = [h["name"] for h in hits]
    rank = next((i + 1 for i, n in enumerate(names) if n in c["expect"]), 0)
    rows.append((c["q"], rank, names[:3]))

top1 = sum(1 for _, rk, _ in rows if rk == 1)
top3 = sum(1 for _, rk, _ in rows if 1 <= rk <= 3)
for q, rk, top in rows:
    tag = "OK  " if rk == 1 else ("~   " if 1 < rk <= 3 else "MISS")
    print(f"{tag} rank={rk or '-':>2}  {q}   -> {', '.join(top)}")
print(f"\nphase={phase}  TOP1 {top1}/{len(rows)}  TOP3 {top3}/{len(rows)}  MISS {len(rows)-top3}/{len(rows)}")
sys.exit(0 if top3 == len(rows) else 1)
