#!/usr/bin/env python3
"""Business-logic probes: concurrent race + negative/zero amount differential."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import ssl
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")


def send(url: str, data: str, ctype: str, timeout: float, insecure: bool) -> dict:
    req = urllib.request.Request(url, data=data.encode(), method="POST",
                                 headers={"Content-Type": ctype, "User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(4096).decode("utf-8", "replace")
            return {"status": r.status, "len": len(body), "body": body}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0, "body": e.read(1024).decode("utf-8", "replace")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="业务逻辑竞态/负值探针")
    ap.add_argument("action", choices=["race", "negative"], nargs="?")
    ap.add_argument("--url", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--data", default="{}")
    ap.add_argument("--ctype", default="application/json")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--field", default="amount")
    ap.add_argument("--value", default="-1")
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    if args.action == "race":
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.n, 30)) as ex:
            rs = list(ex.map(lambda _: send(args.url, args.data, args.ctype, args.timeout, args.insecure), range(args.n)))
        stats = Counter((r.get("status"), r.get("len")) for r in rs)
        out = {"n": args.n, "stats": [[k[0], k[1], v] for k, v in stats.items()], "errors": sum(1 for r in rs if "error" in r)}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        try:
            obj = json.loads(args.data)
        except Exception:
            obj = {}
        if not isinstance(obj, dict):
            obj = {}
        base = send(args.url, json.dumps(obj), args.ctype, args.timeout, args.insecure)
        obj[args.field] = args.value
        test = send(args.url, json.dumps(obj), args.ctype, args.timeout, args.insecure)
        out = {"field": args.field, "value": args.value, "base": {k: base.get(k) for k in ("status", "len", "error")},
               "test": {k: test.get(k) for k in ("status", "len", "error")}, "differential": base.get("status") != test.get("status") or base.get("len") != test.get("len")}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        p = case / "artifacts/logic_probe.json"
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
