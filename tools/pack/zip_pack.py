#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把干净树打成 zip（长路径安全），并校验包内不含被驱逐的路径/扩展名。"""
from __future__ import annotations

import os
import sys
import zipfile

ROOT = r"C:\Users\Administrator\Desktop\TGSEC-Qtzuu-clean-20261105"
OUT = r"C:\Users\Administrator\Desktop\TGSEC-Qtzuu-clean-20261105.zip"
TOP = "TGSEC-Qtzuu-clean-20261105"

BANNED_PATH = ("sessions/", "storages/", "session_projcache", "profiles/", "attachments/",
               "hermes-skills/", "case/", "arsenal.db", ".claude/", "node_modules/")
BANNED_EXT = {".db", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".exe", ".dll",
              ".apk", ".ipa", ".docx", ".xlsx", ".pdb", ".so"}


def _lp(p: str) -> str:
    p = os.path.abspath(p)
    return p if p.startswith("\\\\?\\") else "\\\\?\\" + p


def main() -> int:
    if os.path.exists(OUT):
        os.remove(OUT)
    count = 0
    bad: list[str] = []
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            for name in filenames:
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, ROOT).replace("\\", "/")
                low = rel.lower()
                if any(b in low for b in BANNED_PATH) or os.path.splitext(low)[1] in BANNED_EXT:
                    bad.append(rel)
                    continue
                zf.write(_lp(path), arcname=f"{TOP}/{rel}")
                count += 1
    size = os.path.getsize(OUT)
    raw = 0
    for dirpath, _, filenames in os.walk(ROOT):
        for name in filenames:
            try:
                raw += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    print(f"zip: {OUT}")
    print(f"entries: {count}")
    print(f"size: {size/1048576:.1f} MB   raw: {raw/1048576:.1f} MB   ratio: {size/max(raw,1)*100:.1f}%")
    if bad:
        print(f"skipped-by-policy: {len(bad)}")
        for b in bad[:20]:
            print("   " + b)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
