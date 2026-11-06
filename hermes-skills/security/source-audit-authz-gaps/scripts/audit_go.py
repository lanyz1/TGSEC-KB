#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Go 项目危险模式定向扫描: 只列候选点, 不判结论(人工复核)。

与 gosec 互补, 两个都跑:
  本脚本 — 宽匹配, 能扫到 `Sprintf(...) + db.Raw(...)` 这类组合(gosec 认不出)
  gosec  — 能扫到依赖数据流/SSA 的规则(本脚本不能)

用法:
    python audit_go.py <源码根> [--skip vendor,node_modules] [--per-pattern 40]
"""
import argparse
import os
import re

# (名称, 正则, flags) —— 宁可多报, 结论靠人工
PATTERNS = [
    ("CMD_EXEC", r"exec\.Command(Context)?\(", 0),
    ("SH_C", r'"(/bin/)?(ba)?sh"\s*,\s*"-c"', 0),
    ("SHELL_STR", r"Sprintf\([^)]*(command|exec|sh |bash|cmd)", 0),
    ("SQL_SPRINTF", r"Sprintf\([^)]*(SELECT|WHERE|FROM|INSERT|UPDATE|DELETE|SHOW|ORDER BY)", re.I),
    ("SQL_RAW", r"\.Raw\(", 0),
    ("PATH_JOIN", r"filepath\.Join\(", 0),
    ("TEMPLATE_HTML", r"template\.(HTML|JS|URL)\(", 0),
    ("UNMARSHAL", r"(json|yaml)\.Unmarshal\(", 0),
    ("WEAK_RAND", r"math/rand|\.Intn\(", 0),
    ("TODO_AUTH", r"(TODO|FIXME|XXX)[^\n]*(auth|permission|check|validat|sanitiz|escape)", re.I),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--skip", default="vendor,node_modules,.git,testdata")
    ap.add_argument("--per-pattern", type=int, default=40)
    a = ap.parse_args()
    skips = tuple("/" + s.strip("/") + "/" for s in a.skip.split(",") if s.strip())

    hits = {name: [] for name, _, _ in PATTERNS}
    nfiles = 0
    for dp, dns, fns in os.walk(a.root):
        here = dp.replace("\\", "/") + "/"
        if any(s in here for s in skips):
            dns[:] = []
            continue
        for fn in fns:
            if not fn.endswith(".go") or fn.endswith("_test.go"):
                continue
            nfiles += 1
            p = os.path.join(dp, fn)
            short = p.replace("\\", "/")
            for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                if len(line) > 400:
                    continue
                for name, pat, flags in PATTERNS:
                    if re.search(pat, line, flags):
                        hits[name].append("%s:%d  %s" % (short, i, line.strip()[:150]))

    print("扫描 %d 个 .go 文件\n" % nfiles)
    for name, _, _ in PATTERNS:
        v = hits[name]
        print("=== %s (%d 处) ===" % (name, len(v)))
        for line in v[: a.per_pattern]:
            print("  " + line)
        if len(v) > a.per_pattern:
            print("  ... 还有 %d 处" % (len(v) - a.per_pattern))
        print()
    print("提醒: 命中的绝大多数是安全的(参数化传递)。真正要看『用户输入 -> 变量 -> 参数』这条链是否可控。")


if __name__ == "__main__":
    main()
