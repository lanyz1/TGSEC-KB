#!/usr/bin/env python3
"""Stdlib fallback helpers: hash identification and tiny wordlist generation."""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse


def hash_id(s: str) -> str:
    s = s.strip()
    pats = [
        (r"^\$2[aby]\$\d{2}\$", "bcrypt"),
        (r"^\$argon2", "argon2"),
        (r"^\$1\$", "md5-crypt"),
        (r"^\$5\$", "sha256-crypt"),
        (r"^\$6\$", "sha512-crypt"),
        (r"^[a-f0-9]{32}$", "md5/ntlm"),
        (r"^[a-f0-9]{40}$", "sha1"),
        (r"^[a-f0-9]{64}$", "sha256"),
        (r"^[a-f0-9]{128}$", "sha512"),
    ]
    for pat, name in pats:
        if re.match(pat, s, re.I):
            return name
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="标准库降级工具")
    ap.add_argument("action", choices=["hash_id", "wordlist_gen"], nargs="?")
    ap.add_argument("value", nargs="*", help="hash value / URL")
    ap.add_argument("--list", action="store_true", dest="list_modes")
    args = ap.parse_args()
    if args.list_modes or not args.action:
        print("hash_id, wordlist_gen")
        return 0
    text = " ".join(args.value).strip(" -\t")
    if args.action == "hash_id":
        if not text:
            ap.error("hash value required")
        print(hash_id(text))
        return 0
    if not text:
        ap.error("URL required")
    host = urlparse(text).hostname or text
    words = {host, host.split(".")[0], "admin", "login", "api", "backup", "www", "test", "dev"}
    words |= {p for p in urlparse(text).path.split("/") if p}
    print("\n".join(sorted(words)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
