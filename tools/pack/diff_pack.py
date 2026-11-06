#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对账：zip 里的内容 vs 当前 KB，逐字节给出「同一份 / 仅脱敏 / 被删 / 被排除」四类。"""
from __future__ import annotations

import hashlib
import os
import sys
import zipfile

KB = r"C:\Users\Administrator\.dsh\tgsec-kb"
ZIP = r"C:\Users\Administrator\Desktop\TGSEC-Qtzuu-clean-20261105.zip"
TOP = "TGSEC-Qtzuu-clean-20261105/"

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
MAX_BYTES = 2 * 1024 * 1024


def _lp(p: str) -> str:
    p = os.path.abspath(p)
    return p if p.startswith("\\\\?\\") else "\\\\?\\" + p


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    zf = zipfile.ZipFile(ZIP)
    zip_map: dict[str, str] = {}
    for info in zf.infolist():
        if info.is_dir():
            continue
        rel = info.filename[len(TOP):] if info.filename.startswith(TOP) else info.filename
        zip_map[rel.replace("/", os.sep)] = sha(zf.read(info))

    same = diff = 0
    eligible: set[str] = set()
    excluded: dict[str, int] = {}
    size = 0
    for dirpath, dirnames, filenames in os.walk(KB):
        dirnames[:] = [d for d in dirnames if d not in DROP_DIR]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, KB)
            parts = rel.split(os.sep)
            if any(p in DROP_DIR for p in parts[:-1]):
                excluded["dir"] = excluded.get("dir", 0) + 1
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in DROP_EXT:
                excluded["ext"] = excluded.get("ext", 0) + 1
                continue
            if name.startswith(("files_exploits", "files_shellcodes")) or \
               (name.startswith("KEV") and name.endswith(".json")) or \
               (name.startswith("pocs") and name.endswith(".json")) or \
               name.endswith((".log", ".out", ".tmp", ".bak")) or name.startswith(".tgsec-bootstrapped"):
                excluded["name"] = excluded.get("name", 0) + 1
                continue
            try:
                size = os.path.getsize(_lp(path))
            except OSError:
                excluded["unreadable"] = excluded.get("unreadable", 0) + 1
                continue
            if size > MAX_BYTES:
                excluded["big"] = excluded.get("big", 0) + 1
                continue
            eligible.add(rel)
            digest = zip_map.get(rel)
            if digest is None:
                continue
            with open(_lp(path), "rb") as fh:
                if sha(fh.read()) == digest:
                    same += 1
                else:
                    diff += 1

    missing = sorted(eligible - set(zip_map))
    extra = sorted(set(zip_map) - eligible)

    print(f"zip entries            : {len(zip_map)}")
    print(f"KB 符合口径的文件       : {len(eligible)}")
    print(f"  逐字节一致            : {same}")
    print(f"  内容有差异（脱敏过）   : {diff}")
    print(f"  口径内但不在 zip 里    : {len(missing)}")
    for m in missing[:20]:
        print("    - " + m)
    print(f"排除（不进包）          : {sum(excluded.values())}  " + str(excluded))
    if extra:
        print(f"zip 独有（KB 已无）     : {len(extra)}")
        for e in extra[:10]:
            print("    + " + e)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
