#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验发布包：结构白名单 + 包内凭据复扫。"""
from __future__ import annotations

import os
import re
import sys
import zipfile

ZIP = r"C:\Users\Administrator\Desktop\TGSEC-Qtzuu-clean-20261105.zip"
TEXT_EXT = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".py", ".ps1", ".sh", ".cmd",
            ".js", ".mjs", ".ts", ".go", ".php", ".rb", ".java", ".c", ".h", ".sql", ".conf",
            ".ini", ".toml", ".xml", ".html", ".css", ".rules", ".lua", ".pl", ".csv", ".gitignore"}
PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-ak", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aliyun", re.compile(r"\bLTAI[0-9A-Za-z]{12,24}\b")),
    ("openai", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}\b")),
    ("github", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|github_pat_[A-Za-z0-9_]{40,}")),
    ("slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("telegram", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{30,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("bearer", re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{24,})")),
    ("cookie", re.compile(r"(?i)\bset-cookie:[^\n]{0,80}?(?:session|token|sid|auth)[A-Za-z0-9_.-]*=([A-Za-z0-9%._~-]{20,})")),
    ("generic", re.compile(r"(?i)\b(api[_-]?key|apikey|secret[_-]?key|access[_-]?key|client[_-]?secret|auth[_-]?token|password|passwd)\b\s*[:=]\s*[\"']?([A-Za-z0-9/+=._-]{20,})")),
]
PLACEHOLDER = re.compile(r"(xxx|XXX|\*\*\*|your|YOUR|example|EXAMPLE|placeholder|redacted|REDACTED|1234567890|abcdef|0{8,}|<[^>]*>|\$\{|\.\.\.)", re.I)
BANNED = ("sessions/", "storages/", "session_projcache", "profiles/", "attachments/",
          "hermes-skills/", "arsenal.db", ".claude/", "node_modules/", "__pycache__")


def main() -> int:
    hits = 0
    scanned = 0
    banned = []
    names: list[str] = []
    with zipfile.ZipFile(ZIP) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            low = info.filename.lower()
            names.append(info.filename)
            if any(b in low for b in BANNED):
                banned.append(info.filename)
                continue
            if os.path.splitext(low)[1] not in TEXT_EXT or info.file_size > 4 * 1024 * 1024:
                continue
            try:
                text = zf.read(info).decode("utf-8", "replace")
            except Exception:
                continue
            scanned += 1
            for label, pat in PATTERNS:
                for m in pat.finditer(text):
                    secret = m.group(m.lastindex) if m.lastindex else m.group(0)
                    if PLACEHOLDER.search(secret):
                        continue
                    hits += 1
                    if hits <= 12:
                        print(f"HIT {label}: {info.filename}")

    must = [
        "TGSEC-Qtzuu-clean-20261105/00-发布说明.md",
        "TGSEC-Qtzuu-clean-20261105/ROUTING.md",
        "TGSEC-Qtzuu-clean-20261105/domains/INGEST-20261105-ARTEX.md",
        "TGSEC-Qtzuu-clean-20261105/tools/ledger/ledger.py",
        "TGSEC-Qtzuu-clean-20261105/tools/ledger/guard.rules.json",
        "TGSEC-Qtzuu-clean-20261105/domains/redteam-framework/engagement-ledger-v2/SKILL.md",
        "TGSEC-Qtzuu-clean-20261105/domains/ai-infra-security/context-compaction-budget/SKILL.md",
    ]
    missing = [m for m in must if m not in set(names)]
    print("----")
    print(f"entries          : {len(names)}")
    print(f"text scanned     : {scanned}")
    print(f"secret hits      : {hits}")
    print(f"banned paths     : {len(banned)}")
    for b in banned[:10]:
        print("   " + b)
    print(f"key files present: {len(must) - len(missing)}/{len(must)}")
    for m in missing:
        print("   MISSING " + m)
    ok = hits == 0 and not banned and not missing
    print("VERDICT " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
