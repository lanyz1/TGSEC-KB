#!/usr/bin/env python3
"""Probe a step-up authorize endpoint with foreign object IDs and a bogus factor.

The goal is to see WHICH layer rejects: schema (422), factor (CODE_INVALID),
object ownership (NOT_FOUND/FORBIDDEN), or success (token).

Usage:
  python3 stepup_authorize_probe.py --url https://host/api/v1/exports/x/authorize \
      --headers headers.json --cookies cookies.json \
      --ids 18906,999999 --methods EMAIL,TOTP --code 000000

headers.json / cookies.json are flat {name: value} maps. --ids takes strings.
"""
import argparse
import json

import requests


def load(path: str) -> dict:
    try:
        return json.load(open(path, encoding="utf-8")) if path else {}
    except Exception:
        return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--headers", default="")
    ap.add_argument("--cookies", default="")
    ap.add_argument("--ids", default="1")
    ap.add_argument("--methods", default="EMAIL,TOTP")
    ap.add_argument("--code", default="000000")
    ap.add_argument("--id-field", default="card_ids")
    ap.add_argument("--method-field", default="verification_method")
    ap.add_argument("--code-field", default="verification_code")
    args = ap.parse_args()

    headers = load(args.headers)
    cookies = load(args.cookies)
    ids = [x.strip() for x in args.ids.split(",") if x.strip()]
    for method in [m.strip() for m in args.methods.split(",") if m.strip()]:
        body = {args.id_field: ids, args.method_field: method, args.code_field: args.code}
        try:
            r = requests.post(args.url, json=body, headers=headers, cookies=cookies, timeout=25, verify=False)
            print(f"[{method}] ids={ids} -> {r.status_code}")
            print("  " + r.text[:400].replace("\n", " "))
        except Exception as exc:  # noqa: BLE001
            print(f"[{method}] ERR {exc}")


if __name__ == "__main__":
    main()
