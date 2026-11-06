#!/usr/bin/env python3
"""Static CI/CD surface probe: scan a repository for risky pipeline patterns.

Usage:
  cicd_surface_probe.py drive --path <repo> [--case <case>] [--json]

Read-only. It highlights workflow injection, excessive permissions, unpinned
actions, self-hosted runners, secret exposure and dangerous curl|sh patterns.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".venv", "venv", "__pycache__", ".tox"}
WORKFLOW_NAMES = {
    ".gitlab-ci.yml", ".gitlab-ci.yaml", "jenkinsfile", "azure-pipelines.yml", "azure-pipelines.yaml",
    ".drone.yml", "bitbucket-pipelines.yml", "buildkite.yml", ".buildkite.yml", "cloudbuild.yaml",
    "cloudbuild.yml", "appveyor.yml", "appveyor.yaml", ".cirrus.yml",
}
CI_PATHS = (".github/workflows", ".circleci", ".buildkite", "ci", ".ci", "argo", "argocd")

RULES = [
    ("HIGH", re.compile(r"pull_request_target", re.I), "pull_request_target checkout of untrusted code"),
    ("HIGH", re.compile(r"workflow_run", re.I), "workflow_run chaining can expose secrets"),
    ("HIGH", re.compile(r"permissions\s*:\s*write-all", re.I), "workflow permissions: write-all"),
    ("HIGH", re.compile(r"curl[^\n|]*\|\s*(?:ba)?sh", re.I), "remote script piped to shell"),
    ("HIGH", re.compile(r"/var/run/docker\.sock", re.I), "docker socket mounted"),
    ("MED", re.compile(r"self-hosted", re.I), "self-hosted runner"),
    ("MED", re.compile(r"ACTIONS_ALLOW_UNSECURE_COMMANDS", re.I), "unsecure commands enabled"),
    ("MED", re.compile(r"secrets\.[A-Za-z0-9_]+", re.I), "secret reference"),
    ("MED", re.compile(r"\$\{\{\s*github\.event\.[^}]*\}\}", re.I), "event data in expression"),
    ("MED", re.compile(r"echo[^\n]*\$\{\{\s*secrets\.", re.I), "secret echoed in run step"),
    ("LOW", re.compile(r"uses\s*:\s*[^\s@]+(?:\s|$)", re.I), "action without version pin"),
    ("LOW", re.compile(r"git\s+push[^\n]*--force", re.I), "force push in pipeline"),
]


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".cache")]
        for name in filenames:
            yield Path(dirpath) / name


def is_ci_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    if path.name.lower() in WORKFLOW_NAMES:
        return True
    return any(rel.startswith(p.lower().strip("/") + "/") or rel == p.lower() for p in CI_PATHS)


def scan(root: Path) -> dict:
    findings = []
    files = []
    for path in iter_files(root):
        if not is_ci_file(path, root):
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        files.append(rel)
        for lineno, line in enumerate(text.splitlines(), 1):
            for severity, regex, message in RULES:
                if regex.search(line):
                    findings.append({
                        "severity": severity,
                        "file": rel,
                        "line": lineno,
                        "rule": message,
                        "evidence": line.strip()[:240],
                    })
    # de-duplicate same file/line/rule
    seen = set()
    unique = []
    for item in findings:
        key = (item["file"], item["line"], item["rule"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    unique.sort(key=lambda x: ({"HIGH": 0, "MED": 1, "LOW": 2}[x["severity"]], x["file"], x["line"]))
    return {
        "mode": "cicd",
        "root": str(root),
        "workflow_files": files,
        "findings": unique,
        "summary": {
            "files": len(files),
            "high": sum(1 for x in unique if x["severity"] == "HIGH"),
            "medium": sum(1 for x in unique if x["severity"] == "MED"),
            "low": sum(1 for x in unique if x["severity"] == "LOW"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Static CI/CD workflow surface probe")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("drive")
    p.add_argument("--path", required=True)
    p.add_argument("--case")
    p.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"cicd_surface_probe: not a directory: {root}", file=sys.stderr)
        return 2
    result = scan(root=root)
    if args.case:
        out = Path("/root/cases") / args.case / "artifacts"
        out.mkdir(parents=True, exist_ok=True)
        target = out / "cicd_surface_probe.json"
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result["artifact"] = str(target)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"root={root} workflow_files={result['summary']['files']} "
          f"high={result['summary']['high']} medium={result['summary']['medium']} low={result['summary']['low']}")
    for item in result["findings"][:50]:
        print(f"[{item['severity']}] {item['file']}:{item['line']} {item['rule']} | {item['evidence'][:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
