#!/usr/bin/env python3
"""APK quick recon: zip members + strings for URLs/domains/secret-like keys."""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PATTERNS = {
    "urls": re.compile(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{4,200}"),
    "domains": re.compile(rb"\b(?:[A-Za-z0-9-]+\.)+(?:com|cn|net|io|app|xyz|top|cc|co|me|org|vip)\b"),
    "keys": re.compile(rb"(?i)(?:api[_-]?key|secret|token|appkey|app_secret|access[_-]?key)[\"'\s:=]{1,4}[A-Za-z0-9_\-]{8,80}"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="APK 快速侦察：zip 成员 + 字符串（URL/域名/疑似密钥）")
    ap.add_argument("apk", nargs="?", help="path to .apk")
    ap.add_argument("--file", "-f", dest="file", help="path to .apk")
    ap.add_argument("--output", "-o", help="output JSON path")
    args = ap.parse_args()
    path = Path(args.apk or args.file or "")
    if not path or not path.exists():
        ap.error("APK path required and must exist")
    if not zipfile.is_zipfile(path):
        ap.error(f"not a zip/apk: {path}")

    found = {k: set() for k in PATTERNS}
    members = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            members.append(info.filename)
            if info.file_size > 80 * 1024 * 1024:
                continue
            if not re.search(r"\.(dex|so|xml|json|js|txt|properties|yml|yaml)$", info.filename, re.I):
                continue
            try:
                data = z.read(info)
            except Exception:
                continue
            for key, pat in PATTERNS.items():
                for m in pat.findall(data):
                    found[key].add(m.decode("utf-8", errors="replace"))

    out = {"apk": str(path), "checked_at": datetime.now(timezone.utc).isoformat(),
           "members": len(members), "urls": sorted(found["urls"])[:200],
           "domains": sorted(found["domains"])[:200], "keys": sorted(found["keys"])[:100]}
    target = Path(args.output) if args.output else path.with_suffix(".recon.json")
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[apk] members={len(members)} urls={len(out['urls'])} domains={len(out['domains'])} keys={len(out['keys'])}")
    print(f"[apk] {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
