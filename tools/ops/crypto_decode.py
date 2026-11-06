#!/usr/bin/env python3
"""Crypto decode toolbox: encoding chains, JWT payload, AES trial decrypt."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import urllib.parse
from pathlib import Path

CASES = Path("/root/cases")


def b64(s: str) -> str:
    pad = "=" * (-len(s) % 4)
    return base64.b64decode(s + pad, validate=False).decode("utf-8", errors="replace")


def auto(s: str) -> list[dict]:
    out = []
    cur = s
    for i in range(3):
        step = None
        if re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", cur):
            step = {"kind": "jwt", "value": jwt(cur)}
        elif re.fullmatch(r"[0-9a-fA-F]+", cur) and len(cur) % 2 == 0:
            step = {"kind": "hex", "value": bytes.fromhex(cur).decode("utf-8", errors="replace")}
        elif re.fullmatch(r"[A-Za-z0-9+/=_-]+", cur) and len(cur) >= 8:
            try:
                step = {"kind": "base64", "value": b64(cur)}
            except Exception:
                step = None
        if not step:
            break
        out.append(step)
        cur = step["value"]
        if not cur:
            break
    return out


def jwt(token: str) -> dict:
    parts = token.split(".")
    out = {"header": {}, "payload": {}, "signature": parts[2] if len(parts) > 2 else ""}
    for key, i in (("header", 0), ("payload", 1)):
        try:
            out[key] = json.loads(b64(parts[i]))
        except Exception:
            out[key] = parts[i] if i < len(parts) else ""
    return out


def aes_decrypt(data: str, key: str) -> str:
    try:
        from Crypto.Cipher import AES
    except ImportError:
        raise SystemExit("pycryptodome not installed: pip install pycryptodome")
    raw = base64.b64decode(data)
    cipher = AES.new(key.encode(), AES.MODE_CBC, raw[:16])
    plain = cipher.decrypt(raw[16:])
    plain = plain[:-plain[-1]] if plain and 0 < plain[-1] <= 16 else plain
    return plain.decode("utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser(description="编解码/JWT/AES 工具箱")
    ap.add_argument("action", choices=["auto", "jwt_decode", "aes_decrypt", "hash_id"],
                    nargs="?", default="auto")
    ap.add_argument("--list", action="store_true", dest="list_modes")
    ap.add_argument("--input", "-i")
    ap.add_argument("--key", "-k")
    ap.add_argument("--case", "-c")
    args = ap.parse_args()
    if args.list_modes:
        print("auto, jwt_decode, aes_decrypt, hash_id")
        return 0
    if not args.input:
        ap.error("--input required")
    if args.action == "auto":
        result = auto(args.input)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.action == "jwt_decode":
        result = jwt(args.input)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.action == "aes_decrypt":
        if not args.key:
            ap.error("--key required")
        result = {"plain": aes_decrypt(args.input, args.key)}
        print(result["plain"])
    else:
        result = {"sha256": hashlib.sha256(args.input.encode()).hexdigest(),
                  "md5": hashlib.md5(args.input.encode()).hexdigest(),
                  "sha1": hashlib.sha1(args.input.encode()).hexdigest()}
        print(json.dumps(result, indent=2))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        (case / "artifacts/crypto_decode.json").write_text(json.dumps({"action": args.action, "result": result}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[case] {case / 'artifacts/crypto_decode.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
