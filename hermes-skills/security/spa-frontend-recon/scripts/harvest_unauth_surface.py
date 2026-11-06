#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harvest_unauth_surface.py —— 「未授权面」双扫 + 收割器(可复用)

用途:SPA/多端产品的 API 是“全局登录过滤器 + 白名单”模型时,
      把前端包里抠出的**全部**路径逐条双扫(不带 cookie / 带 cookie),
      按响应签名分类,只落地“真有数据”的接口;并顺带检测**API 返回的对象存储直链**是否可匿名下载。

配套方法论:../references/api-inventory-dual-sweep-and-content-assets.md

用法:
  # 1) 从文件读路径清单(每行一个 /path),双扫
  python3 harvest_unauth_surface.py --host https://api.example.com --paths endpoints.txt \
      --out ./harvest [--cookie-jar ./jar.txt]
  # 2) 只扫“已知未授权”的固定清单(快速收割)
  python3 harvest_unauth_surface.py --host https://api.example.com --known --out ./harvest
  # 3) 顺带把所有响应里出现的对象存储直链 HEAD 一遍(看能否匿名下载)
  python3 harvest_unauth_surface.py --host ... --known --out ./harvest --objects

设计约束(按纪律来):
  * 只做 GET;不提交写操作、不上传、不修改数据
  * 默认 1.3s 间隔;识别到账号级限流(如 code=-100102 / “请求过于频繁”)立刻暂停并冷却
  * .raw 保原始证据,加密响应另存 .dec 明文(openssl 解密,零第三方依赖)
"""
import argparse, base64, binascii, json, os, re, subprocess, sys, time

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# 常见的“被登录过滤器拦住”的响应特征(按目标实测调整)
LOGIN_SENTINELS = ("登录状态已失效", "请重新登录", "未登录", "请登录")
# 常见的限流特征
LIMIT_SENTINELS = ("请求过于频繁", "-100102", "too many requests", "rate limit")

# 未授权接口的固定清单示例(实战替换为你自己扫出来的)
KNOWN_UNAUTH = [
    "/search/userDefault", "/work/notice", "/work/config",
    "/common/allCid", "/common/dyCid", "/common/area",
]


def curl(url, cookie_jar=None, head=False, timeout=25):
    cmd = ["curl", "-sS", "-k", "--max-time", str(timeout), "-A", UA]
    if head:
        cmd.append("-I")
    if cookie_jar:
        cmd += ["-c", cookie_jar, "-b", cookie_jar]
    cmd.append(url)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 8).stdout or ""
    except Exception:
        return ""


def aes_ecb_decrypt(b64, key):
    """零依赖 AES-128-ECB/Pkcs7 解密(用系统 openssl)"""
    try:
        ct = base64.b64decode(b64.replace(" ", "+") + "=" * (-len(b64) % 4))
    except Exception:
        return None
    open("/tmp/_hs_ct.bin", "wb").write(ct)
    subprocess.run(["openssl", "enc", "-d", "-aes-128-ecb",
                    "-K", binascii.hexlify(key.encode()).decode(),
                    "-nopad", "-in", "/tmp/_hs_ct.bin", "-out", "/tmp/_hs_pt.bin"],
                   capture_output=True)
    if not os.path.exists("/tmp/_hs_pt.bin"):
        return None
    b = open("/tmp/_hs_pt.bin", "rb").read()
    if not b:
        return None
    if 1 <= b[-1] <= 16 and b.endswith(bytes([b[-1]]) * b[-1]):
        b = b[:-b[-1]]
    return b.decode("utf-8", "replace")


def classify(body, keys):
    """返回 (类别, 说明, 明文对象)"""
    if not body:
        return "EMPTY", "无响应", None
    low = body[:400]
    for s in LIMIT_SENTINELS:
        if s in low:
            return "RATELIMIT", s, None
    for s in LOGIN_SENTINELS:
        if s in low:
            return "LOGIN-GATE", s, None
    if "Not Found" in low and "404" in low[:80]:
        return "404", "", None
    try:
        j = json.loads(body)
    except Exception:
        return ("RAW", "非 JSON(可能是文件/HTML)", body[:200])
    v = j.get("data")
    if isinstance(v, str) and len(v) > 40:
        for k in keys:
            g = aes_ecb_decrypt(v, k)
            if g and g.strip()[:1] in "{[":
                try:
                    return "DATA", "解密(%s)" % k, json.loads(g)
                except Exception:
                    return "DATA", "解密但非 JSON", g
        return "ENCRYPTED?", "解密失败(密钥不在候选集)", None
    if isinstance(v, (list, dict)) and v:
        return "DATA", "明文", v
    if j.get("code") in (500,) or "系统异常" in str(j.get("message")):
        return "REACHABLE-NO-PARAM", "已过鉴权、缺参数", None
    if isinstance(v, dict) and "appId" in v:
        return "CATCH-ALL", "兜底路由(不存在)", None
    return "EMPTY-BODY", str(j)[:80], None


def find_object_urls(text):
    return sorted(set(re.findall(
        r'https?://[A-Za-z0-9._-]*(?:cos\.[a-z0-9-]+\.myqcloud\.com|oss-[a-z0-9-]+\.aliyuncs\.com|'
        r'storage\.googleapis\.com|s3[.-][a-z0-9-]+\.amazonaws\.com)[^\s"\'<>\\]*', text)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="API 基址,如 https://api.example.com")
    ap.add_argument("--paths", help="路径清单文件(每行一个 /path)")
    ap.add_argument("--known", action="store_true", help="只扫内置的已知未授权清单")
    ap.add_argument("--cookie-jar", help="会话 cookie 文件(用于双扫的 AUTH 轮)")
    ap.add_argument("--keys", default="", help="候选 AES 密钥,逗号分隔(前端硬编码)")
    ap.add_argument("--out", default="./harvest")
    ap.add_argument("--sleep", type=float, default=1.3)
    ap.add_argument("--objects", action="store_true", help="额外 HEAD 响应里出现的对象存储直链")
    a = ap.parse_args()

    keys = [k for k in a.keys.split(",") if k]
    paths = list(KNOWN_UNAUTH) if a.known else []
    if a.paths:
        paths += [l.strip() for l in open(a.paths, encoding="utf-8") if l.strip().startswith("/")]
    paths = list(dict.fromkeys(paths))
    if not paths:
        ap.error("需要 --paths 或 --known")

    os.makedirs(a.out, exist_ok=True)
    os.makedirs(os.path.join(a.out, "dec"), exist_ok=True)
    rows, obj_urls = [], set()
    print("[*] 双扫 %d 条路径 -> %s" % (len(paths), a.out))

    for p in paths:
        for tag, jar in (("UNAUTH", None), ("AUTH", a.cookie_jar)):
            if tag == "AUTH" and not a.cookie_jar:
                continue
            body = curl(a.host + p, cookie_jar=jar)
            time.sleep(a.sleep)
            kind, note, obj = classify(body, keys)
            if kind == "RATELIMIT":
                print("   !! 触发限流(%s) —— 冷却 120s" % note)
                time.sleep(120)
                body = curl(a.host + p, cookie_jar=jar)
                kind, note, obj = classify(body, keys)
            if kind not in ("DATA", "REACHABLE-NO-PARAM"):
                continue
            slug = re.sub(r"[^A-Za-z0-9]", "_", p).strip("_")
            open(os.path.join(a.out, slug + ".raw"), "w", encoding="utf-8").write(body)
            n = 0
            if isinstance(obj, (list, dict)):
                n = len(obj)
                open(os.path.join(a.out, "dec", slug + ".dec"), "w", encoding="utf-8").write(
                    json.dumps(obj, ensure_ascii=False))
            rows.append((tag, p, len(body), n, note))
            print("   %-6s %-34s %9d B  条=%-5s %s" % (tag, p, len(body), n, note))
            obj_urls |= set(find_object_urls(body))

    # 对象存储直链匿名下载检测(内容资产)
    if a.objects and obj_urls:
        print("\n[*] 检测 %d 个对象存储直链能否匿名下载" % len(obj_urls))
        with open(os.path.join(a.out, "OBJECTS.tsv"), "w", encoding="utf-8") as f:
            for u in sorted(obj_urls):
                h = curl(u, head=True)
                code = re.search(r"HTTP/\S+\s+(\d+)", h)
                ln = re.search(r"(?i)content-length:\s*(\d+)", h)
                ct = re.search(r"(?i)content-type:\s*(\S+)", h)
                f.write("%s\t%s\t%s\t%s\n" % (u, code.group(1) if code else "?",
                                              ln.group(1) if ln else "", ct.group(1) if ct else ""))
                print("   %s %-10s %s" % (code.group(1) if code else "?", ln.group(1) if ln else "", u[:96]))
                time.sleep(0.6)

    with open(os.path.join(a.out, "INVENTORY.txt"), "w", encoding="utf-8") as f:
        for tag, p, sz, n, note in rows:
            f.write("%-6s %-34s %9d %6s %s\n" % (tag, p, sz, n, note))
    print("\n[*] 命中 %d 条;总字节 %d;产物:INVENTORY.txt%s" % (
        len(rows), sum(r[2] for r in rows), " + OBJECTS.tsv" if a.objects else ""))


if __name__ == "__main__":
    main()
