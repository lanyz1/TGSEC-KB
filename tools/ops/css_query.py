#!/usr/bin/env python3
"""css_query.py — CyberSecurity-Skills 本地入口（TGSEC ops 层）

上游数据：docs/learning/cybersecurity-skills（MIT，见同目录 SOURCE.md）
本脚本只做命令适配，查询逻辑仍由上游 skill_query.py 执行。

兼容卡面命令：
  css_query.py list-modules
  css_query.py list-skills --module 30
  css_query.py search --keyword 无线
  css_query.py get --id 05-002
  css_query.py doctor
  css_query.py resolve --module 3 --skill SQL注入
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = [
    ROOT / "docs/learning/cybersecurity-skills",
    Path("/root/docs/learning/cybersecurity-skills"),
    Path("/root/.hermes/docs/learning/cybersecurity-skills"),
]

ALIASES = {
    "get": "get-skill",
    "get-skill": "get-skill",
    "doctor": "validate",
    "validate": "validate",
    "list": "list-modules",
    "list-modules": "list-modules",
    "list-skills": "list-skills",
    "search": "search",
    "resolve": "resolve",
}


def data_root() -> Path:
    for candidate in CANDIDATES:
        if (candidate / "skill_query.py").is_file() and (candidate / "index.json").is_file():
            return candidate
    checked = ", ".join(str(p) for p in CANDIDATES)
    raise SystemExit(
        "css_query: 数据源缺失（docs/learning/cybersecurity-skills）。\n"
        f"已检查: {checked}\n"
        "恢复: 按 SOURCE.md 重新导入 hi-fullhouse/cybersecurity-skills。"
    )


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print((__doc__ or "").strip())
        return 0

    command = sys.argv[1]
    if command not in ALIASES:
        print(f"css_query: 未知命令 {command!r}", file=sys.stderr)
        print("可用: list-modules, list-skills, search, get, doctor, resolve", file=sys.stderr)
        return 2

    data = data_root()
    upstream = data / "skill_query.py"
    mapped = ALIASES[command]
    argv = [sys.executable, str(upstream), mapped, *sys.argv[2:]]

    if command == "doctor":
        print(f"[css_query] data={data}")
        print(f"[css_query] index={data / 'index.json'}")
        print(f"[css_query] upstream={upstream}")

    os.execv(sys.executable, argv)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
