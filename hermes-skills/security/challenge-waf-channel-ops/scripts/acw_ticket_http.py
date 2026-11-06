#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""acw_ticket_http.py —— 挑战型 WAF（ACW 回跳票）的纯 HTTP 回放器

用途：把「真浏览器铸出来的票」搬到纯 HTTP 客户端批量直发，替代 6-7s/条的导航读。

铸票（浏览器侧，每 path 一次；导航恒 GET => 只能铸 GET 的票）：
  1) 用真浏览器打开 https://<host><path>
  2) 等质询解完（页内出现真内容 / 真 JSON，而不是 <textarea id="renderData">）
  3) 读 location.href，取 encode__1715= / md5__1713= / refer__1720= 的完整值 = 该 path 的票
  4) 写进 pairs 文件：每行 `path <TAB> 票 <TAB> method`（method 省略 = GET）

用法：
  python acw_ticket_http.py --host https://int3.example.com --pairs pairs.txt
  python acw_ticket_http.py --host https://h --pairs pairs.txt --only-method GET --sleep 1

铁律（实测）：
  * 票与「path + method」绑定：同 path 同 method 可重复使用；跨 path 或 GET 票发 POST => 挑战页。
  * 票不依赖 cookie / 指纹头 / 出口 IP => 无 cookie 的裸 requests 也能直通。
  * 串行 + 间隔：连发自造请求会触发阶梯处罚（keepper 惩罚态 -> 空体 -> 连接 reset）。
判读：
  真业务响应 = ok；body 含 renderData / _waf_ 或长度 ≈110310 = ACW 挑战（票对该 path+method 不适用，需重铸）。
"""
import argparse
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

HDR = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=utf-8",
}
TICKET_PARAMS = ("encode__1715", "md5__1713", "refer__1720", "decode__1714")


def load_pairs(fp):
    """每行: path<TAB>票<TAB>method ；# 开头与空行跳过。"""
    out = []
    for ln in open(fp, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = [p.strip() for p in ln.split("\t")]
        path = parts[0]
        ticket = parts[1] if len(parts) > 1 else ""
        method = (parts[2] if len(parts) > 2 else "GET").upper()
        out.append((method, path, ticket))
    return out


def is_challenge(r):
    """挑战页是 200：判成功看 body 特征与长度，不看状态码。"""
    t = r.text
    return ("renderData" in t) or ("_waf_" in t) or (len(t) > 60000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="如 https://int3.xwallet801.com")
    ap.add_argument("--pairs", required=True, help="每行: path<TAB>票<TAB>method(可省,默认GET)")
    ap.add_argument("--param", default="encode__1715", help="票参数名（默认 encode__1715）")
    ap.add_argument("--post-body", default="{}", help="POST 的 body（POST 的票须各自铸出）")
    ap.add_argument("--only-method", default="", help="只发某个方法（如 GET）")
    ap.add_argument("--sleep", type=float, default=0.5, help="串行间隔秒；别连发")
    ap.add_argument("--head", type=int, default=160, help="body 预览字符数")
    a = ap.parse_args()

    s = requests.Session()
    s.trust_env = False  # 别让本机系统代理静默接管；要用代理请显式挂 proxies
    ok = bad = err = 0

    for method, path, ticket in load_pairs(a.pairs):
        if a.only_method and method != a.only_method.upper():
            continue
        url = a.host + path
        if ticket:
            url += ("&" if "?" in path else "?") + a.param + "=" + ticket
        try:
            if method == "GET":
                r = s.get(url, headers=HDR, timeout=25, verify=False)
            else:
                r = s.post(url, data=a.post_body, headers=HDR, timeout=25, verify=False)
            tag = "ACW" if is_challenge(r) else "ok"
            if is_challenge(r):
                bad += 1
            else:
                ok += 1
            body = r.text.replace("\n", " ").replace("\r", " ")[: a.head]
            print("  %-5s %-38s st=%-4s %-4s len=%-7s %s"
                  % (method, path[:38], r.status_code, tag, len(r.text), body))
        except Exception as e:  # noqa: BLE001
            err += 1
            print("  %-5s %-38s ERR %s" % (method, path[:38], str(e)[:90]))
        time.sleep(a.sleep)

    print("\n  ok=%d  ACW=%d  ERR=%d" % (ok, bad, err))
    print("  ACW => 票对该 path/method 不适用：重铸，或该路径只放行另一种请求方法。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
