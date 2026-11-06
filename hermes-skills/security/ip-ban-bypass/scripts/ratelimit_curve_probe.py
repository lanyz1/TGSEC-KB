#!/usr/bin/env python3
"""限流伪装探测 —— 同一请求连发 N 次,打印「序号 -> 错误码」曲线。

解决的问题:换出口/改头之后,某接口"连试几次都失败,突然某一次返回成功码/errno:0"。
那可能是**真绕过**,也可能是**撞到限流阈值**。本脚本用来区分这两者。

用法:
    python3 ratelimit_curve_probe.py <URL> [N=20] [--ref REF] [--sleep S] [--gap G]

    URL     : 完整目标 URL(含 query string)
    N       : 连发次数,默认 20
    --ref   : Referer 头的值;传空串表示发送 `Referer: `(空值),不传则不发该头
    --gap   : 每次请求间隔秒,默认 1.0
    --sleep : 开跑前先静默等待的秒数(等上一次限流窗口过去),默认 0

判读:
    第 1 次就成功            => 才可能是真绕过
    曲线单调跳变             => 【限流】,不是绕过
    全程同一个码             => 该码即基线响应,与次数无关

**必做对照**:在【两台互不相干的干净出口】上各跑一次。曲线一致 = 结构性行为,
与 Referer/UA/cookie 等变量无关,立刻停止沿该"技巧"投入。
只在同一台机器/session 上跑出的"命中"一律不可信 —— 前序请求会污染后续响应。

实例(2026-09 实测,百度网盘 /pcloud/feed/getsharelist):
    两台独立跳板机各连发 20 次,曲线完全一致:
        1-10  -> {"errno":2,"show_msg":"请求失败"}
        11-20 -> {"errno":0,"error_msg":"too fast"}
    结论:匿名恒被拒,配额约 10 次/窗口。老教程"把 Referer 改掉就通"已失效。
    初判时曾把第 11 次的 errno:0 当成绕过成功,并挂了个 8 分钟轮询白等半小时。
"""
import argparse
import re
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def build_headers(referer):
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if referer is not None:
        h["Referer"] = referer        # 空串 = 发送 `Referer: `
    return h


def one(url, referer):
    req = urllib.request.Request(url, headers=build_headers(referer))
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return f"HTTP{r.status} " + r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        try:
            return f"HTTP{ex.code} " + ex.read().decode("utf-8", "replace")
        except Exception:
            return f"HTTP{ex.code}"
    except Exception as ex:
        return f"ERR {ex!r}"


def fingerprint(body):
    """把响应压成便于比较的短指纹:优先 errno/code/message。"""
    m = re.search(r'"errno"\s*:\s*(-?\d+)', body)
    c = re.search(r'"(?:code|status)"\s*:\s*(-?\d+)', body)
    msg = re.search(r'"(?:error_msg|errmsg|show_msg|message)"\s*:\s*"([^"]*)"', body)
    parts = []
    if m:
        parts.append(f"errno={m.group(1)}")
    elif c:
        parts.append(f"code={c.group(1)}")
    if msg:
        parts.append(f'msg="{msg.group(1)}"')
    if not parts:
        parts.append(body.strip().replace("\n", " ")[:60] or "(empty)")
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("n", nargs="?", type=int, default=20)
    ap.add_argument("--ref", default=None)
    ap.add_argument("--gap", type=float, default=1.0)
    ap.add_argument("--sleep", type=float, default=0.0)
    a = ap.parse_args()

    ref = None if a.ref is None else a.ref
    ref_show = "<不发>" if ref is None else (f'"{ref}"' if ref else "<空值>")
    print(f"### target : {a.url}")
    print(f"### Referer: {ref_show}   N={a.n}  gap={a.gap}s")
    if a.sleep:
        print(f"### 先静默等待 {a.sleep:.0f}s ...")
        time.sleep(a.sleep)

    seq, trans = [], None
    for i in range(1, a.n + 1):
        fp = fingerprint(one(a.url, ref))
        seq.append(fp)
        if trans is None and i > 1 and fp != seq[0]:
            trans = i
        print(f"  #{i:>3} -> {fp[:150]}")
        if i < a.n:
            time.sleep(a.gap)

    print("\n### 判读")
    uniq = []
    for s in seq:
        if s not in uniq:
            uniq.append(s)
    if len(uniq) == 1:
        print(f"  全程同一个响应 {uniq[0][:70]} —— 与请求次数无关,该码即基线响应。")
    else:
        print(f"  响应在 #{trans} 发生变化,共 {len(uniq)} 种:")
        for u in uniq:
            print(f"    - {u[:90]}")
        print("  ⚠️ 单调跳变 = 【限流】,不代表绕过。必须在另一台干净出口复跑对照:")
        print("     曲线一致  -> 结构性行为,与 Referer/UA/cookie 等变量无关,停止沿该技巧投入")
        print("     曲线不同  -> 继续做变量隔离,别急着下结论")


if __name__ == "__main__":
    sys.exit(main())
