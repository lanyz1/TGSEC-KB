#!/usr/bin/env python3
"""TG cloud-panel surface probe: login hits, accounts/proxy APIs, Fernet clues."""
from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")
PATHS = ["/", "/login", "/api/login", "/proxy/list", "/api/proxy/list", "/admin/users",
         "/api/accounts", "/api/sessions", "/main.wasm", "/assets/"]


def get(url: str, timeout: float, insecure: bool) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(8192).decode("utf-8", "replace")
            return {"status": r.status, "len": len(body),
                    "login": any(x in body.lower() for x in ("login", "登录", "password")),
                    "fernet": body.count("gAAAAA"), "jwt": len(re.findall(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}", body))}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0, "login": False, "fernet": 0, "jwt": 0}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="TG 云控面板探针")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--case")
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    base = args.url.rstrip("/")
    host = (urlparse(base).hostname or "").lower()
    if not host:
        print("[scope] invalid url")
        return 2
    out: dict[str, object] = {p: get(base + p, args.timeout, args.insecure) for p in PATHS}
    out["login_hits"] = [p for p, r in out.items() if isinstance(r, dict) and r.get("login")]
    out["fernet_hits"] = [p for p, r in out.items() if isinstance(r, dict) and r.get("fernet")]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/tg_cloud_panel.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", case / "artifacts/tg_cloud_panel.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
