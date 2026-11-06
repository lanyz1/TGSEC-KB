#!/usr/bin/env python3
"""Sample triage: file type, hashes, zip members, high-signal strings."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

STR_RE = re.compile(rb"[\x20-\x7e]{5,}")


def main() -> int:
    ap = argparse.ArgumentParser(description="样本分诊：类型/哈希/包成员/字符串")
    ap.add_argument("--path", "-p", required=True, help="apk/ipa/exe/elf/jar sample")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    path = Path(args.path)
    if not path.exists():
        ap.error(f"not found: {path}")

    data = path.read_bytes()
    out = {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "file": subprocess.run(["file", "-b", str(path)], capture_output=True, text=True).stdout.strip(),
        "zip": zipfile.is_zipfile(path),
        "members": [],
        "urls": [],
    }
    if out["zip"]:
        with zipfile.ZipFile(path) as z:
            out["members"] = z.namelist()[:200]
            for info in z.infolist():
                if info.file_size > 20 * 1024 * 1024:
                    continue
                if not re.search(r"\.(dex|so|xml|json|js|txt|properties|yml|yaml)$", info.filename, re.I):
                    continue
                try:
                    blob = z.read(info)
                except Exception:
                    continue
                for s in STR_RE.findall(blob):
                    text = s.decode("utf-8", errors="replace")
                    if "http://" in text or "https://" in text:
                        out["urls"].append(text[:300])
    out["urls"] = sorted(set(out["urls"]))[:100]

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"path={out['path']} size={out['size']} zip={out['zip']}")
        print(f"file={out['file']}")
        print(f"sha256={out['sha256']}")
        print(f"members={len(out['members'])} urls={len(out['urls'])}")
        for u in out["urls"][:10]:
            print("  ", u)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
