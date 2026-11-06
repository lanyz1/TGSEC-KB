#!/usr/bin/env python3
"""Origin recon: DNS A/AAAA, crt.sh hostnames, HTTP server headers."""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import urllib.parse
import urllib.request


def dns(name: str) -> dict:
    out = {}
    for family, label in ((socket.AF_INET, "A"), (socket.AF_INET6, "AAAA")):
        try:
            out[label] = sorted({x[4][0] for x in socket.getaddrinfo(name, None, family)})
        except OSError:
            out[label] = []
    return out


def crt(name: str) -> list[str]:
    url = "https://crt.sh/?q=%25." + urllib.parse.quote(name) + "&output=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            rows = json.loads(r.read().decode("utf-8", errors="replace"))
        return sorted({n.strip().lower() for row in rows for n in row.get("name_value", "").splitlines() if n.strip()})
    except Exception:
        return []


def headers(name: str) -> dict:
    try:
        req = urllib.request.Request("https://" + name, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12, context=ssl.create_default_context()) as r:
            return {"status": r.status, "server": r.headers.get("server", ""),
                    "location": r.headers.get("location", ""), "via": r.headers.get("via", "")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="源站/资产侦察：DNS + 证书 + 响应头")
    ap.add_argument("--domain", "-d", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-crt", action="store_true")
    args = ap.parse_args()
    out = {"domain": args.domain, "dns": dns(args.domain)}
    if not args.no_crt:
        out["crt"] = crt(args.domain)
    out["headers"] = headers(args.domain)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"domain={out['domain']}")
        print(f"A={out['dns']['A']} AAAA={out['dns']['AAAA']}")
        if "crt" in out:
            print(f"crt_hosts={len(out['crt'])}")
            for h in out["crt"][:30]:
                print("  ", h)
        print("headers:", out["headers"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
