#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apidog/Hyperf 风格控制器的鉴权覆盖差分扫描。

用法:
    python audit_apidog_mw.py <app/Controller 目录> [域关键字=filters, 默认 admin]

输出:
    ① 中间件组合频次(孤例/缺环 = 嫌疑)
    ② 零中间件控制器及其可写路由(完全未授权面)
    ③ 域内单闸门控制器(唯一中间件校验什么决定危害)

判定要点:
    零中间件 Admin 控制器 = 完全未授权;
    ['AdminMiddleware'] 单闸门 = 若与 .env 常量比相等, 知道常量即管理员 API;
    有 Admin+Login+Log 缺 Permission = 垂直越权;
    注入型中间件(if (checkAuth) { set uid } 无 else) 单独出现 = fail-open。
"""

import os
import re
import sys
from collections import Counter

WRITE_HINT = ("create", "update", "delete", "grant", "send", "audit",
              "settle", "review", "approve", "batch", "revoke", "reset")

VER_RE = re.compile(r'@ApiVersion\(version="([^"]+)"\)')
MW_RE = re.compile(r'@Middleware\((\w+)::class\)')
ROUTE_RE = re.compile(r'@(?:Get|Post|Put|Delete|Patch)Api\(path="([^"]+)"')


def scan(root):
    rows = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".php"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                src = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            ver = VER_RE.search(src)
            rows.append({
                "file": os.path.relpath(p, root).replace("\\", "/"),
                "ver": ver.group(1) if ver else "",
                "mws": MW_RE.findall(src),
                "routes": ROUTE_RE.findall(src),
            })
    return rows


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = os.path.normpath(sys.argv[1])
    domain = sys.argv[2] if len(sys.argv) > 2 else "admin"
    rows = scan(root)
    print(f"[i] 控制器总数 {len(rows)}  (域关键字: {domain})")

    print("\n[i] 中间件组合频次(孤例/缺环即嫌疑):")
    for combo, n in Counter((r["ver"], tuple(sorted(set(r["mws"])))) for r in rows).most_common(20):
        print(f"    {n:4d}  {combo[0] or '(无 version)':12s} {list(combo[1])}")

    dom = [r for r in rows if domain in (r["ver"] + r["file"]).lower()]
    print(f"\n[i] 域内控制器 {len(dom)}")

    print("\n===== ① 零中间件(完全未授权) =====")
    zero = [r for r in dom if not r["mws"]]
    for r in sorted(zero, key=lambda x: -len(x["routes"])):
        wr = [u for u in r["routes"] if any(k in u.lower() for k in WRITE_HINT)]
        flag = "  <<< 含可写路由" if wr else ""
        print(f"  [{r['ver'] or '-'}] {len(r['routes'])} 路由 {r['file']}{flag}")
        for u in (wr or r["routes"])[:5]:
            print(f"        {u}")
    if not zero:
        print("  (无)")

    print("\n===== ② 单闸门(仅一个中间件) =====")
    single = [r for r in dom if len(r["mws"]) == 1]
    for r in sorted(single, key=lambda x: -len(x["routes"]))[:20]:
        wr = [u for u in r["routes"] if any(k in u.lower() for k in WRITE_HINT)]
        print(f"  [{r['ver'] or '-'}] gate={r['mws'][0]:24s} {len(r['routes']):2d} 路由 "
              f"写{len(wr):2d}  {r['file']}")
    print(f"  ... 共 {len(single)} 个")

    print("\n===== ③ 缺环(有 Admin 无 Login / 有 Login 无 Permission) =====")
    for r in dom:
        s = set(r["mws"])
        if not any("Admin" in m for m in s) and not any("Login" in m for m in s):
            continue
        miss = [m for m in ("AdminMiddleware", "AdminLoginMiddleware", "AdminPermissionMiddleware")
                if m not in s and any(x in s for x in ("AdminMiddleware", "AdminLoginMiddleware"))]
        if miss and s:
            print(f"  缺 {','.join(miss):50s} 有={sorted(s)}  {r['file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
