#!/usr/bin/env python3
"""Gambling agent-account probe: discover, register, api-enum, fields."""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")
AGENT_PATHS = ["/agent/login", "/agent/register", "/daili", "/proxy", "/affiliate", "/partner",
               "/api/game/agent/login", "/api/game/agent/register", "/api/agent/login", "/api/agent/register"]
SUBS = ["agent", "affiliate", "partner", "proxy", "daili", "aff", "promo"]
API_PATHS = ["/api/game/agent/all-users", "/api/game/agent/member/list", "/api/agent/users",
             "/api/agent/balance", "/api/agent/report", "/api/agent/commission"]
SENSITIVE = ("sessionToken", "session", "token", "jwt", "accessToken", "refreshToken",
             "password", "password_hash", "passwordHash", "password_md5", "salt",
             "withdrawPassword", "withdrawPasswordHash", "payPassword", "payPasswordHash",
             "googleKey", "otpSecret")


def req(url: str, method: str = "GET", token: str | None = None, data: dict | None = None,
        timeout: float = 10, insecure: bool = False) -> dict:
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/html"}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(r, timeout=timeout, context=ctx) as resp:
            raw = resp.read(2 * 1024 * 1024)
            return {"status": resp.status, "len": len(raw), "body": raw.decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "len": 0, "body": e.read(2048).decode("utf-8", "replace")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def save(case: str | None, name: str, data) -> None:
    if not case:
        return
    p = Path(case) if Path(case).is_absolute() else CASES / case
    (p / "artifacts").mkdir(parents=True, exist_ok=True)
    (p / "artifacts" / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="代理商账号体系探针")
    ap.add_argument("action", choices=["discover", "register", "api-enum", "fields"])
    ap.add_argument("--base", "-b", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--token")
    ap.add_argument("--case")
    ap.add_argument("--paths")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    host = (urlparse(base).hostname or "").lower()
    allowed = args.scope.replace("*.", "").lower()
    if not (host == allowed or host.endswith("." + allowed)):
        print(f"[scope] DENY {host}")
        return 2

    if args.action == "discover":
        out = {}
        for p in AGENT_PATHS:
            out[p] = {k: v for k, v in req(base + p, timeout=args.timeout, insecure=args.insecure).items() if k != "body"}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        save(args.case, "agent_discover.json", out)
        return 0

    if args.action == "register":
        user = "selfprobe" + secrets.token_hex(4)
        password = "Test@" + secrets.token_hex(4)
        payload = {"username": user, "password": password}
        if args.dry_run:
            print(json.dumps({"would_post": base + "/api/game/agent/register", "payload_keys": list(payload)}, indent=2))
            return 0
        attempts = ["/api/game/agent/register", "/api/agent/register", "/agent/register"]
        out = {"username": user, "attempts": []}
        for p in attempts:
            r = req(base + p, "POST", data=payload, timeout=args.timeout, insecure=args.insecure)
            out["attempts"].append({"path": p, "status": r.get("status"), "len": r.get("len"),
                                    "body": r.get("body", "")[:300]})
            if r.get("status") == 200:
                break
        print(json.dumps(out, ensure_ascii=False, indent=2))
        save(args.case, "agent_register.json", out)
        return 0

    if args.action == "fields":
        paths = (args.paths or ",".join(API_PATHS)).split(",")
        out = {"paths": {}, "sensitive": {}, "tokens": {"total": 0, "live": 0, "expired": 0}}
        for p in paths:
            r = req(base + p.strip(), token=args.token, timeout=args.timeout, insecure=args.insecure)
            out["paths"][p] = {"status": r.get("status"), "len": r.get("len")}
            try:
                obj = json.loads(r.get("body", "{}"))
            except Exception:
                continue
            rows = obj if isinstance(obj, list) else obj.get("data", obj.get("list", [])) if isinstance(obj, dict) else []
            if isinstance(rows, dict):
                rows = [rows]
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict):
                    continue
                for k in row:
                    if k in SENSITIVE:
                        out["sensitive"][k] = out["sensitive"].get(k, 0) + 1
                for k in ("token", "sessionToken", "accessToken", "jwt"):
                    v = row.get(k)
                    if isinstance(v, str) and v.count(".") == 2:
                        out["tokens"]["total"] += 1
                        try:
                            payload = v.split(".")[1]
                            payload += "=" * (-len(payload) % 4)
                            import base64
                            exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0)
                            import time
                            out["tokens"]["live" if exp > time.time() else "expired"] += 1
                        except Exception:
                            pass
        print(json.dumps(out, ensure_ascii=False, indent=2))
        save(args.case, "agent_field_audit.json", out)
        return 0

    out = {}
    for p in API_PATHS:
        r = req(base + p, token=args.token, timeout=args.timeout, insecure=args.insecure)
        out[p] = {k: v for k, v in r.items() if k != "body"}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    save(args.case, "agent_api_enum.json", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
