#!/usr/bin/env python3
"""Bulk string harvest from a large disassembly / JS bundle.

Usage: python3 harvest_bundle_strings.py <file> [outdir]

Why: once a mobile bundle or SPA has been decompiled you are looking at millions of lines; grepping one guessed
keyword at a time wastes rounds. This extracts the whole interesting surface in one pass and writes three files:
  <out>/paths.txt   quoted string constants containing '/', no whitespace -> candidate API routes + page paths
  <out>/hosts.txt   hostnames matching *.tld patterns (find sibling/undiscovered hosts)
  <out>/keylike.txt long hex / base64-ish literals (secrets, keys, ids) - review, never paste into a report

Print the counts and a sample first; feed the files back into the endpoint probe matrix.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

STR = re.compile(r"[\"']([^\"'\n]{2,200})[\"']")
PATHLIKE = re.compile(r"^[A-Za-z0-9_\-./{}$?=&%:]+$")
HOSTISH = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:network|ad|com|io|net|org|xyz|top|ru|cn|co|app|dev)")
HEX40 = re.compile(r"\b[0-9a-fA-F]{40}\b")
HEX64 = re.compile(r"\b[0-9a-fA-F]{64}\b")
B64ISH = re.compile(r"^[A-Za-z0-9+/=_-]{24,88}$")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/bundle_harvest")
    out.mkdir(parents=True, exist_ok=True)

    paths: set[str] = set()
    hosts: set[str] = set()
    keylike: set[str] = set()

    with src.open("r", errors="replace") as fh:
        for line in fh:
            for s in STR.findall(line):
                if "/" in s and " " not in s and PATHLIKE.match(s):
                    paths.add(s)
            for h in HOSTISH.findall(line):
                hosts.add(h.lower())
            for rx in (HEX40, HEX64):
                for m in rx.findall(line):
                    keylike.add(m)
            for s in STR.findall(line):
                if B64ISH.match(s) and not s.isalpha() and len(s) >= 24:
                    keylike.add(s)

    # keep only routes a server could serve; drop obvious static asset paths
    routes = sorted(p for p in paths if p.startswith("/") and not p.endswith((".png", ".jpg", ".svg", ".css")))
    (out / "paths.txt").write_text("\n".join(routes))
    (out / "hosts.txt").write_text("\n".join(sorted(hosts)))
    (out / "keylike.txt").write_text("\n".join(sorted(keylike)))

    print(f"routes  {len(routes):6d}  -> {out/'paths.txt'}")
    print(f"hosts   {len(hosts):6d}  -> {out/'hosts.txt'}")
    print(f"keylike {len(keylike):6d}  -> {out/'keylike.txt'}  (review locally; redact in reports)")
    for label, items in (("routes", routes), ("hosts", sorted(hosts))):
        print(f"\n--- {label} sample (first 25 of {len(items)}) ---")
        for it in items[:25]:
            print("  " + it)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
