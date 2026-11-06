#!/usr/bin/env python3
"""CDN range inventory: fetch provider CIDRs and optionally classify an IP."""
from __future__ import annotations

import argparse
import ipaddress
import json
import urllib.request

SOURCES = {
    "cloudflare": ["https://www.cloudflare.com/ips-v4", "https://www.cloudflare.com/ips-v6"],
    "aws": ["https://ip-ranges.amazonaws.com/ip-ranges.json"],
    "gcp": ["https://www.gstatic.com/ipranges/cloud.json"],
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def collect(provider: str) -> list[str]:
    nets = []
    for url in SOURCES[provider]:
        text = fetch(url)
        if provider == "aws":
            data = json.loads(text)
            nets += [p["ip_prefix"] for p in data.get("prefixes", [])]
            nets += [p["ipv6_prefix"] for p in data.get("ipv6_prefixes", [])]
        elif provider == "gcp":
            data = json.loads(text)
            nets += [p["ipv4Prefix"] for p in data.get("prefixes", []) if "ipv4Prefix" in p]
            nets += [p["ipv6Prefix"] for p in data.get("prefixes", []) if "ipv6Prefix" in p]
        else:
            nets += [x.strip() for x in text.splitlines() if x.strip()]
    return sorted(set(nets))


def main() -> int:
    ap = argparse.ArgumentParser(description="CDN 段清单/归属判定")
    ap.add_argument("--provider", choices=[*SOURCES, "all"], default="cloudflare")
    ap.add_argument("--check", help="IP to classify")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    providers = list(SOURCES) if args.provider == "all" else [args.provider]
    result: dict = {p: collect(p) for p in providers}
    if args.check:
        ip = ipaddress.ip_address(args.check)
        hits = []
        for p, nets in result.items():
            if any(ip in ipaddress.ip_network(n, strict=False) for n in nets if "/" in n):
                hits.append(p)
        result["check"] = {"ip": args.check, "providers": hits}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for p, nets in result.items():
            if p == "check":
                print(f"check={nets}")
            else:
                print(f"{p}: {len(nets)} ranges")
                for n in nets[:10]:
                    print("  ", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
