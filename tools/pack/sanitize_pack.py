#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布前脱敏扫描：找出高置信凭据并从文本文件里就地抹掉。

用法: python sanitize_pack.py <pack-root> [--dry-run]
退出码: 0 = 干净（或已脱敏），1 = 仍残留
"""
from __future__ import annotations

import argparse
import os
import re
import sys

TEXT_EXT = {
    ".md", ".markdown", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".py", ".ps1", ".psm1",
    ".sh", ".bash", ".cmd", ".bat", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rb",
    ".php", ".java", ".cs", ".c", ".h", ".cpp", ".rs", ".sql", ".conf", ".config", ".ini", ".toml",
    ".xml", ".html", ".htm", ".css", ".csv", ".env", ".rules", ".lua", ".pl", ".m", ".mjs",
}
SKIP_DIR = {".git", "node_modules", "__pycache__"}

# 形似占位符的串不抹：文档里的示例比真凭据多
PLACEHOLDER = re.compile(
    r"(xxx|XXX|\*\*\*|your|YOUR|example|EXAMPLE|placeholder|redacted|REDACTED|"
    r"1234567890|abcdef|0{8,}|<[^>]*>|\$\{|\.\.\.)", re.I
)

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-ak", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws-ak-id", re.compile(r"\bAKID[0-9A-Za-z]{16,40}\b")),
    ("aliyun-ltaI", re.compile(r"\bLTAI[0-9A-Za-z]{12,24}\b")),
    ("openai-sk", re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b")),
    ("openai-sk-proj", re.compile(r"\bsk-proj-[A-Za-z0-9_-]{24,}\b")),
    ("anthropic-sk", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("github-pat", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("telegram-bot", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{30,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("bearer", re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{24,})")),
    ("set-cookie", re.compile(r"(?i)\bset-cookie:[^\n]{0,80}?(?:session|token|sid|auth)[A-Za-z0-9_.-]*=([A-Za-z0-9%._~-]{20,})")),
    ("generic-secret", re.compile(
        r"(?i)\b(api[_-]?key|apikey|secret[_-]?key|access[_-]?key|client[_-]?secret|"
        r"auth[_-]?token|password|passwd|pwd)\b\s*[:=]\s*[\"']?([A-Za-z0-9/+=._-]{20,})[\"']?")),
    ("ssk", re.compile(r"\bssk_[A-Za-z0-9]{12,}\b")),
]

SUSPECT_NAME = re.compile(r"(aksk|credential|secrets?\.)", re.I)
DROP_SECRET_EXT = {".pem", ".key", ".crt", ".cer", ".p12", ".pfx", ".jks", ".keystore", ".kdbx", ".ppk"}
DROP_SECRET_NAME = re.compile(r"(?i)^(\.env(\..*)?|id_rsa.*|.*\.env|aksk.*|.*credentials?\.(txt|json|ya?ml|csv|ini))$")


def is_text(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    if ext in TEXT_EXT:
        return True
    if ext:
        return False
    try:
        with open(path, "rb") as fh:
            head = fh.read(4096)
        return b"\x00" not in head
    except OSError:
        return False


def scan_text(text: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for name, pat in PATTERNS:
        for m in pat.finditer(text):
            secret = m.group(m.lastindex) if m.lastindex else m.group(0)
            if PLACEHOLDER.search(secret):
                continue
            hits.append((name, secret))
    return hits


def redact(text: str) -> tuple[str, int]:
    total = 0
    for name, pat in PATTERNS:
        def repl(m: re.Match[str]) -> str:
            nonlocal total
            if m.lastindex:
                secret = m.group(m.lastindex)
                if PLACEHOLDER.search(secret):
                    return m.group(0)
                total += 1
                return m.group(0).replace(secret, "<REDACTED>")
            if PLACEHOLDER.search(m.group(0)):
                return m.group(0)
            total += 1
            return "<REDACTED>"
        text = pat.sub(repl, text)
    return text, total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        raise SystemExit(f"目录不存在: {root}")

    dropped = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        for name in list(filenames):
            path = os.path.join(dirpath, name)
            ext = os.path.splitext(name)[1].lower()
            if ext in DROP_SECRET_EXT or DROP_SECRET_NAME.match(name):
                try:
                    os.remove(path)
                    dropped += 1
                except OSError:
                    pass
    if dropped:
        print(f"dropped secret-shaped files: {dropped}")

    files = 0
    hit_files = 0
    hits_total = 0
    redacted_total = 0
    suspects: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if SUSPECT_NAME.search(rel) and os.path.getsize(path) < 4 * 1024 * 1024:
                suspects.append(rel)
            if not is_text(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            files += 1
            hits = scan_text(text)
            if not hits:
                continue
            hit_files += 1
            hits_total += len(hits)
            print(f"{rel}: " + ", ".join(f"{n}({len(s)})" for n, s in hits[:6]))
            if args.dry_run:
                continue
            new_text, n = redact(text)
            if n:
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new_text)
                redacted_total += n

    print("----")
    print(f"text files scanned : {files}")
    print(f"files with hits    : {hit_files}")
    print(f"secret matches     : {hits_total}")
    print(f"redacted           : {redacted_total}")
    if suspects:
        print("name-suspicious (人工复核，未自动处理):")
        for s in suspects[:40]:
            print("  " + s)
    if args.dry_run:
        return 0
    residual = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        for name in filenames:
            path = os.path.join(dirpath, name)
            if not is_text(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    if scan_text(fh.read()):
                        residual += 1
            except OSError:
                continue
    print(f"residual files     : {residual}")
    return 0 if residual == 0 else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
