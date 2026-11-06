#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 SPA bundle 提取权威 (path, method) 路由表, 并对只读类路径做未授权探测。

依赖: 仅 stdlib + curl(走本机或跳板 SOCKS 代理)。

用法:
  # 1) 提取(gRPC-gateway/Connect 生成的 client 最容易, 普通 axios/fetch 也能抓)
  python extract_route_table.py routes bundle.js [bundle2.js ...] -o api_map.json

  # 2) 未授权探测(只读路径; 破坏性路径自动跳过并在日志里标注)
  python extract_route_table.py probe api_map.json https://console.example.com \
      --proxy socks5h://127.0.0.1:20812 --delay 0.8 --log probe.log

判定约定: 401=受保护 / 405=方法不对(路由存在) / 404=未挂载 / 400=已过鉴权(候选) / 200=命中
"""
import argparse, json, re, subprocess, sys, time

PAIR = re.compile(r'path\s*:\s*"(/api/[^"]{2,160})"\s*,\s*method\s*:\s*"([A-Z]+)"')
BARE = re.compile(r'"(/api/[A-Za-z][A-Za-z0-9_]{2,60})"')
READONLY = re.compile(r'(Get|List|Query|Check|Search|Stat|Info|Detail|Export|View|Show)', re.I)
DESTRUCTIVE = re.compile(r'(Delete|Remove|Drop|Cancel|Reset|Refund|Kill|Stop|Disable|Destroy|Purge|Abort)', re.I)


def cmd_routes(args):
    pairs, bare = {}, set()
    for f in args.files:
        js = open(f, "r", encoding="utf-8", errors="ignore").read()
        for m in PAIR.finditer(js):
            pairs[m.group(1)] = m.group(2).upper()
        for m in BARE.finditer(js):
            bare.add(m.group(1))
    only_bare = sorted(b for b in bare if b not in pairs)
    print(f"[routes] path+method 配对: {len(pairs)} 条")
    print(f"[routes] 仅裸路径(多为方法名缩写/前缀, 需自行拼名字空间): {len(only_bare)} 条")
    for p in only_bare[:40]:
        print(f"    ? {p}")
    out = {p: {"method": m, "path_class": "destructive" if DESTRUCTIVE.search(p) else "readonly"}
           for p, m in sorted(pairs.items())}
    if args.out:
        json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[routes] 已写 {args.out}")
    print(f"[routes] 只读类 {sum(1 for v in out.values() if v['path_class']=='readonly')} / "
          f"破坏类 {sum(1 for v in out.values() if v['path_class']=='destructive')}")


def probe(base, path, method, proxy, timeout=20):
    url = base.rstrip("/") + path
    cmd = ["curl", "-s", "-k", "--max-time", str(timeout),
           "-o", "-", "-w", "\n%{http_code}|%{size_download}",
           "-X", method, "-H", "Content-Type: application/json"]
    if method in ("POST", "PUT", "PATCH"):
        cmd += ["-d", "{}"]
    if proxy:
        cmd += ["--proxy", proxy]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 8)
        raw = r.stdout.decode("utf-8", "ignore")
        body, _, meta = raw.rpartition("\n")
        code, _, size = meta.partition("|")
        return code, size, body[:200].replace("\n", " ")
    except Exception as e:
        return "ERR", "0", str(e)[:100]


def verdict(code, body):
    if code == "200":
        return "HIT"
    if code == "400" or "is not set" in body or "field \"" in body:
        return "CANDIDATE(passed-auth)"
    if code == "401" or code == "403":
        return "protected"
    if code == "405":
        return "route-exists"
    if code == "404":
        return "not-mounted"
    return "other"


def cmd_probe(args):
    routes = json.load(open(args.map, encoding="utf-8"))
    log = open(args.log, "a", encoding="utf-8") if args.log else None
    n = hits = 0
    for path, meta in sorted(routes.items()):
        if DESTRUCTIVE.search(path):
            line = f"[skip] {path} <- 破坏性动词, 不测"
            print(line); (log.write(line + "\n") if log else None); continue
        if args.only_readonly and not READONLY.search(path):
            continue
        got = []
        for method in ("GET", "POST"):
            code, size, body = probe(args.base, path, method, args.proxy)
            v = verdict(code, body)
            got.append((method, code, size, v, body))
            n += 1
            if v in ("HIT", "CANDIDATE(passed-auth)"):
                hits += 1
            time.sleep(args.delay)
        line = f"  [{got[0][1]}/{got[1][1]}] {path} :: {got[0][3]} | {got[1][3]}"
        print(line); (log.write(line + "\n") if log else None)
        for m, c, s, v, b in got:
            if v in ("HIT", "CANDIDATE(passed-auth)"):
                detail = f"    !! {m} {path} -> {c} ({s}B) {b}"
                print(detail); (log.write(detail + "\n") if log else None)
    print(f"\n[probe] 探测 {n} 次 / 候选命中 {hits} 条")
    if n == 0:
        print("[probe] !! 探测 0 次 = 筛选条件把全部路径滤掉了, 不是'没漏洞';检查筛选正则")
    if log:
        log.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("routes"); r.add_argument("files", nargs="+"); r.add_argument("-o", "--out")
    p = sub.add_parser("probe")
    p.add_argument("map"); p.add_argument("base")
    p.add_argument("--proxy", default=None); p.add_argument("--delay", type=float, default=0.8)
    p.add_argument("--log", default=None); p.add_argument("--only-readonly", action="store_true")
    a = ap.parse_args()
    (cmd_routes if a.cmd == "routes" else cmd_probe)(a)


if __name__ == "__main__":
    sys.exit(main())
