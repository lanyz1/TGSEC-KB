#!/usr/bin/env python3
"""localproxy.py - local, credential-free HTTP proxy that chains to an UPSTREAM
AUTHENTICATED HTTP proxy.

Why this exists
---------------
Chrome/Chromium/Firefox (and Playwright's HTTP proxy handling) do NOT honour
credentials embedded in a proxy URL such as --proxy-server=http://user:pass@host:port.
They strip them or simply fail to authenticate, which looks exactly like a broken
egress. The fix: run this shim locally, point the browser at it with NO credentials,
and let the shim attach Proxy-Authorization for the upstream hop.

Usage
-----
export UPSTREAM_HOST=proxy.example.com
export UPSTREAM_PORT=10000
export UPSTREAM_USER='account-or-account-country-session'
export UPSTREAM_PASS='secret'
export LISTEN=127.0.0.1:8899
python3 localproxy.py

  chrome --proxy-server=http://127.0.0.1:8899
  # Playwright/Camoufox: launch(proxy={"server": "http://127.0.0.1:8899"})

Verify the egress BEFORE blaming the browser:
  curl -x http://127.0.0.1:8899 https://api.ipify.org

Notes
-----
* The upstream credentials are re-read from the environment on every connection, so a
  wrapper can rotate them (some providers change the exit IP per CONNECT).
* Handles CONNECT tunnels (https) and absolute-URI plain HTTP (http).
* stdlib only; no dependencies.
"""
import base64
import os
import socket
import threading

UPSTREAM_HOST = os.environ.get("UPSTREAM_HOST", "")
UPSTREAM_PORT = int(os.environ.get("UPSTREAM_PORT", "0") or 0)
LISTEN_SPEC = os.environ.get("LISTEN", "127.0.0.1:8899")
LISTEN_HOST, LISTEN_PORT = LISTEN_SPEC.rsplit(":", 1)
LISTEN_PORT = int(LISTEN_PORT)
TIMEOUT = float(os.environ.get("PROXY_TIMEOUT", "30"))


def upstream_auth_header():
    """Re-read creds each call so an external wrapper can rotate them."""
    user = os.environ.get("UPSTREAM_USER", "")
    password = os.environ.get("UPSTREAM_PASS", "")
    if not user:
        return b""
    token = <REDACTED> + ":" + password).encode()).decode()
    return ("Proxy-Authorization: Basic %s\r\n" % token).encode()


def upstream_connect_tunnel(host, port):
    """Open a CONNECT tunnel through the upstream proxy. Returns (socket, leftover)."""
    sock = socket.create_connection((UPSTREAM_HOST, UPSTREAM_PORT), timeout=TIMEOUT)
    req = (
        "CONNECT %s:%d HTTP/1.1\r\n"
        "Host: %s:%d\r\n"
        "Proxy-Connection: keep-alive\r\n" % (host, port, host, port)
    ).encode() + upstream_auth_header() + b"\r\n"
    sock.sendall(req)
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise OSError("upstream closed during CONNECT")
        buf += chunk
    status = buf.split(b"\r\n", 1)[0]
    if b" 200" not in status:
        raise OSError("upstream CONNECT failed: %r" % status)
    _, _, rest = buf.partition(b"\r\n\r\n")
    return sock, rest


def read_headers(sock):
    """Read an HTTP request head from the client. Returns (head_bytes, leftover)."""
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            return (buf, b"")
        buf += chunk
    head, _, rest = buf.partition(b"\r\n\r\n")
    return head, rest


def pump(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def handle(client):
    try:
        head, leftover = read_headers(client)
        if not head:
            client.close()
            return
        lines = head.split(b"\r\n")
        parts = lines[0].split(b" ", 2)
        method = parts[0].upper()
        target = parts[1] if len(parts) > 1 else b""

        if method == b"CONNECT":
            host, _, port = target.decode().rpartition(":")
            remote, rest = upstream_connect_tunnel(host, int(port))
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            if rest:
                remote.sendall(rest)
            if leftover:
                remote.sendall(leftover)
        else:
            # Plain HTTP: hand the absolute-URI request to the upstream proxy,
            # injecting the auth header if the client did not supply one.
            remote = socket.create_connection((UPSTREAM_HOST, UPSTREAM_PORT), timeout=TIMEOUT)
            if b"proxy-authorization" not in head.lower():
                head = lines[0] + b"\r\n" + upstream_auth_header() + b"\r\n".join(lines[1:])
            remote.sendall(head + b"\r\n\r\n" + leftover)

        threading.Thread(target=pump, args=(client, remote), daemon=True).start()
        threading.Thread(target=pump, args=(remote, client), daemon=True).start()
    except Exception as exc:  # keep the shim alive; one bad connection is not fatal
        print("[localproxy] error: %r" % (exc,), flush=True)
        try:
            client.close()
        except OSError:
            pass


def main():
    if not UPSTREAM_HOST or not UPSTREAM_PORT:
        raise SystemExit("set UPSTREAM_HOST / UPSTREAM_PORT")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((LISTEN_HOST, LISTEN_PORT))
    srv.listen(128)
    print("[localproxy] %s:%d -> %s:%d" % (LISTEN_HOST, LISTEN_PORT, UPSTREAM_HOST, UPSTREAM_PORT), flush=True)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
