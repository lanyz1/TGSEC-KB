#!/usr/bin/env python3
"""socks5 认证代理 -> 本地 HTTP CONNECT 代理桥（服务器端）。

用途：Chrome/puppeteer/签名服务不支持 --proxy-server 内嵌 socks5 认证，
起本桥后让它们连 http://127.0.0.1:8888（无认证），桥负责 socks5 握手+转发。

用法：python3 proxy_bridge_srv.py 8888   （改 UP/USER/PASS 为实际代理）
验证：curl -x http://127.0.0.1:8888 http://ip-api.com/json  （应显示代理出口 IP）
"""
import socket, threading, struct, sys

UP = ("q0_1746307169.ga6x.com", 30801)   # 上游 socks5 代理
USER = b"q0_1746307169-ddcn-92163419290624"
PASS = b"c6f8d10e"

def sock5_connect(host, port):
    s = socket.create_connection(UP, timeout=20)
    s.sendall(b"\x05\x02\x00\x02")
    resp = s.recv(2)
    if resp == b"\x05\x02":
        s.sendall(b"\x01" + bytes([len(USER)]) + USER + bytes([len(PASS)]) + PASS)
        if s.recv(2) != b"\x01\x00":
            raise Exception("认证失败")
    elif resp != b"\x05\x00":
        raise Exception("socks5 握手失败: %r" % resp)
    s.sendall(b"\x05\x01\x00\x03" + bytes([len(host)]) + host.encode() + struct.pack(">H", port))
    r = s.recv(4)
    if r[1] != 0:
        raise Exception("CONNECT 失败: %r" % r)
    atyp = r[3]
    if atyp == 1: s.recv(6)        # IPv4
    elif atyp == 4: s.recv(18)     # IPv6
    else:                          # 域名
        l = s.recv(1)[0]; s.recv(l + 2)
    return s

def pipe(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d: break
            b.sendall(d)
    except Exception:
        pass
    finally:
        try: b.shutdown(socket.SHUT_WR)
        except Exception: pass

def handle(client):
    try:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = client.recv(4096)
            if not chunk: return
            data += chunk
        line = data.split(b"\r\n")[0].decode(errors="ignore")
        parts = line.split(" ")
        if len(parts) < 2 or parts[0] != "CONNECT":
            client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            return
        host, port_s = parts[1].rsplit(":", 1)
        up = sock5_connect(host, int(port_s))
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        threading.Thread(target=pipe, args=(client, up), daemon=True).start()
        pipe(up, client)
    except Exception:
        try: client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        except Exception: pass
    finally:
        try: client.close()
        except Exception: pass

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(50)
    print(f"桥已启动: 127.0.0.1:{port}", flush=True)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()

if __name__ == "__main__":
    main()
