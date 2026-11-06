#!/usr/bin/env python3
"""Minimal WebSocket probe: handshake + optional one text frame."""
from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import ssl
import struct
import time
from pathlib import Path
from urllib.parse import urlparse

CASES = Path("/root/cases")


def frame(text: str) -> bytes:
    data = text.encode()
    mask = os.urandom(4)
    payload = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    n = len(payload)
    if n < 126:
        head = bytes([0x81, 0x80 | n])
    elif n < 65536:
        head = bytes([0x81, 0xFE]) + struct.pack(">H", n)
    else:
        head = bytes([0x81, 0xFF]) + struct.pack(">Q", n)
    return head + mask + payload


def read_frame(sock) -> bytes:
    first = sock.recv(2)
    if len(first) < 2:
        return b""
    n = first[1] & 0x7F
    if n == 126:
        n = struct.unpack(">H", sock.recv(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", sock.recv(8))[0]
    return sock.recv(n)


def main() -> int:
    ap = argparse.ArgumentParser(description="WebSocket 握手/单帧探针")
    ap.add_argument("--url", "-u", required=True)
    ap.add_argument("--send", help="text frame after handshake")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--case", "-c")
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    u = urlparse(args.url)
    host = u.hostname or ""
    port = u.port or (443 if u.scheme == "wss" else 80)
    key = base64.b64encode(os.urandom(16)).decode()
    path = u.path or "/"
    if u.query:
        path += "?" + u.query
    req = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
           f"Origin: https://{host}\r\n\r\n")
    raw = socket.create_connection((host, port), timeout=args.timeout)
    if u.scheme == "wss":
        raw = ssl._create_unverified_context().wrap_socket(raw, server_hostname=host)
    raw.sendall(req.encode())
    head = raw.recv(4096).decode("utf-8", errors="replace")
    status = head.splitlines()[0] if head else "NO RESPONSE"
    print(status)
    for line in head.splitlines()[1:]:
        if line.lower().startswith(("sec-websocket", "upgrade", "connection")):
            print(line)
    if args.send and "101" in status:
        raw.sendall(frame(args.send))
        raw.settimeout(args.timeout)
        print("[recv]", read_frame(raw)[:1000])
    raw.close()
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/ws_probe.json"
        out.write_text(json.dumps({"url": args.url, "status": status, "headers": head[:2000]}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
