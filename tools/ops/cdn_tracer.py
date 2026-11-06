#!/usr/bin/env python3
"""CDN tracer: DNS chain, HTTP edge headers, certificate hostnames."""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import subprocess
import urllib.parse
import urllib.request

EDGE = ["cf-ray", "x-amz-cf-id", "x-cache", "via", "server", "x-edge-location"]


def dig(name: str) -> str:
    try:
        p = subprocess.run(["dig", "+short", name], capture_output=True, text=True, timeout=8)
        return p.stdout.strip()
    except Exception:
        return ""


def http_headers(domain: str) -> dict:
    try:
        req = urllib.request.Request("https://" + domain, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12, context=ssl._create_unverified_context()) as r:
            return {k: r.headers.get(k, "") for k in EDGE} | {"status": r.status}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def crt(domain: str) -> list[str]:
    try:
        url = "https://crt.sh/?q=%25." + urllib.parse.quote(domain) + "&output=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            rows = json.loads(r.read().decode("utf-8", errors="replace"))
        return sorted({n.strip().lower() for row in rows for n in row.get("name_value", "").splitlines() if n.strip()})
    except Exception:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description="CDN 溯源：DNS/边缘头/证书")
    ap.add_argument("domain")
    ap.add_argument("--all", action="store_true", help="include crt.sh hosts")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    d = args.domain
    out = {"domain": d, "a": dig(d), "cname": dig("www." + d), "headers": http_headers(d)}
    if args.all:
        out["crt"] = crt(d)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"domain={d}")
        print(f"A:\n{out['a']}")
        print(f"www CNAME:\n{out['cname']}")
        print("headers:", out["headers"])
        if "crt" in out:
            print(f"crt={len(out['crt'])}")
            for h in out["crt"][:20]:
                print("  ", h)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
