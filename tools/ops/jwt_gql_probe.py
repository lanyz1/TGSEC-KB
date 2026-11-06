#!/usr/bin/env python3
"""GraphQL introspection + JWT payload view."""
from __future__ import annotations

import argparse
import base64
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")
Q = {"query": "{__schema{types{name kind}}}"}


def post(url: str, token: str | None, timeout: float, insecure: bool) -> dict:
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=json.dumps(Q).encode(), headers=headers, method="POST")
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(16384).decode("utf-8", "replace")
            return {"status": r.status, "len": len(body), "introspection": "__schema" in body or "types" in body}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0, "body": e.read(1024).decode("utf-8", "replace")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def jwt_payload(token: str) -> dict:
    try:
        p = token.split(".")[1]
        p += "=" * (-len(p) % 4)
        return json.loads(base64.urlsafe_b64decode(p))
    except Exception as e:
        return {"error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser(description="GraphQL/JWT 面探针")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--token")
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    host = (urlparse(args.url).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2
    out = {"anon": post(args.url, None, args.timeout, args.insecure),
           "auth": post(args.url, args.token, args.timeout, args.insecure) if args.token else None}
    if args.token:
        out["jwt"] = jwt_payload(args.token)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/gql_jwt.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/gql_jwt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
