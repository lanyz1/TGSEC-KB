#!/usr/bin/env python3
"""Probe a relay proxy node to classify its state.

Usage:
  python probe_relay.py HOST PORT [USER PASS]

Output classification:
  - TCP OK + SOCKS5 connect accepted  -> healthy socks5 node
  - SOCKS5 "wrong version" + TCP OK   -> NOT socks5 (auth proxy tunnel / custom)
  - HTTP no-auth -> 407               -> HTTP-proxy facade
  - auth CONNECT -> binary + "Connection timed out" -> ACCOUNT EXPIRED (fake timeout)
  - TCP fail / connect timeout        -> node truly dead
"""
import socket, base64, sys

def probe(host: str, port: int, user: str | None, pwd: str | None):
    target = "www.google.com"
    print(f"=== probe {host}:{port} user={user} ===")

    # TCP
    try:
        s = socket.create_connection((host, port), timeout=8)
        s.close()
        print("TCP: OK")
    except Exception as e:
        print("TCP: FAIL", e)
        return

    # SOCKS5 handshake (auth if creds given)
    try:
        s = socket.create_connection((host, port), timeout=8)
        if user:
            s.sendall(b"\x05\x01\x02")
            r = s.recv(2)
            if len(r) == 2 and r[0] == 5:
                s.sendall(bytes([1, len(user)]) + user.encode()
                          + bytes([len(pwd)]) + pwd.encode())
                r = s.recv(2)
                s.sendall(b"\x05\x01\x00\x03" + bytes([len(target)])
                          + target.encode() + b"\x01\xbb")
                r = s.recv(10)
                if len(r) >= 2 and r[1] == 0:
                    print("SOCKS5: OK (auth + connect accepted)")
                else:
                    print(f"SOCKS5: connect refused reply={r.hex()}")
            else:
                print(f"SOCKS5: WRONG VERSION reply={r.hex()}  <-- not socks5, try HTTP/CONNECT")
        else:
            s.sendall(b"\x05\x01\x00")
            r = s.recv(2)
            if len(r) == 2 and r[0] == 5 and r[1] == 0:
                print("SOCKS5: OK (no-auth)")
            else:
                print(f"SOCKS5: unexpected reply={r.hex()} (may be non-socks service)")
        s.close()
    except Exception as e:
        print("SOCKS5: ERR", e)

    # HTTP CONNECT with/without auth
    for label, auth in (("HTTP(no-auth)", None), ("HTTP(auth)", (user, pwd))):
        if label == "HTTP(auth)" and not user:
            continue
        try:
            s = socket.create_connection((host, port), timeout=8)
            req = f"CONNECT {target}:443 HTTP/1.1\r\nHost: {target}:443\r\n"
            if auth:
                tok = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
                req += f"Proxy-Authorization: Basic {tok}\r\n"
            req += "\r\n"
            s.sendall(req.encode())
            s.settimeout(5)
            data = s.recv(200)
            txt = data.decode(errors="replace")
            if txt.startswith("HTTP/1.1 200"):
                print(f"{label}: 200 OK (proxy works)")
            elif txt.startswith("HTTP/1.1 407"):
                print(f"{label}: 407 auth required (facade)")
            elif "Connection timed out" in txt or "\x00" in txt:
                print(f"{label}: auth passed but OUTBOUND TIMEOUT -> ACCOUNT EXPIRED / dead relay")
                print("   raw:", txt[:120].encode().hex())
            else:
                print(f"{label}: unknown resp: {txt[:120]!r}")
            s.close()
        except Exception as e:
            print(f"{label}: ERR", e)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    host = sys.argv[1]
    port = int(sys.argv[2])
    user = sys.argv[3] if len(sys.argv) > 3 else None
    pwd = <REDACTED> if len(sys.argv) > 4 else None
    probe(host, port, user, pwd)
