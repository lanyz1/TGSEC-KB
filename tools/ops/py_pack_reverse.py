#!/usr/bin/env python3
"""PyInstaller pack triage: detect CArchive and use pyinstxtractor if present."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

MAGIC = b"MEI\014\013\012\013\016"


def main() -> int:
    ap = argparse.ArgumentParser(description="PyInstaller 包分析")
    ap.add_argument("path")
    ap.add_argument("--out", default="/tmp/pyinst_extract")
    args = ap.parse_args()
    p = Path(args.path)
    if not p.exists():
        ap.error(f"not found: {p}")
    data = p.read_bytes()[:1024 * 1024]
    found = data.find(MAGIC)
    out = {"path": str(p), "bytes": p.stat().st_size, "pyinstaller": found >= 0, "magic_offset": hex(found) if found >= 0 else None}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if found < 0:
        return 0
    exe = shutil.which("pyinstxtractor") or shutil.which("pyinstxtractor.py")
    script = Path("/root/tools/pyinstxtractor.py")
    if exe:
        cmd = [exe, str(p)]
    elif script.exists():
        cmd = ["python3", str(script), str(p)]
    else:
        print("[plan] pyinstxtractor missing; install: pip install pyinstxtractor-ng or clone pyinstxtractor")
        return 0
    print("[run]", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
