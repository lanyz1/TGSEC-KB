#!/usr/bin/env python3
"""Windows LPE surface: local privileged tokens / patches, or parse systeminfo."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20, shell=False)
        return (p.stdout + p.stderr).strip()
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def parse_systeminfo(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if k in ("OS Name", "OS Version", "System Type", "Host Name", "Hotfix(s)"):
            out[k] = v
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Windows 提权面检查（本地或 systeminfo 文本）")
    ap.add_argument("--systeminfo", help="saved systeminfo.txt")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", "-o")
    args = ap.parse_args()
    data: dict = {"platform": platform.platform()}
    if args.systeminfo:
        data["systeminfo"] = parse_systeminfo(Path(args.systeminfo).read_text(errors="ignore"))
    elif platform.system() == "Windows":
        data["whoami_priv"] = run(["whoami", "/priv"])
        data["systeminfo_raw"] = run(["systeminfo"])[:20000]
        data["hotfix"] = run(["wmic", "qfe", "list", "brief"])
    else:
        ap.error("not Windows; pass --systeminfo <saved systeminfo.txt>")
    if args.out:
        Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
