#!/usr/bin/env python3
"""Unauthenticated middleware checks: Redis/ES/Mongo/Memcached/Docker."""
from __future__ import annotations

import argparse
import json
import socket
import urllib.request


def tcp(host: str, port: int, timeout: float) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def redis(host: str, port: int, timeout: float) -> dict:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.sendall(b"*1\r\n$4\r\nPING\r\n")
        data = s.recv(128)
        s.close()
        return {"open": True, "pong": b"PONG" in data}
    except Exception as e:
        return {"open": False, "error": str(e)}


def http(url: str, timeout: float) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"status": r.status, "body": r.read(300).decode("utf-8", errors="replace")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="中间件未授权检查")
    ap.add_argument("--host", "-H", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--timeout", type=float, default=4)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ports", help="comma-separated subset: 6379,9200,11211,2375")
    args = ap.parse_args()
    if args.host.lower() != args.scope.replace("*.", "").lower():
        print(f"[scope] DENY {args.host} (scope={args.scope})")
        return 2
    wanted = {int(x) for x in args.ports.split(",") if x.strip()} if args.ports else {6379, 9200, 11211, 2375}
    out = {}
    if 6379 in wanted and tcp(args.host, 6379, args.timeout):
        out["redis"] = redis(args.host, 6379, args.timeout)
    if 9200 in wanted and tcp(args.host, 9200, args.timeout):
        out["elasticsearch"] = http(f"http://{args.host}:9200/", args.timeout)
    if 11211 in wanted and tcp(args.host, 11211, args.timeout):
        try:
            s = socket.create_connection((args.host, 11211), timeout=args.timeout)
            s.sendall(b"stats\r\n")
            out["memcached"] = {"open": True, "stats": s.recv(500).decode("utf-8", errors="replace")[:300]}
            s.close()
        except Exception as e:
            out["memcached"] = {"error": str(e)}
    if 2375 in wanted and tcp(args.host, 2375, args.timeout):
        out["docker"] = http(f"http://{args.host}:2375/version", args.timeout)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
