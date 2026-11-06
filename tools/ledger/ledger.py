#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TGSEC engagement ledger v2 — 单事件流账本 + 证据版本挡板 + 收官判据。

设计三条硬线（借鉴自自主渗透框架的机制，落地为本机 JSONL）：
1. 单一真相源：一个 case 目录下的 ledger.jsonl 追加事件，不做双写派生文件。
2. 证据四角色 + 内容寻址：证据落 evidence/blobs/<sha256>.bin，绑定记 role/note/序；
   evidence_version = 该 finding 的绑定条数，报告须写明自己写的版本号。
3. 收官判据脚本化：goals 全 met/dropped、无 open intent、每条 finding 有 proof 证据、
   报告版本 == 当前证据版本，缺一条就 exit 1。

用法见 `ledger.py --help` 或同目录 README。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from typing import Any
from urllib.parse import urlsplit

LEDGER = "ledger.jsonl"
BLOBS = os.path.join("evidence", "blobs")
ROLES = ("baseline", "proof", "verification", "supporting")
KINDS = ("domain", "subdomain", "ip", "port", "endpoint", "app", "other")
RESULTS = ("ok", "blocked", "error")


# ---------------------------------------------------------------- 基础设施
def case_dir(path: str) -> str:
    d = os.path.abspath(path)
    if not os.path.isdir(d):
        raise SystemExit(f"case 目录不存在: {d}")
    return d


def ledger_path(case: str) -> str:
    return os.path.join(case, LEDGER)


def append(case: str, event: dict[str, Any]) -> dict[str, Any]:
    event = {"ts": int(time.time() * 1000), **event}
    with open(ledger_path(case), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def events(case: str) -> list[dict[str, Any]]:
    path = ledger_path(case)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{lineno} 不是合法 JSON: {exc}")
    return out


def sha256_file(path: str) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def next_id(evts: list[dict[str, Any]], prefix: str, type_: str) -> str:
    n = sum(1 for e in evts if e.get("type") == type_)
    return f"{prefix}{n + 1}"


# ---------------------------------------------------------------- 状态派生
def derive(case: str) -> dict[str, Any]:
    evts = events(case)
    left = [e["id"] for e in evts if e.get("type") == "seq.reserve"]  # 兼容占位，正常为空
    del left

    goals: dict[str, dict[str, Any]] = {}
    hyps: dict[str, dict[str, Any]] = {}
    findings: dict[str, dict[str, Any]] = {}
    intents: dict[str, dict[str, Any]] = {}
    targets: dict[str, str] = {}
    tested: set[str] = set()
    binds: dict[str, list[dict[str, Any]]] = {}
    reports: dict[str, dict[str, Any]] = {}
    tools: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []

    for e in evts:
        t = e.get("type")
        if t == "goal.add":
            goals[e["id"]] = {**e, "status": "open", "note": "", "by": ""}
        elif t == "goal.met":
            if e["id"] in goals:
                goals[e["id"]]["status"] = "met"
                goals[e["id"]]["note"] = e.get("note", "")
                goals[e["id"]]["by"] = e.get("by", "")
        elif t == "goal.drop":
            if e["id"] in goals:
                goals[e["id"]]["status"] = "dropped"
                goals[e["id"]]["note"] = e.get("reason", "")
        elif t == "hyp.open":
            hyps[e["id"]] = {**e, "verdict": "open"}
        elif t == "hyp.verdict":
            if e["id"] in hyps:
                hyps[e["id"]]["verdict"] = e.get("verdict", "open")
                hyps[e["id"]]["verdict_note"] = e.get("note", "")
        elif t == "finding.add":
            findings[e["id"]] = {**e}
            binds.setdefault(e["id"], [])
        elif t == "evidence.bind":
            binds.setdefault(e["finding"], []).append(e)
        elif t == "report.write":
            reports[e["finding"]] = e
        elif t == "intent.open":
            intents[e["id"]] = {**e, "closed": False}
        elif t == "intent.close":
            if e["id"] in intents:
                intents[e["id"]]["closed"] = True
                intents[e["id"]]["outcome"] = e.get("outcome", "")
        elif t == "target.add":
            targets[e["value"]] = e.get("kind", "other")
        elif t == "tested":
            tested.add(e["target"])
        elif t == "tool":
            tools.append(e)
        elif t == "audit":
            audit.append(e)

    for fid, rows in binds.items():
        for order, row in enumerate(rows, 1):
            row["order"] = order
    return {
        "goals": goals,
        "hyps": hyps,
        "findings": findings,
        "intents": intents,
        "targets": targets,
        "tested": tested,
        "binds": binds,
        "reports": reports,
        "tools": tools,
        "audit": audit,
    }


def evidence_version(state: dict[str, Any], finding: str) -> int:
    return len(state["binds"].get(finding, []))


# ---------------------------------------------------------------- verify
def verify(case: str) -> dict[str, Any]:
    st = derive(case)
    errors: list[str] = []
    warnings: list[str] = []

    for gid, g in st["goals"].items():
        if g["status"] == "open":
            errors.append(f"goal {gid} 未收官（open）：{g.get('text', '')[:60]}")

    for iid, it in st["intents"].items():
        if not it["closed"]:
            errors.append(f"intent {iid} 未结算（open）：{it.get('text', '')[:60]}")

    blobdir = os.path.join(case, BLOBS)
    for fid, f in st["findings"].items():
        rows = st["binds"].get(fid, [])
        if not rows:
            errors.append(f"finding {fid} 没有任何证据绑定：{f.get('title', '')[:50]}")
            continue
        if not any(r.get("role") == "proof" for r in rows):
            errors.append(f"finding {fid} 缺 role=proof 证据（当前 roles={[r.get('role') for r in rows]}）")
        for r in rows:
            sha = r.get("sha256", "")
            blob = os.path.join(blobdir, f"{sha}.bin")
            if not sha or not os.path.exists(blob):
                errors.append(f"finding {fid} 的证据 blob 缺失：{sha or '(no sha)'}")

    for fid, rep in st["reports"].items():
        want = evidence_version(st, fid)
        got = int(rep.get("evidence_version", -1))
        if got != want:
            errors.append(f"finding {fid} 报告版本 {got} != 当前证据版本 {want}（报告待更新）")

    for fid in st["findings"]:
        if fid not in st["reports"]:
            warnings.append(f"finding {fid} 尚未出报告")

    if not st["findings"]:
        warnings.append("账本里还没有 finding")

    open_goals = [g for g in st["goals"].values() if g["status"] == "open"]
    stats = {
        "goals": len(st["goals"]),
        "goals_open": len(open_goals),
        "hyps": len(st["hyps"]),
        "hyps_open": sum(1 for h in st["hyps"].values() if h["verdict"] == "open"),
        "findings": len(st["findings"]),
        "intents_open": sum(1 for i in st["intents"].values() if not i["closed"]),
        "targets": len(st["targets"]),
        "tested": len(st["tested"]),
    }
    return {"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats}


# ---------------------------------------------------------------- coverage
def coverage(case: str) -> dict[str, Any]:
    st = derive(case)
    buckets: dict[str, dict[str, int]] = {}
    for value, kind in st["targets"].items():
        b = buckets.setdefault(kind if kind in KINDS else "other", {"total": 0, "tested": 0})
        b["total"] += 1
        if value in st["tested"]:
            b["tested"] += 1
    total = sum(b["total"] for b in buckets.values())
    done = sum(b["tested"] for b in buckets.values())
    return {
        "total": total,
        "tested": done,
        "percent": round(done * 100.0 / total, 1) if total else 0.0,
        "buckets": dict(sorted(buckets.items(), key=lambda kv: kv[1]["total"], reverse=True)),
        "untested": sorted(t for t in st["targets"] if t not in st["tested"]),
    }


# ---------------------------------------------------------------- attribution
def attribution(case: str) -> dict[str, Any]:
    st = derive(case)
    groups: dict[str, dict[str, Any]] = {}
    streak: dict[str, int] = {}
    tripped: list[dict[str, Any]] = []
    for e in st["tools"]:
        key = f"{e.get('tool', '?')}:{e.get('action', 'run')}"
        g = groups.setdefault(key, {"ok": 0, "blocked": 0, "error": 0, "total": 0, "last_reason": ""})
        result = e.get("result", "error")
        if result not in RESULTS:
            result = "error"
        g[result] += 1
        g["total"] += 1
        g["last_reason"] = e.get("reason", g["last_reason"])
        if result == "error":
            streak[key] = streak.get(key, 0) + 1
            if streak[key] >= 3 and not any(x["key"] == key for x in tripped):
                tripped.append({"key": key, "consecutive_errors": streak[key], "reason": g["last_reason"]})
        else:
            streak[key] = 0
    return {"groups": groups, "tripped": tripped}


# ---------------------------------------------------------------- guard
def load_rules(rules_path: str) -> list[dict[str, Any]]:
    with open(rules_path, encoding="utf-8") as fh:
        data = json.load(fh)
    rules = data.get("rules", data if isinstance(data, list) else [])
    rules = [r for r in rules if r.get("enabled", True)]
    return sorted(rules, key=lambda r: int(r.get("priority", 0)), reverse=True)


def evaluate(command: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
    for rule in rules:  # priority DESC + 首命中短路
        pattern = rule.get("pattern", "")
        if not pattern:
            continue
        try:
            hit = re.search(pattern, command, re.IGNORECASE | re.MULTILINE)
        except re.error as exc:
            print(f"[guard] 规则 {rule.get('id')} 正则无效，跳过：{exc}", file=sys.stderr)
            continue
        if hit:
            return {
                "action": rule.get("action", "ask"),
                "rule": rule.get("id", ""),
                "reason": rule.get("reason", ""),
                "matched": hit.group(0)[:200],
            }
    return {"action": "allow", "rule": "", "reason": "no rule matched", "matched": ""}


# ---------------------------------------------------------------- 目标分类与导入
IPV4 = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
CIDR = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}$")
HOST = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,62})?\.)+[A-Za-z]{2,63}$")
HOSTPORT = re.compile(r"^(?:[A-Za-z0-9_.-]+|\[[0-9A-Fa-f:]+\]):\d{1,5}$")
URL_TOKEN = re.compile(r"https?://[^\s\"'<>)\]},]+")
PATH_TOKEN = re.compile(r"/[A-Za-z0-9_\-.{}$:]*[A-Za-z0-9_\-.{}$](?:[A-Za-z0-9_\-./{}$:]*)?")
HOST_TOKEN = re.compile(r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61})\.)+[A-Za-z]{2,63}\b")
METHOD_PATH = re.compile(r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+)", re.IGNORECASE)
MAX_IMPORT = 20000


def classify(value: str) -> str | None:
    """把一个字符串判成 target 类型；判不出来返回 None。"""
    v = (value or "").strip().strip("\"'`,;")
    if not v or len(v) > 2048:
        return None
    if CIDR.match(v) or IPV4.match(v):
        return "ip"
    if v.startswith(("http://", "https://")):
        parts = urlsplit(v)
        path = parts.path or "/"
        host = parts.netloc.split("@")[-1]
        if path in ("", "/"):
            return "subdomain" if host.count(".") >= 2 else "domain"
        return "endpoint"
    if v.startswith("/"):
        return "endpoint" if len(v) > 1 else None
    if HOSTPORT.match(v):
        return "port"
    if HOST.match(v):
        return "domain" if v.count(".") == 1 else "subdomain"
    if v.endswith((".apk", ".ipa")) or v.startswith("bundle:"):
        return "app"
    return None


def extract_values(path: str) -> list[str]:
    """从一个侦察产物里抽候选目标：txt 逐行、json 走字符串树。"""
    out: list[str] = []
    if path.lower().endswith((".json", ".jsonl")):
        try:
            with open(path, encoding="utf-8-sig") as fh:
                if path.lower().endswith(".jsonl"):
                    docs = [json.loads(line) for line in fh if line.strip()]
                else:
                    docs = [json.load(fh)]
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[import] 跳过 {path}: {exc}", file=sys.stderr)
            return out

        def walk(node: Any) -> None:
            if len(out) >= MAX_IMPORT:
                return
            if isinstance(node, str):
                for m in URL_TOKEN.finditer(node):
                    out.append(m.group(0))
                for m in PATH_TOKEN.finditer(node):
                    out.append(m.group(0))
                if HOST.match(node.strip()):
                    out.append(node.strip())
            elif isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        for doc in docs:
            walk(doc)
        return out

    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            for raw in fh:
                if len(out) >= MAX_IMPORT:
                    break
                line = raw.strip()
                if not line or line.startswith(("#", "//", ";", "<!--")):
                    continue
                m = METHOD_PATH.match(line)
                if m:
                    out.append(m.group(2))
                    continue
                for token in re.split(r"[\s,;|]+", line):
                    if not token:
                        continue
                    out.append(token)
    except OSError as exc:
        print(f"[import] 跳过 {path}: {exc}", file=sys.stderr)
    return out


def collect_sources(targets: list[str]) -> list[str]:
    files: list[str] = []
    for item in targets:
        p = os.path.abspath(item)
        if os.path.isdir(p):
            for name in ("targets.txt", "api_static.txt", "routes.txt", "site_map.json",
                         "param_candidates.json", "params_merged.json"):
                cand = os.path.join(p, name)
                if os.path.exists(cand):
                    files.append(cand)
        elif os.path.exists(p):
            files.append(p)
        else:
            print(f"[import] 路径不存在，跳过: {item}", file=sys.stderr)
    return files


# ---------------------------------------------------------------- 命令
def cmd_init(a: argparse.Namespace) -> int:
    d = os.path.abspath(a.case)
    os.makedirs(os.path.join(d, BLOBS), exist_ok=True)
    path = os.path.join(d, LEDGER)
    if not os.path.exists(path):
        open(path, "w", encoding="utf-8").close()
    targets = os.path.join(d, "targets.txt")
    if a.targets and not os.path.exists(targets):
        shutil.copyfile(a.targets, targets)
    print(json.dumps({"case": d, "ledger": path, "ok": True}, ensure_ascii=False))
    return 0


def cmd_goal(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    evts = events(case)
    if a.action == "add":
        gid = next_id(evts, "G", "goal.add")
        append(case, {"type": "goal.add", "id": gid, "text": a.text, "parent": a.parent or ""})
        print(f"{gid}\t{a.text}")
    elif a.action == "met":
        append(case, {"type": "goal.met", "id": a.id, "note": a.note or "", "by": a.by or ""})
        print(f"{a.id}\tmet")
    elif a.action == "drop":
        append(case, {"type": "goal.drop", "id": a.id, "reason": a.reason or ""})
        print(f"{a.id}\tdropped")
    elif a.action == "list":
        st = derive(case)
        for gid, g in st["goals"].items():
            print(f"{gid}\t{g['status']}\t{g.get('text', '')}\t{g.get('note', '')}")
    return 0


def cmd_hyp(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    evts = events(case)
    if a.action == "open":
        hid = next_id(evts, "H", "hyp.open")
        append(case, {"type": "hyp.open", "id": hid, "text": a.text, "signal": a.signal or ""})
        print(f"{hid}\t{a.text}")
    elif a.action == "verdict":
        verdict = a.verdict or a.value
        if verdict not in ("confirmed", "refuted", "inconclusive"):
            raise SystemExit("verdict 取值：confirmed | refuted | inconclusive")
        append(case, {"type": "hyp.verdict", "id": a.id, "verdict": verdict, "note": a.note or ""})
        print(f"{a.id}\t{verdict}")
    elif a.action == "list":
        st = derive(case)
        for hid, h in st["hyps"].items():
            print(f"{hid}\t{h['verdict']}\t{h.get('text', '')}")
    return 0


def cmd_finding(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    evts = events(case)
    fid = next_id(evts, "F", "finding.add")
    append(
        case,
        {
            "type": "finding.add",
            "id": fid,
            "title": a.title,
            "severity": a.severity,
            "endpoint": a.endpoint or "",
            "hyp": a.hyp or "",
        },
    )
    print(f"{fid}\t{a.severity}\t{a.title}")
    return 0


def cmd_evidence(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    if a.action != "bind":
        raise SystemExit("evidence 只支持 bind")
    if a.role not in ROLES:
        raise SystemExit(f"role 取值：{' | '.join(ROLES)}")
    src = os.path.abspath(a.file)
    if not os.path.exists(src):
        raise SystemExit(f"证据文件不存在: {src}")
    sha, size = sha256_file(src)
    blob = os.path.join(case, BLOBS, f"{sha}.bin")
    if not os.path.exists(blob):
        shutil.copyfile(src, blob)
    append(
        case,
        {
            "type": "evidence.bind",
            "finding": a.finding,
            "role": a.role,
            "note": a.note or "",
            "cmd": a.cmd or "",
            "file": os.path.basename(src),
            "sha256": sha,
            "size": size,
        },
    )
    st = derive(case)
    print(f"{a.finding}\t{a.role}\tsha256={sha}\tsize={size}\tversion={evidence_version(st, a.finding)}")
    return 0


def cmd_report(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    st = derive(case)
    if a.finding not in st["findings"]:
        raise SystemExit(f"finding 不存在: {a.finding}")
    want = evidence_version(st, a.finding)
    append(
        case,
        {
            "type": "report.write",
            "finding": a.finding,
            "path": a.path or "",
            "evidence_version": want,
            "note": a.note or "",
        },
    )
    print(f"{a.finding}\treport@v{want}\t{a.path or ''}")
    return 0


def cmd_target(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    if a.action == "add":
        if a.kind not in KINDS:
            raise SystemExit(f"kind 取值：{' | '.join(KINDS)}")
        append(case, {"type": "target.add", "value": a.value, "kind": a.kind})
        print(f"target\t{a.kind}\t{a.value}")
        return 0

    if a.action == "list":
        cov = coverage(case)
        for value, kind in sorted(derive(case)["targets"].items()):
            mark = "tested" if value in derive(case)["tested"] else "-"
            print(f"{kind:<10}\t{mark:<7}\t{value}")
        print(f"TOTAL {cov['total']}  tested {cov['tested']}  {cov['percent']}%")
        return 0

    if a.action != "import":
        raise SystemExit("target 只支持 add / import / list")

    sources = collect_sources(a.sources or [])
    if not sources:
        raise SystemExit("没有可导入的产物文件（targets.txt / api_static.txt / routes.txt / site_map.json …）")
    known = derive(case)["targets"]
    fresh: dict[str, str] = {}
    per_file: list[tuple[str, int, int]] = []
    for path in sources:
        before = len(fresh)
        for value in extract_values(path):
            kind = classify(value)
            if kind is None:
                continue
            key = value.strip().rstrip("/") or value.strip()
            if key in known or key in fresh:
                continue
            fresh[key] = kind
            if len(fresh) >= MAX_IMPORT:
                break
        per_file.append((os.path.basename(path), len(fresh) - before, 0))

    if a.dry_run:
        for name, added, _ in per_file:
            print(f"DRY\t{name}\t+{added}")
        buckets: dict[str, int] = {}
        for kind in fresh.values():
            buckets[kind] = buckets.get(kind, 0) + 1
        print("DRY total +%d %s" % (len(fresh), buckets))
        return 0

    for value, kind in fresh.items():
        append(case, {"type": "target.add", "value": value, "kind": kind})
    for name, added, _ in per_file:
        print(f"import\t{name}\t+{added}")
    buckets = {}
    for kind in fresh.values():
        buckets[kind] = buckets.get(kind, 0) + 1
    cov = coverage(case)
    print(f"IMPORTED +{len(fresh)} {buckets} → 分母 {cov['total']}（{cov['percent']}% 已测）")
    return 0


def cmd_tested(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    append(case, {"type": "tested", "target": a.target, "finding": a.finding or ""})
    st = derive(case)
    cov = coverage(case)
    print(f"tested\t{a.target}\t{cov['tested']}/{cov['total']} = {cov['percent']}%")
    return 0


def cmd_intent(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    evts = events(case)
    if a.action == "open":
        iid = next_id(evts, "I", "intent.open")
        append(case, {"type": "intent.open", "id": iid, "text": a.text})
        print(f"{iid}\t{a.text}")
    else:
        append(case, {"type": "intent.close", "id": a.id, "outcome": a.outcome or ""})
        print(f"{a.id}\tclosed\t{a.outcome or ''}")
    return 0


def cmd_tool(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    if a.result not in RESULTS:
        raise SystemExit(f"result 取值：{' | '.join(RESULTS)}")
    append(
        case,
        {
            "type": "tool",
            "tool": a.tool,
            "action": a.action_name or "run",
            "result": a.result,
            "reason": a.reason or "",
            "cmd": a.cmd or "",
        },
    )
    attr = attribution(case)
    key = f"{a.tool}:{a.action_name or 'run'}"
    g = attr["groups"].get(key, {})
    print(f"tool\t{key}\t{a.result}\tcounts ok={g.get('ok', 0)} blocked={g.get('blocked', 0)} error={g.get('error', 0)}")
    for t in attr["tripped"]:
        print(f"TRIPPED\t{t['key']}\tconsecutive_errors={t['consecutive_errors']}\t{t['reason']}")
    return 0


def cmd_verify(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    res = verify(case)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        s = res["stats"]
        print(f"goals {s['goals']} (open {s['goals_open']}) · hyps {s['hyps']} (open {s['hyps_open']}) · "
              f"findings {s['findings']} · intents_open {s['intents_open']} · coverage {s['tested']}/{s['targets']}")
        for e in res["errors"]:
            print("ERROR  " + e)
        for w in res["warnings"]:
            print("WARN   " + w)
        print("VERDICT " + ("收工" if res["ok"] else "未收官"))
    return 0 if res["ok"] else 1


def cmd_coverage(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    cov = coverage(case)
    if a.json:
        print(json.dumps(cov, ensure_ascii=False, indent=1))
    else:
        print(f"覆盖度 {cov['tested']}/{cov['total']} = {cov['percent']}%")
        for kind, b in cov["buckets"].items():
            pct = round(b["tested"] * 100.0 / b["total"], 1) if b["total"] else 0.0
            print(f"  {kind:<10} {b['tested']:>4}/{b['total']:<4} {pct:>5}%")
        if a.show_untested and cov["untested"]:
            print("未测：")
            for t in cov["untested"]:
                print("  " + t)
    return 0


def cmd_attr(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    attr = attribution(case)
    if a.json:
        print(json.dumps(attr, ensure_ascii=False, indent=1))
    else:
        for key, g in sorted(attr["groups"].items(), key=lambda kv: kv[1]["total"], reverse=True):
            print(f"{key:<34} ok={g['ok']:<3} blocked={g['blocked']:<3} error={g['error']:<3} {g['last_reason'][:50]}")
        for t in attr["tripped"]:
            print(f"TRIPPED {t['key']} 连续 error={t['consecutive_errors']} → 换路径")
    return 0


def cmd_guard(a: argparse.Namespace) -> int:
    rules = load_rules(a.rules)
    verdict = evaluate(a.command, rules)
    if a.case:
        case = case_dir(a.case)
        append(case, {"type": "audit", **verdict, "command": a.command[:400]})
    if a.json:
        print(json.dumps(verdict, ensure_ascii=False))
    else:
        print(f"{verdict['action'].upper()}\t{verdict['rule']}\t{verdict['reason']}\tmatched={verdict['matched']}")
    return {"allow": 0, "ask": 2, "deny": 3}.get(verdict["action"], 0)


def cmd_status(a: argparse.Namespace) -> int:
    case = case_dir(a.case)
    st = derive(case)
    cov = coverage(case)
    attr = attribution(case)
    print(f"case      {case}")
    print(f"goals     {len(st['goals'])}（open {sum(1 for g in st['goals'].values() if g['status'] == 'open')}）")
    print(f"hyps      {len(st['hyps'])}（open {sum(1 for h in st['hyps'].values() if h['verdict'] == 'open')}）")
    print(f"findings  {len(st['findings'])}")
    for fid, f in st["findings"].items():
        print(f"  {fid} {f.get('severity', ''):<8} evidence=v{evidence_version(st, fid)} "
              f"roles={[r.get('role') for r in st['binds'].get(fid, [])]} report="
              f"{'v' + str(st['reports'][fid].get('evidence_version')) if fid in st['reports'] else '-'} {f.get('title', '')[:40]}")
    print(f"coverage  {cov['tested']}/{cov['total']} = {cov['percent']}%")
    if attr["tripped"]:
        for t in attr["tripped"]:
            print(f"TRIPPED   {t['key']} 连续 error={t['consecutive_errors']}")
    return 0


# ---------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ledger", description="TGSEC engagement ledger v2")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="初始化 case 目录")
    s.add_argument("case")
    s.add_argument("--targets", help="从文件导入目标清单（分母）")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("goal")
    s.add_argument("action", choices=["add", "met", "drop", "list"])
    s.add_argument("case")
    s.add_argument("id", nargs="?")
    s.add_argument("--text")
    s.add_argument("--parent")
    s.add_argument("--note")
    s.add_argument("--by")
    s.add_argument("--reason")
    s.set_defaults(func=cmd_goal)

    s = sub.add_parser("hyp")
    s.add_argument("action", choices=["open", "verdict", "list"])
    s.add_argument("case")
    s.add_argument("id", nargs="?")
    s.add_argument("value", nargs="?", help="verdict 的简写位置参数：confirmed / refuted / inconclusive")
    s.add_argument("--text")
    s.add_argument("--signal")
    s.add_argument("--verdict", choices=["confirmed", "refuted", "inconclusive"])
    s.add_argument("--note")
    s.set_defaults(func=cmd_hyp)

    s = sub.add_parser("finding")
    s.add_argument("action", choices=["add"])
    s.add_argument("case")
    s.add_argument("--title", required=True)
    s.add_argument("--severity", default="medium")
    s.add_argument("--endpoint")
    s.add_argument("--hyp")
    s.set_defaults(func=cmd_finding)

    s = sub.add_parser("evidence")
    s.add_argument("action", choices=["bind"])
    s.add_argument("case")
    s.add_argument("--finding", required=True)
    s.add_argument("--role", required=True)
    s.add_argument("--file", required=True)
    s.add_argument("--note")
    s.add_argument("--cmd")
    s.set_defaults(func=cmd_evidence)

    s = sub.add_parser("report")
    s.add_argument("action", choices=["write"])
    s.add_argument("case")
    s.add_argument("--finding", required=True)
    s.add_argument("--path")
    s.add_argument("--note")
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("target")
    s.add_argument("action", choices=["add", "import", "list"])
    s.add_argument("case")
    s.add_argument("--value")
    s.add_argument("--kind", default="endpoint")
    s.add_argument("--from", dest="sources", nargs="+", help="产物文件或目录（targets.txt / api_static.txt / routes.txt / site_map.json）")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_target)

    s = sub.add_parser("tested")
    s.add_argument("case")
    s.add_argument("--target", required=True)
    s.add_argument("--finding")
    s.set_defaults(func=cmd_tested)

    s = sub.add_parser("intent")
    s.add_argument("action", choices=["open", "close"])
    s.add_argument("case")
    s.add_argument("id", nargs="?")
    s.add_argument("--text")
    s.add_argument("--outcome")
    s.set_defaults(func=cmd_intent)

    s = sub.add_parser("tool")
    s.add_argument("verb", choices=["log"], help="固定写 log")
    s.add_argument("case")
    s.add_argument("--tool", required=True)
    s.add_argument("--action-name", dest="action_name", default="run", help="工具动作名，默认 run")
    s.add_argument("--result", required=True)
    s.add_argument("--reason")
    s.add_argument("--cmd")
    s.set_defaults(func=cmd_tool)

    s = sub.add_parser("verify", help="收官判据（不通过 exit 1）")
    s.add_argument("case")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("coverage")
    s.add_argument("case")
    s.add_argument("--json", action="store_true")
    s.add_argument("--show-untested", action="store_true")
    s.set_defaults(func=cmd_coverage)

    s = sub.add_parser("attr")
    s.add_argument("case")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_attr)

    s = sub.add_parser("status")
    s.add_argument("case")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("guard", help="命令闸门：allow=0 / ask=2 / deny=3")
    s.add_argument("command")
    s.add_argument("--case")
    s.add_argument("--json", action="store_true")
    s.add_argument(
        "--rules",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard.rules.json"),
    )
    s.set_defaults(func=cmd_guard)
    return p


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv[1:]))
