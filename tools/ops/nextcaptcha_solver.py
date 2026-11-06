#!/usr/bin/env python3
"""NextCaptcha solver adapter (real API; key required).

Usage:
  nextcaptcha_solver.py recaptcha2 https://target/login SITEKEY
  nextcaptcha_solver.py turnstile https://target/login SITEKEY --json

Key: --api-key or env NEXTCAPTCHA_API_KEY. The script creates one task, polls
until ready, prints the token, and never logs the API key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

DEFAULT_API = "https://api.nextcaptcha.com"
TYPE_MAP = {
    "recaptcha2": "RecaptchaV2TaskProxyLess",
    "recaptcha_v2": "RecaptchaV2TaskProxyLess",
    "recaptcha3": "RecaptchaV3TaskProxyLess",
    "recaptcha_v3": "RecaptchaV3TaskProxyLess",
    "hcaptcha": "HCaptchaTaskProxyLess",
    "turnstile": "TurnstileTaskProxyLess",
}


def post(url: str, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def main() -> int:
    ap = argparse.ArgumentParser(description="NextCaptcha task adapter")
    ap.add_argument("type", help="recaptcha2|recaptcha3|hcaptcha|turnstile")
    ap.add_argument("url")
    ap.add_argument("sitekey")
    ap.add_argument("--api-key", default=os.environ.get("NEXTCAPTCHA_API_KEY", ""))
    ap.add_argument("--api-url", default=DEFAULT_API)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--poll", type=float, default=3.0)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    task_type = TYPE_MAP.get(args.type.lower(), args.type)
    task = {"type": task_type, "websiteURL": args.url, "websiteKey": args.sitekey}
    if args.dry_run:
        print(json.dumps({"api_url": args.api_url, "task": task}, indent=2))
        return 0
    if not args.api_key:
        print("[nextcaptcha] missing key: set NEXTCAPTCHA_API_KEY or --api-key", file=sys.stderr)
        return 2

    base = args.api_url.rstrip("/")
    try:
        created = post(base + "/createTask", {"clientKey": args.api_key, "task": task}, args.timeout)
    except Exception as exc:  # noqa: BLE001
        print(f"[nextcaptcha] createTask failed: {exc}", file=sys.stderr)
        return 1
    if created.get("errorId"):
        print(f"[nextcaptcha] createTask error: {created.get('errorCode')} {created.get('errorDescription')}", file=sys.stderr)
        return 1
    task_id = created.get("taskId")
    if task_id is None:
        print(f"[nextcaptcha] no taskId: {created}", file=sys.stderr)
        return 1

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        time.sleep(args.poll)
        try:
            result = post(base + "/getTaskResult", {"clientKey": args.api_key, "taskId": task_id}, args.timeout)
        except Exception as exc:  # noqa: BLE001
            print(f"[nextcaptcha] poll failed: {exc}", file=sys.stderr)
            continue
        status = result.get("status")
        if status == "ready":
            solution = result.get("solution", {})
            if args.json:
                print(json.dumps({"taskId": task_id, "solution": solution}, ensure_ascii=False, indent=2))
            else:
                token = solution.get("gRecaptchaResponse") or solution.get("token") or solution.get("cf_clearance") or ""
                print(token)
            return 0
        if result.get("errorId"):
            print(f"[nextcaptcha] error: {result.get('errorCode')} {result.get('errorDescription')}", file=sys.stderr)
            return 1
    print(f"[nextcaptcha] timeout after {args.timeout}s (taskId={task_id})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
