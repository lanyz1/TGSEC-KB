#!/usr/bin/env python3
"""Reverse-engineering route helper: hint/file → matching local skills."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

KIND = {
    ".apk": "apk-recon / mobile-app-pentest",
    ".ipa": "apk-recon / ios-harvest-chain-recon",
    ".js": "js-reverse / spa-protocol-reverse",
    ".so": "flutter-reverse / dart-flutter-reverse",
    ".elf": "reverse-engineering",
    ".exe": "reverse-engineering",
    ".dll": "reverse-engineering",
    ".jar": "java-jar-protection-bypass",
    ".wasm": "wasm-ws-protocol-crack / js-reverse",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="逆向路由：文件类型/提示 → 技能与工具")
    ap.add_argument("--hint", "-H", help="自然语言提示，如 'K8s' 或 'flutter libapp.so'")
    ap.add_argument("--file", "-f", help="sample path, infer by extension")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()
    if not args.hint and not args.file:
        ap.error("need --hint or --file")

    if args.file:
        ext = Path(args.file).suffix.lower()
        print(f"[reverse] file={args.file} ext={ext or '(none)'}")
        if ext in KIND:
            print(f"suggest: {KIND[ext]}")
        else:
            print("suggest: reverse-engineering (run `file`/`binwalk` first)")

    query = args.hint or Path(args.file).suffix.lstrip(".") or "reverse"
    p = subprocess.run(["/usr/local/bin/skill_find", query, "--top", str(args.top)],
                       capture_output=True, text=True)
    print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, file=sys.stderr, end="")
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
