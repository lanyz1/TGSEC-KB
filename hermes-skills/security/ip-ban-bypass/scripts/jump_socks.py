#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""paramiko SOCKS5 动态隧道: 本地监听 127.0.0.1:<local_port>, 经跳板 SSH 转发。
用法: python jump_socks.py <jump_ip> <jump_port> <user> <pass> <local_port>
实测(2026-09 OKPay): 跳板 103.109.21.198 → 本地 20800 → requests socks5h 绕过目标 IP 风控。
要求: pip install paramiko; 目标方用 requests + socks5h://127.0.0.1:<local_port>(urllib+socks 打 HTTPS 会 SSL EOF)
"""
import paramiko, socket, select, threading, sys, time

def handle(conn, ssh):
    # SOCKS5 握手: VER=5 NMETHODS=1 METHOD=0(no-auth)
    h = conn.recv(4)
    if len(h) < 4 or h[0] != 5:
        conn.close(); return
    conn.sendall(b"\x05\x00")
    # 请求: VER CMD RSV ATYP
    req = conn.recv(4)
    if len(req) < 4 or req[1] != 1:  # 仅 CONNECT
        conn.close(); return
    atyp = req[3]
    if atyp == 1:      # IPv4
        host = socket.inet_ntoa(conn.recv(4))
    elif atyp == 3:    # 域名
        ln = conn.recv(1)[0]
        host = conn.recv(ln).decode()
    elif atyp == 4:    # IPv6
        host = socket.inet_ntop(socket.AF_INET6, conn.recv(16))
    else:
        conn.close(); return
    port = int.from_bytes(conn.recv(2), "big")
    try:
        chan = ssh.get_transport().open_channel("direct-tcpip", (host, port), ("127.0.0.1", 0))
    except Exception:
        conn.close(); return
    conn.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
    socks = [conn, chan]
    while True:
        r, _, _ = select.select(socks, [], [], 60)
        if not r:
            continue
        for s in r:
            try:
                data = s.recv(65536)
            except Exception:
                data = b""
            if not data:
                conn.close(); chan.close(); return
            dst = chan if s is conn else conn
            try:
                dst.sendall(data)
            except Exception:
                conn.close(); chan.close(); return

def main():
    ip, port, user, pw, lp = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, port=port, username=user, password=pw, timeout=25)
    print(f"[tunnel] {user}@{ip}:{port} up, listening 127.0.0.1:{lp}", flush=True)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", lp))
    srv.listen(50)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn, ssh), daemon=True).start()

if __name__ == "__main__":
    main()
