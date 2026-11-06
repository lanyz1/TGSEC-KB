#!/usr/bin/env python3
"""Callability gate: files in tools/ops must be runnable, not just present.

Status:
  ready   - compiles and entry `--help` exits 0/2
  library - compiles, but is a shared helper with no runnable entrypoint
  manual  - compiles, entry exists but `--help` does not answer cleanly
  broken  - syntax error, import/startup failure, or `--help` crash/timeout

Only `--help` is run; business arguments are never supplied. Adapter shims are
resolved to their target script (external tools first, then tools/ops).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

OPS = Path(__file__).resolve().parent
ROOT = OPS.parent.parent
SKIP = {Path(__file__).name}
EXT = ROOT / ".claude/skills/pentest-redteam/scripts/tools"


def adapter_target(source: str, name: str) -> str | None:
    """Return the script this compatibility entry forwards to, if any."""
    m = re.search(r'run\("([^"]+\.py)"\)', source)
    if m:
        return m.group(1)
    if name != "_adapter.py" and "Path(sys.argv[0]).name" in source and "def run(target_name)" in source:
        return name
    return None


def check(path: Path, timeout: int) -> dict:
    name = path.name
    try:
        source = path.read_text(errors="ignore")
    except OSError as exc:
        return {"name": name, "status": "broken", "reason": f"read: {exc}"}
    try:
        compile(source, str(path), "exec")
    except SyntaxError as exc:
        return {"name": name, "status": "broken", "reason": f"syntax: {exc}"}

    has_argparse = "argparse" in source
    has_main = "__main__" in source
    target_name = adapter_target(source, name)
    if target_name:
        target = EXT / target_name
        if not target.exists():
            target = OPS / target_name
        if not target.exists():
            return {"name": name, "status": "broken", "reason": f"adapter target missing: {target_name}"}
        if target.resolve() == path.resolve():
            return {"name": name, "status": "broken", "reason": f"adapter self-loop: {target_name}"}
        try:
            proc = subprocess.run(
                [sys.executable, str(path), "--help"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"name": name, "status": "broken", "reason": f"adapter --help timeout>{timeout}s"}
        except OSError as exc:
            return {"name": name, "status": "broken", "reason": f"adapter exec: {exc}"}
        if proc.returncode in (0, 2):
            return {"name": name, "status": "ready", "reason": f"adapter -> {target_name} --help rc={proc.returncode}"}
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        return {"name": name, "status": "broken", "reason": f"adapter -> {target_name} rc={proc.returncode}: {tail[-1][:160] if tail else ''}"}
    if not (has_argparse and has_main):
        if name == "_adapter.py":
            return {"name": name, "status": "library", "reason": "shared adapter helper"}
        if not has_main and "os.execv" not in source:
            return {"name": name, "status": "library", "reason": "library helper (no __main__)"}
        try:
            proc = subprocess.run(
                [sys.executable, str(path), "--help"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"name": name, "status": "manual", "reason": f"non-uniform CLI; --help timeout>{timeout}s"}
        if proc.returncode in (0, 2):
            return {"name": name, "status": "ready", "reason": f"manual --help rc={proc.returncode}"}
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        return {"name": name, "status": "manual", "reason": f"non-uniform CLI; --help rc={proc.returncode}: {tail[-1][:160] if tail else ''}"}

    try:
        proc = subprocess.run(
            [sys.executable, str(path), "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "broken", "reason": f"--help timeout>{timeout}s"}
    except OSError as exc:
        return {"name": name, "status": "broken", "reason": f"exec: {exc}"}
    if proc.returncode not in (0, 2):
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        return {
            "name": name,
            "status": "broken",
            "reason": f"--help rc={proc.returncode}: {tail[-1][:160] if tail else ''}",
        }
    return {"name": name, "status": "ready", "reason": "--help rc=%d" % proc.returncode}


def scan(timeout: int = 5) -> dict:
    rows = [check(p, timeout) for p in sorted(OPS.glob("*.py")) if p.name not in SKIP]
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("ready", "library", "manual", "broken")}
    return {"total": len(rows), "counts": counts, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description="tools/ops 可调用性门禁（只跑 --help）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="存在 broken 时 exit 1")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=5)
    args = ap.parse_args()
    result = scan(args.timeout)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        c = result["counts"]
        print(f"total={result['total']} ready={c['ready']} library={c['library']} manual={c['manual']} broken={c['broken']}")
        for status in ("broken", "manual", "library"):
            bad = [r for r in result["rows"] if r["status"] == status]
            if bad:
                print(f"top {status}:")
                for r in bad[: args.top]:
                    print(f"  {r['name']}: {r['reason']}")
    return 1 if args.strict and result["counts"]["broken"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
