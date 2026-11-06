#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探针对照组测试 —— 检测中间层(代理/网关)是否在撒谎

原理：用同一个中间层去连【目标的真实端口】和【已知必然不可达的端口】。
  死端口也返回数据  → 中间层没连目标，拿自己的页面冒充(撒谎)，结论作废
  死端口无数据、真端口有数据 → 中间层诚实，数据可信

判据细节：不能只看内容 md5 差异 —— 差异常只来自 REQUEST_URI 里带的端口号。
必须比对【关键字段】(Server / REMOTE_ADDR / banner) 是否一致。

用法:
  python3 probe_control_test.py <目标IP> --port 8853
  python3 probe_control_test.py <目标IP> --port 8853 --control 9999 --control 80
  python3 probe_control_test.py <目标IP> --port 8853 --proxy 1.2.3.4:8080 --proxy 5.6.7.8:3128
  python3 probe_control_test.py <目标IP> --port 8853 --proxy-file proxies.txt

退出码: 0 = 至少一个中间层诚实; 2 = 全部撒谎; 3 = 全部无效(得不出结论)
"""
import argparse
import re
import socket
import sys
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = 12

# 回应里能指认"这是谁回的"的关键字段
KEY_FIELDS = re.compile(
    r"(?im)^\s*(REMOTE_ADDR|SERVER_ADDR|SERVER_NAME|HTTP_HOST|Host|Server)\s*[:=]\s*(.+?)\s*$")


def probe(proxy, host, port):
    """经 proxy 连 host:port —— 真正的隧道探测。

    返回 (kind, detail)；kind ∈ {"data","refused","emptytunnel","error"}
    ★ 探测无效必须自成一类，绝不能和"成功"混用。
    """
    ph, _, pp = proxy.rpartition(":")
    try:
        s = socket.create_connection((ph, int(pp)), timeout=TIMEOUT)
        s.settimeout(TIMEOUT)
        s.sendall(("CONNECT %s:%d HTTP/1.1\r\nHost: %s:%d\r\n\r\n"
                   % (host, port, host, port)).encode())
        buf = b""
        while b"\r\n\r\n" not in buf and len(buf) < 4096:
            d = s.recv(1024)
            if not d:
                break
            buf += d
        if not buf:
            s.close()
            return ("error", "中间层无响应")
        first = buf.split(b"\r\n")[0].decode("latin1", "replace")
        if " 200" not in first:
            s.close()
            return ("refused", first[:80])
        # 隧道建立 → 发请求读真实数据
        try:
            s.sendall(("GET / HTTP/1.1\r\nHost: %s:%d\r\n"
                       "User-Agent: curl/8.0\r\nConnection: close\r\n\r\n"
                       % (host, port)).encode())
        except Exception:
            s.close()
            return ("emptytunnel", "隧道写失败")
        body = b""
        try:
            while len(body) < 8192:
                d = s.recv(2048)
                if not d:
                    break
                body += d
        except socket.timeout:
            pass
        s.close()
        if not body:
            return ("emptytunnel", "CONNECT 200 但无数据")
        return ("data", body.decode("latin1", "replace"))
    except socket.timeout:
        return ("error", "超时")
    except Exception as e:
        return ("error", type(e).__name__)


def fingerprint(body):
    """抽取关键字段做指纹 —— 用于判断不同端口的内容是否来自同一个实体"""
    return {k.lower(): v.strip() for k, v in KEY_FIELDS.findall(body or "")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("host", help="目标 IP 或域名")
    ap.add_argument("--port", type=int, required=True, help="要判定的目标端口")
    ap.add_argument("--control", type=int, action="append", default=[],
                    help="对照组端口(已知不可达)。默认自动用 80 和 9999")
    ap.add_argument("--proxy", action="append", default=[], help="中间层 host:port")
    ap.add_argument("--proxy-file", help="中间层清单文件，每行 host:port")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    if not args.control:
        args.control = [80, 9999]

    proxies = list(args.proxy)
    if args.proxy_file:
        with open(args.proxy_file) as f:
            proxies += [l.strip() for l in f if l.strip() and not l.startswith("#")]
    if not proxies:
        print("[!] 没有指定中间层(host:port) —— 无中间层时直接用 nping/nmap 直连即可，本脚本不适用")
        return 3

    ports = [args.port] + [c for c in args.control if c != args.port]
    print("目标 %s  真实端口 %d  对照组 %s" % (args.host, args.port, args.control))
    print("中间层 %d 个\n" % len(proxies))

    jobs = [(p, pt) for p in proxies for pt in ports]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(lambda a: (a[0], a[1]) + probe(a[0], a[1], a[2]), jobs))

    by_proxy = {}
    for proxy, port, kind, detail in results:
        by_proxy.setdefault(proxy, {})[port] = (kind, detail)

    honest, liars, useless = [], [], []
    for proxy, per_port in by_proxy.items():
        # 死端口是否也"有数据"
        dead_with_data = [pt for pt in args.control
                          if per_port.get(pt, ("", ""))[0] == "data"]
        real = per_port.get(args.port, ("", ""))[0]
        if dead_with_data:
            liars.append((proxy, dead_with_data))
            verdict = "❌ 撒谎（死端口 %s 也返回数据）" % dead_with_data
        elif real == "data":
            honest.append(proxy)
            verdict = "✅ 诚实（死端口无数据，真端口有数据）"
        else:
            useless.append(proxy)
            verdict = "⚠️  无效（无数据，得不出结论）"
        print("── %s" % proxy)
        for pt in ports:
            kind, detail = per_port.get(pt, ("", ""))
            tag = ""
            if kind == "data":
                fp = fingerprint(detail)
                tag = "  " + " | ".join("%s=%s" % (k, v[:40]) for k, v in list(fp.items())[:2])
            print("     %-6d %-13s %s" % (pt, kind, (detail[:50] if kind != "data" else "") + tag))
        print("   → %s\n" % verdict)

    print("═" * 62)
    print("诚实 %d / 撒谎 %d / 无效 %d" % (len(honest), len(liars), len(useless)))
    if liars:
        print("\n撒谎中间层（其全部结论作废）:")
        for p, d in liars:
            print("   %s  死端口 %s 也返回数据" % (p, d))
    if honest:
        print("\n可用中间层: %s" % ", ".join(honest))
    if not honest:
        print("\n[!] 没有任何诚实中间层 —— 跨出口结论作废，改用本机直连取证：")
        print("      nping --tcp -p %d -c 4 <IP>" % args.port)
    if liars and not honest:
        return 2
    if not honest and not liars:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
