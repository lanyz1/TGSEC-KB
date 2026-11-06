#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skew_probe.py -- 测目标服务器时钟偏差, 并给出 TOTP 候选码。

为什么需要它: TOTP 30s 一步, 本机钟偏 >±60s 时怎么算都错; HMAC+timestamp 闸同理。
被 WAF 挑战 / 403 / 302 的响应一样带 Date 头, 所以状态码不影响测量。

用法:
  python3 skew_probe.py https://target/api/health
  python3 skew_probe.py https://target/index --host-compare www.baidu.com --secret JBSWY3DPEHPK3PXP
  python3 skew_probe.py https://target/ --proxy socks5h://127.0.0.1:1086 --period 30 --digits 6

输出: 每台主机 skew(秒) + 本机偏/目标偏判定 + delta in {-1,0,1,2} 的候选动态码与剩余有效期。
"""
import argparse, base64, email.utils as eu, hashlib, hmac, statistics, struct, sys, time

import requests


def parse_date(hdr):
    if not hdr:
        return None
    try:
        return eu.parsedate_to_datetime(hdr).timestamp()
    except Exception:
        return None


def probe(url, proxy=None, timeout=20):
    """返回 (skew秒, http状态或错误)。skew = 服务端钟 - 本机钟。"""
    s = requests.Session()
    s.trust_env = False  # 避免系统代理静默接管: 否则测到的是代理的钟
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    t0 = time.time()
    try:
        r = s.get(url, timeout=timeout, verify=False, allow_redirects=False)
    except Exception as e:
        return None, "ERR %s" % e
    half = (time.time() - t0) / 2.0
    sd = parse_date(r.headers.get("date"))
    if sd is None:
        return None, "%s (no Date header)" % r.status_code
    return (sd - (t0 + half)), r.status_code


def totp(secret_b32, epoch, period=30, digits=6, algo="sha1"):
    pad = "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(secret_b32.upper() + pad)
    ctr = struct.pack(">Q", int(epoch) // period)
    mac = hmac.new(key, ctr, getattr(hashlib, algo)).digest()
    off = mac[-1] & 0x0F
    code = (struct.unpack(">I", mac[off:off + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", help="目标上的任一路径(健康检查/静态资源即可)")
    ap.add_argument("--host-compare", action="append", default=[],
                    help="对照主机(可多次)用来判定本机钟坏还是目标钟坏, 建议含一个无关大站")
    ap.add_argument("--proxy", default=None, help="如 socks5h://127.0.0.1:1086")
    ap.add_argument("--secret", default=None, help="base32 TOTP 密钥; 给了就打印候选码")
    ap.add_argument("--period", type=int, default=30)
    ap.add_argument("--digits", type=int, default=6)
    ap.add_argument("--algo", default="sha1", choices=["sha1", "sha256", "sha512"])
    ap.add_argument("--deltas", default="-1,0,1,2", help="步长偏移扫描顺序(先小后大)")
    a = ap.parse_args()

    rows = []
    for u in [a.url] + [("https://%s/" % h if "://" not in h else h) for h in a.host_compare]:
        skew, st = probe(u, a.proxy)
        rows.append((u, skew, st))
        print("%-52s %-22s %s" % (u, ("skew=%+.2fs" % skew) if skew is not None else "skew=N/A", st))

    if all(s is None for _, s, _ in rows):
        print("\n[!] 全部主机未回 Date 头 -> 改用响应体 serverTime/timestamp, 或解 JWT 的 iat/exp 做基准")
        return 1

    tgt = rows[0][1]
    others = [s for _, s, _ in rows[1:] if s is not None]
    print("\n目标 skew = %s" % (("%+.2fs" % tgt) if tgt is not None else "N/A"))
    if tgt is not None and others:
        med = statistics.median(others)
        print("对照主机中位 skew = %+.2fs" % med)
        if abs(med - tgt) < 5:
            print("判定: 各主机一致 -> 本机钟偏, 按目标钟重算所有时间敏感凭据")
        else:
            print("判定: 只有目标偏离 -> 目标自身钟偏, 仍按目标钟重算")
    print("建议 delta 扫描顺序: %s (命中即停; 不要扫 ±960 的时区假设)" % a.deltas)

    if a.secret and tgt is not None:
        print("\n候选动态码 (period=%ds digits=%d algo=%s):" % (a.period, a.digits, a.algo))
        for d in [int(x) for x in a.deltas.split(",")]:
            now_srv = time.time() + tgt
            step = int(now_srv / a.period) + d
            code = totp(a.secret, step * a.period, a.period, a.digits, a.algo)
            print("  delta=%+d  code=%s  (该步还剩 %.1fs)" % (d, code, a.period - (now_srv % a.period)))
        print("\n[!] 对齐后立刻重试; 30s 边界会抖动 -> 连打 2-3 次比只打一次稳")
    return 0


if __name__ == "__main__":
    sys.exit(main())
