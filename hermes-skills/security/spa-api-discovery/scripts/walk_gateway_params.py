#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网关必填参数链 oracle 走链器 + 未授权面分档器
用途:自研 API 网关(ct/ts/si/vn 这类"客户端参数")不知道要传什么时,**让报错告诉你**。

配套文档:spa-api-discovery/references/gateway-param-chain-oracle.md
实战:2026-09 央选信息族(chaoyongbushou.com / supsaas.com / sviptrader.com)

用法示例:
    python walk_gateway_params.py --base https://api.example.com --path / --seed ct=h5 --seed ts=SEC
    python walk_gateway_params.py --base https://api.example.com --triage        # 分档模式

设计要点(都是踩过的坑):
  * 报错里的参数名要按 **小写** 再试一遍(PHP $_GET 大小写敏感;报 Ts/Si,实际只认 ts/si)
  * 缺参数报 "X不能为空";值不合法报别的(如"非法时间戳") ⇒ 进入值校验阶段就用矩阵逐个试格式
  * 一次只改一个变量;看到"通过了"先怀疑是不是路径没命中、中间件没跑
  * 频率:默认 1.2s/请求,串行。**不用于凭据爆破**,只用于契约发现
"""
import argparse
import re
import subprocess
import sys
import time

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.42")


def curl(url, qs=None, method="GET", headers=None, body=None, timeout=25):
    """零依赖 HTTP;响应直接返回文本(建议调用方落文件后再读,HTTP/2 分块易抓空)。"""
    a = ["curl", "-sS", "-k", "--max-time", str(timeout), "-A", UA]
    for h in (headers or []):
        a += ["-H", h]
    if method == "GET":
        a.append("--get")
        for k, v in (qs or []):
            a += ["--data-urlencode", "%s=%s" % (k, v)]
    else:
        a += ["-X", method]
        if body is not None:
            a += ["--data-raw", body]
    a.append(url)
    p = subprocess.run(a, capture_output=True, timeout=timeout + 5)
    return (p.stdout or b"").decode("utf-8", "ignore")


def walk(base, path, seeds, max_steps=12, delay=1.2, headers=None):
    """沿"X不能为空"链逐个补参数,直到不再报缺。返回 (最终参数, 最后响应)。"""
    d = dict(seeds)
    if d.get("ts") == "SEC":
        d["ts"] = str(int(time.time()))
    last = ""
    seen = []
    for step in range(max_steps):
        r = curl(base.rstrip("/") + path, qs=list(d.items()), headers=headers)
        last = r
        m = re.search(r'"message"\s*:\s*"([A-Za-z0-9_]+)不能为空"', r)
        if not m:
            print("[+] 链走完(不再报缺),最后响应:" + re.sub(r"\s+", " ", r)[:300])
            return d, last
        raw = m.group(1)
        low = raw.lower()
        print("[%02d] 缺 %-8s -> 补 %s=1" % (step + 1, raw, low))
        if low in seen:
            print("[!] %s 补过还是报缺 ⇒ 大小写/值的形态问题,改试值形态矩阵" % low)
            return d, last
        seen.append(low)
        d[low] = "1"
        time.sleep(delay)
    return d, last


def value_matrix(base, path, params, key, values, headers=None, delay=1.0):
    """参数名定下来后,试值的形态(时间戳秒/毫秒/YmdHis、签名长度等),看报错是否前进。"""
    for v in values:
        qs = [(k, (v if k == key else val)) for k, val in (params or {}).items()]
        if not any(k == key for k, _ in qs):
            qs.append((key, v))
        r = curl(base.rstrip("/") + path, qs=qs, headers=headers)
        print("   %-14s -> %s" % (key + "=" + str(v), re.sub(r"\s+", " ", r)[:180]))
        time.sleep(delay)


# ---- 未授权面分档判据(照抄即可,详见 references/gateway-param-chain-oracle.md)----
TRIAGE = [
    (r'"error_msg"\s*:\s*"404 Route Not Found"', "网关无此服务前缀"),
    (r'"code"\s*:\s*"?10404"?', "服务内路径不存在(前缀对)"),
    (r'"code"\s*:\s*401', "路径存在,要 token"),
    (r'"code"\s*:\s*422.*参数缺失', "路径存在且免登录,只缺参数 ★"),
    (r'不能为空', "路径存在且免登录,只缺该字段 ★"),
    (r'"code"\s*:\s*400.*请求方式不正确', "路径存在,换方法"),
    (r'"status"\s*:\s*405', "路径存在,换方法"),
    (r'"success"\s*:\s*true', "*** 直出数据 ***"),
]


def triage(base, paths, headers=None, delay=1.2):
    for p in paths:
        r = curl(base.rstrip("/") + p, headers=headers)
        tag = "?"
        for pat, desc in TRIAGE:
            if re.search(pat, r, re.S):
                tag = desc
                break
        print("%-70s %-28s %s" % (p, tag, re.sub(r"\s+", " ", r)[:120]))
        time.sleep(delay)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--path", default="/")
    ap.add_argument("--seed", action="append", default=[], help="如 ct=h5 (可多次)")
    ap.add_argument("--header", action="append", default=[],
                    help="如 'applicationId: 3'(前端拦截器里扒到的头契约)")
    ap.add_argument("--triage", action="store_true", help="分档模式:逐个打路径判未授权面")
    ap.add_argument("--paths-file", help="分档模式的路径清单(每行一条)")
    ap.add_argument("--key", help="值矩阵:参数名")
    ap.add_argument("--values", help="值矩阵:逗号分隔候选值")
    a = ap.parse_args()

    seeds = []
    for s in a.seed:
        k, _, v = s.partition("=")
        seeds.append((k, v))

    if a.triage:
        ps = [l.strip() for l in open(a.paths_file, encoding="utf-8") if l.strip()] if a.paths_file else [a.path]
        triage(a.base, ps, headers=a.header)
        return

    params, _ = walk(a.base, a.path, seeds, headers=a.header)
    if a.key and a.values:
        print("\n== 值形态矩阵 ==")
        value_matrix(a.base, a.path, params, a.key, a.values.split(","), headers=a.header)


if __name__ == "__main__":
    sys.exit(main())
