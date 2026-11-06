#!/usr/bin/env python3
"""HTTP proxy classifier: CONNECT reachability + origin/header leakage."""
from __future__ import annotations

import argparse
import http.client
import json
import socket
from pathlib import Path


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def check(proxy: str, target: str = "httpbin.org", timeout: float = 8) -> dict:
    if "://" in proxy:
        proxy = proxy.split("://", 1)[1]
    host, _, port = proxy.partition(":")
    try:
        c = http.client.HTTPConnection(host, int(port or 8080), timeout=timeout)
        c.set_tunnel(target, 80)
        c.request("GET", "/ip", headers={"User-Agent": "Mozilla/5.0", "Host": target})
        r = c.getresponse()
        body = r.read(2048).decode("utf-8", "replace")
        c.close()
        origin = ""
        try:
            origin = json.loads(body).get("origin", "")
        except Exception:
            pass
        leaks = [h for h in ("Via", "X-Forwarded-For", "Forwarded", "Proxy-Connection") if r.getheader(h)]
        return {"proxy": proxy, "status": r.status, "origin": origin, "leak_headers": leaks,
                "class": "elite" if not leaks else ("anonymous" if leaks else "unknown")}
    except Exception as e:
        return {"proxy": proxy, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="代理匿名性分类")
    ap.add_argument("--file", "-f", required=True)
    ap.add_argument("--target", default="httpbin.org")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    proxies = [l.strip() for l in Path(args.file).read_text().splitlines() if l.strip() and not l.startswith("#")]
    out = [check(p, args.target, args.timeout) for p in proxies]
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for x in out:
            print(x.get("proxy"), x.get("class", "ERR"), x.get("origin", ""), x.get("leak_headers", ""), x.get("error", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
