#!/usr/bin/env python3
"""Telegram bot command/webhook enumeration via Bot API."""
from __future__ import annotations

import argparse
import json
import urllib.request


def api(token: str, method: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="TG Bot 命令/回调枚举")
    ap.add_argument("--token", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    out = {m: api(args.token, m) for m in ("getMe", "getMyCommands", "getWebhookInfo")}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for m, r in out.items():
            print(m, "ok=", r.get("ok"), r.get("result", r.get("error")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
