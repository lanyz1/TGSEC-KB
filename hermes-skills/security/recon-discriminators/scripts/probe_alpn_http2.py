#!/usr/bin/env python3
"""判定目标是否 HTTP/2-only,并给出可用的取值方式。

用法:
    python3 probe_alpn_http2.py <host> [ip] [path ...]

    # 例:
    python3 probe_alpn_http2.py dev.example.com 1.2.3.4
    python3 probe_alpn_http2.py example.com 1.2.3.4 /api/docs /api/health

行为:
  1) 解析 host(或使用给定 ip)
  2) 对 443 做 ALPN 协商,打印选中的协议  <-- 判定的关键一步
  3) 用原始 socket 发 HTTP/1.1,展示是否收到 GOAWAY / 空回复
  4) 若 httpx[h2] 可用,用 HTTP/2 真正取一遍页面,打印状态码/长度/片段

判读:
  ALPN == 'h2' 且 HTTP/1.1 得到空回复/GOAWAY  ->  HTTP/2-only 主机
  修复: pip install --break-system-packages "httpx[http2]"
        httpx.Client(http2=True, verify=False, timeout=25)

依赖:
  标准库即可跑完 1~3 步;第 4 步需要 httpx(带 h2): pip install "httpx[http2]"
"""
import socket
import ssl
import sys

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def resolve(host, ip=None):
    if ip:
        return ip
    try:
        return socket.gethostbyname(host)
    except Exception as exc:
        print(f"[!] DNS 解析失败 {host}: {exc}")
        return None


def check_alpn(host, ip, port=443, timeout=10):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    try:
        raw = socket.create_connection((ip, port), timeout=timeout)
    except Exception as exc:
        print(f"[!] TCP 连接失败 {ip}:{port}: {exc}")
        return None
    try:
        tls = ctx.wrap_socket(raw, server_hostname=host)
    except Exception as exc:
        print(f"[!] TLS 握手失败: {type(exc).__name__}: {exc}")
        raw.close()
        return None
    alpn = tls.selected_alpn_protocol()
    print(f"[*] TLS 版本     : {tls.version()}")
    print(f"[*] ALPN 选中    : {alpn!r}   <-- 关键判据")
    return tls


def http1_probe(tls, host):
    """在协商好的连接上发 HTTP/1.1,看服务端是否给 GOAWAY / 空回复。"""
    req = (f"GET / HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {UA}\r\n"
           "Accept: */*\r\nConnection: close\r\n\r\n")
    try:
        tls.sendall(req.encode())
        data = tls.recv(400)
    except Exception as exc:
        print(f"[*] HTTP/1.1 读取异常: {type(exc).__name__}")
        return b""
    if not data:
        print("[*] HTTP/1.1 响应: 空回复(零字节)")
    elif data.startswith(b"HTTP/"):
        print(f"[*] HTTP/1.1 响应: {data.splitlines()[0]!r}")
    else:
        print(f"[*] HTTP/1.1 响应: 非 HTTP 数据,疑似 h2 帧/GOAWAY -> {data[:24]!r}")
    return data


def http2_fetch(host, ip, paths):
    try:
        import httpx
    except ImportError:
        print("[i] 未安装 httpx,跳过 HTTP/2 实测。安装: "
              'pip install --break-system-packages "httpx[http2]"')
        return
    try:
        client = httpx.Client(http2=True, verify=False, timeout=25,
                             headers={"User-Agent": UA, "Accept": "*/*"},
                             follow_redirects=False)
    except Exception as exc:
        print(f"[!] httpx 初始化失败(可能缺 h2): {exc}")
        print('    安装: pip install --break-system-packages "httpx[http2]"')
        return
    for path in paths:
        url = f"https://{host}{path}"
        try:
            resp = client.get(url, extensions={"sni_hostname": host} if ip else None)
            body = resp.text[:200].replace("\n", " ")
            print(f"[+] {path:<20} {resp.status_code} {len(resp.content)}B  {body}")
        except Exception as exc:
            print(f"[!] {path:<20} {type(exc).__name__}: {str(exc)[:120]}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    host = sys.argv[1]
    ip = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2][0].isdigit() else None
    paths = [a for a in sys.argv[2:] if a.startswith("/")] or ["/", "/api/docs",
                                                              "/api/health"]
    ip = resolve(host, ip)
    if not ip:
        return 2
    print(f"[*] 目标 {host} -> {ip}")
    tls = check_alpn(host, ip)
    if tls:
        http1_probe(tls, host)
        tls.close()
    print("[*] 试 HTTP/2 实取 ...")
    http2_fetch(host, ip, paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())
