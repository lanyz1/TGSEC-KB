#!/usr/bin/env python3
"""Error-differential fingerprint probe for signed-REST WP backdoors (link-factory class).

Authorized testing only; read-only probing (no write can succeed without a valid signature).

Usage: python3 fingerprint_signed_rest.py https://target.tld [namespace] [route]
Defaults: namespace=link-factory/v1, route=articles.

Reading the output:
  * gate-order error strings map the validation chain (headers -> timestamp -> nonce -> signature)
  * 500 on a 63/65-byte signature = uncaught SodiumException -> native libsodium,
    no length precheck; WP_DEBUG_DISPLAY sites leak file:line in the body
"""
import base64
import sys
import time
import urllib.error
import urllib.request

if len(sys.argv) < 2:
    sys.exit("usage: fingerprint_signed_rest.py https://host [ns] [route]")
BASE = sys.argv[1].rstrip("/")
NS = sys.argv[2] if len(sys.argv) > 2 else "link-factory/v1"
ROUTE = sys.argv[3] if len(sys.argv) > 3 else "articles"
PREFIX = "X-Link-Factory"  # header family; adjust if error text names a different prefix
U = f"{BASE}/wp-json/{NS}"


def call(method, path, headers=None, body=None):
    req = urllib.request.Request(U + path, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status, r.read(400).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(400).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, repr(e)


def hdrs(sig, ts, nonce):
    return {
        "Content-Type": "application/json",
        f"{PREFIX}-Signature": sig,
        f"{PREFIX}-Timestamp": str(ts),
        f"{PREFIX}-Nonce": nonce,
        f"{PREFIX}-Protocol-Version": "5",
    }


def b64(n):
    return base64.b64encode(b"\x00" * n).decode()


now = int(time.time())
print("health:", *call("GET", "/health"))
probes = [
    ("no headers", {}, b"{}"),
    ("stale ts (now-3600)", hdrs(b64(64), now - 3600, "p2"), b"{}"),
    ("64B garbage sig", hdrs(b64(64), now, "p3"), b"{}"),
    ("63B sig (expect 500)", hdrs(b64(63), now, "p4"), b"{}"),
    ("65B sig (expect 500)", hdrs(b64(65), now, "p5"), b"{}"),
]
fallback = []
for label, h, body in probes:
    st, txt = call("POST", f"/{ROUTE}", h, body)
    print(f"{label}: {st} {txt[:240]}")
    if st == 404:
        fallback.append((label, h, body))
if fallback and ROUTE != "sentences":
    print("-- route 404, retrying on /sentences --")
    for label, h, body in fallback:
        st, txt = call("POST", "/sentences", h, body)
        print(f"{label} @sentences: {st} {txt[:240]}")
