#!/usr/bin/env python3
"""Scope file helper: check targets and add explicit entries (no auto-expansion)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/ops"))
from scope_lint import host_of, load_scope, matches  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Scope 管理：in_scope / add / list")
    ap.add_argument("action", choices=["in_scope", "add", "list"])
    ap.add_argument("target", nargs="?")
    ap.add_argument("--scope-file", "-f", default="scope.txt")
    args = ap.parse_args()
    path = Path(args.scope_file)
    entries = load_scope(str(path) if path.exists() else None, [])

    if args.action == "list":
        for e in entries:
            print(e)
        return 0
    if not args.target:
        ap.error("target required")
    host = host_of(args.target)
    if not host:
        ap.error("target has no host")
    if args.action == "in_scope":
        ok = any(matches(host, e)[0] for e in entries)
        print(f"{'ALLOW' if ok else 'DENY'} {host} ({len(entries)} scope entries)")
        return 0 if ok else 2
    if args.action == "add":
        if host not in entries:
            entries.append(host)
            path.write_text("\n".join(entries) + "\n", encoding="utf-8")
            print(f"ADDED {host} -> {path}")
        else:
            print(f"PRESENT {host}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
