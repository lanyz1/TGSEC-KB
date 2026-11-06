#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按发布口径把 tgsec-kb 拷成干净树（长路径安全）。

规则：
- 丢目录：arsenal / hermes-skills / .claude / .git / node_modules / __pycache__ /
  AboutSecurity-Dic / wordlists / knowledge / learning / .absorb-backup-*
- 丢扩展名：媒体、二进制、压缩包、Office、installer、db
- 丢文件名：files_exploits.csv / files_shellcodes.csv / KEV*.json / pocs*.json / *.log / *.out
- 丢 > 2MB 的单文件（词表、poc blob、巨型 json）
"""
from __future__ import annotations

import os
import shutil
import sys

SRC = r"C:\Users\Administrator\.dsh\tgsec-kb"
DST = r"C:\Users\Administrator\Desktop\TGSEC-Qtzuu-clean-20261105"

DROP_EXT = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
    ".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav",
    ".ipa", ".apk", ".dll", ".pdb", ".exe", ".sys", ".msi", ".cab",
    ".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".xz", ".bz2",
    ".img", ".iso", ".bin", ".vhd", ".vmdk",
    ".xls", ".xlsx", ".doc", ".docx", ".ppt", ".pptx",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".db", ".sqlite", ".sqlite3", ".mdb",
    ".jar", ".class", ".so", ".dylib", ".o", ".a", ".lib", ".obj",
}
DROP_DIR = {
    "hermes-skills", ".claude", ".git", "node_modules", "__pycache__", "case", "logs",
    "AboutSecurity-Dic", "wordlists", "knowledge", "learning", ".absorb-backup-20261105",
    ".github", "ai-config",
}
DROP_NAME_PREFIX = ("files_exploits", "files_shellcodes")
DROP_NAME_GLOB = ("KEV", "pocs")
DROP_NAME_SUFFIX = (".log", ".out", ".tmp", ".bak")
MAX_BYTES = 2 * 1024 * 1024


def _lp(p: str) -> str:
    p = os.path.abspath(p)
    return p if p.startswith("\\\\?\\") else "\\\\?\\" + p


def ensure_dir(path: str) -> None:
    p = _lp(path)
    if not os.path.isdir(p):
        os.makedirs(p, exist_ok=True)


def copy_file(src: str, dst: str) -> None:
    with open(_lp(src), "rb") as fi, open(_lp(dst), "wb") as fo:
        shutil.copyfileobj(fi, fo, 1 << 20)


def keep(rel: str, size: int) -> tuple[bool, str]:
    parts = rel.split(os.sep)
    for p in parts[:-1]:
        if p in DROP_DIR:
            return False, f"dir:{p}"
    ext = os.path.splitext(rel)[1].lower()
    if ext in DROP_EXT:
        return False, f"ext:{ext}"
    name = parts[-1]
    if name.startswith(DROP_NAME_PREFIX):
        return False, "name"
    for g in DROP_NAME_GLOB:
        if name.startswith(g) and name.endswith(".json"):
            return False, "name"
    if name.endswith(DROP_NAME_SUFFIX):
        return False, "suffix"
    if size > MAX_BYTES:
        return False, "big"
    return True, ""


def main() -> int:
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST, exist_ok=True)
    kept = 0
    kept_bytes = 0
    reasons: dict[str, int] = {}
    big: list[tuple[str, float]] = []
    for dirpath, dirnames, filenames in os.walk(SRC):
        dirnames[:] = [d for d in dirnames if d not in DROP_DIR]
        for name in filenames:
            src = os.path.join(dirpath, name)
            rel = os.path.relpath(src, SRC)
            try:
                size = os.path.getsize(src)
            except OSError:
                continue
            ok, why = keep(rel, size)
            if not ok:
                reasons[why] = reasons.get(why, 0) + 1
                if why == "big":
                    big.append((rel, size / 1048576))
                continue
            dst = os.path.join(DST, rel)
            ensure_dir(os.path.dirname(dst))
            copy_file(src, dst)
            kept += 1
            kept_bytes += size
    print(f"kept {kept} files  {kept_bytes/1048576:.1f} MB -> {DST}")
    print("dropped: " + ", ".join(f"{k}={v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])))
    if big:
        print(f"dropped-big top10:")
        for rel, mb in sorted(big, key=lambda x: -x[1])[:10]:
            print(f"   {mb:6.1f}MB  {rel}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
    raise SystemExit(main())
