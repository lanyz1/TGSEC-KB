#!/usr/bin/env python3
"""White-label gambling family probe: generic GET + JS/domain inventory."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "tools/ops/kit_run.py"
CASES = Path("/root/cases")


def main() -> int:
    ap = argparse.ArgumentParser(description="白标博彩家族通用探针（GET + JS/域名清单）")
    ap.add_argument("--family", required=True, help="family label, e.g. 1z/mm8/whitelabel")
    ap.add_argument("--base", required=True, help="authorized base URL")
    ap.add_argument("--case", required=True, help="case name")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    host = urlparse(args.base).hostname
    if not host:
        ap.error("--base needs a hostname")
    cmd = [sys.executable, str(KIT), "run", "--kit", "web", "-u", args.base,
           "--case", args.case, "--scope", host, "--timeout", str(args.timeout)]
    if args.dry_run:
        cmd.append("--dry-run")
    rc = subprocess.run(cmd).returncode
    if rc != 0 or args.dry_run:
        return rc

    case = CASES / args.case
    art = case / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    html = ""
    status = None
    try:
        req = urllib.request.Request(args.base, headers={"User-Agent": "TGSEC-family-probe/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            status = r.status
            html = r.read(2_000_000).decode("utf-8", errors="replace")
        (art / "homepage.html").write_text(html, encoding="utf-8")
    except Exception as e:
        (art / "homepage-error.txt").write_text(repr(e), encoding="utf-8")

    scripts = sorted(set(re.findall(r'<script[^>]+src=["\']([^"\']+)', html, re.I)))
    actions = sorted(set(re.findall(r'<form[^>]+action=["\']([^"\']+)', html, re.I)))
    domains = sorted(set(re.findall(r'https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,})', html)))
    data = {"family": args.family, "base": args.base, "status": status,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "scripts": [urljoin(args.base, s) for s in scripts],
            "form_actions": [urljoin(args.base, a) for a in actions],
            "domains": domains}
    (art / "family.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[family] {args.family} status={status} scripts={len(scripts)} forms={len(actions)} domains={len(domains)}")
    print(f"[family] {art / 'family.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
