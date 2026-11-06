#!/usr/bin/env python3
"""Scope gate: refuse to run active checks outside an explicit scope file."""
from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


def host_of(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    return (parsed.hostname or "").strip().lower().rstrip(".")


def load_scope(path: str | None, inline: list[str]) -> list[str]:
    entries: list[str] = []
    if path:
        p = Path(path)
        if not p.exists():
            raise SystemExit(f"[scope] scope file not found: {p}")
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                entries.append(line)
    entries.extend(inline)
    return entries


def matches(target: str, entry: str) -> tuple[bool, str]:
    entry = entry.strip().lower().rstrip(".")
    if not entry:
        return False, "empty"
    if entry == "*":
        return True, "wildcard *"
    # CIDR / single IP
    try:
        net = ipaddress.ip_network(entry, strict=False)
        ip = ipaddress.ip_address(target)
        return (ip in net), f"ip {ip} in {net}"
    except ValueError:
        pass
    # URL / hostname
    ehost = host_of(entry) if "://" in entry else entry
    if ehost.startswith("*."):
        suffix = ehost[2:]
        ok = target == suffix or target.endswith("." + suffix)
        return ok, f"wildcard {ehost}"
    return (target == ehost), f"exact {ehost}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Check a target against an explicit engagement scope")
    ap.add_argument("--target", required=True, help="URL, host or IP")
    ap.add_argument("--scope-file", help="one entry per line: host, *.host, CIDR, URL")
    ap.add_argument("--scope", action="append", default=[], help="inline scope entry (repeatable)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    target = host_of(args.target)
    if not target:
        print("[scope] cannot parse target host", file=sys.stderr)
        return 2
    entries = load_scope(args.scope_file, args.scope)
    if not entries:
        print("[scope] DENY: no scope file/entries; active testing requires explicit scope", file=sys.stderr)
        return 2

    for entry in entries:
        ok, why = matches(target, entry)
        if ok:
            result = {"ok": True, "target": target, "matched": entry, "reason": why, "entries": len(entries)}
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(f"[scope] ALLOW {target}  ({why})")
            return 0

    result = {"ok": False, "target": target, "matched": None, "reason": "no scope entry matched", "entries": len(entries)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"[scope] DENY {target}: no scope entry matched ({len(entries)} checked)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
