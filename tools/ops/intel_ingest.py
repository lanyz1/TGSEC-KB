#!/usr/bin/env python3
"""Intel ingest: inventory local intel files and rebuild the vuln DB."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="本地情报摄入")
    ap.add_argument("--path", default="/root/intel")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()
    root = Path(args.path)
    files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
    by_ext: dict[str, int] = {}
    for p in files:
        by_ext[p.suffix.lower() or "-"] = by_ext.get(p.suffix.lower() or "-", 0) + 1
    out = {"path": str(root), "files": len(files), "bytes": sum(p.stat().st_size for p in files), "by_ext": by_ext}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.rebuild:
        script = "/root/.hermes/arsenal/vuln_build.py"
        print("[rebuild]", script)
        return subprocess.call(["python3", script])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
