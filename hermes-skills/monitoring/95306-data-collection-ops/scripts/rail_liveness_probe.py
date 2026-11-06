#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rail 票龄→token 存活率探针 + 缺口账号活票盯守（**只读**；在采集机上跑）

用途
  ① 实测 token 寿命分布：把 rail 最近窗口里的票按「票龄」分桶逐票调 user/info，
     得「票龄 → 存活率」曲线 ⇒ 判定补采轮次（30 分钟）够不够。
  ② 盯守缺口账号：缺口账号一旦出现在窗口里就高亮它的 token 存活情况（★HOT），
     用于验证「登录后 ≤30 分钟内接住」是否成立。

用法（采集机上；探针属只读，免同意）
  BK_CTX=/tmp/bk8_bf_ctx.json python3 -u rail_liveness_probe.py
  环境变量：GW_N=16(轮数) GW_SLEEP=150(间隔秒) GW_WIN=45(窗宽分钟)
            GW_TOPN=8(每轮探活上限) GW_FORCE=账号,逗号分隔(默认取 ctx.force_accts)
输出：/tmp/gapwatch.jsonl（每轮一行 JSON）+ stdout 汇总

纪律（都是踩过的坑，别改回去）
  - `rail_rows()` 返回 **(rows, fail) 元组**，必须解包；直接迭代报
    `AttributeError: 'list' object has no attribute 'get'`。
  - 必须**显式加载生产文件** `/tmp/bk_worker.py`；采集机上 `import master.bk_worker`
    会落到 `/opt/v6/current` **旧树** ⇒ 新字段恒为空（假象，如 force_accts=0）。
  - 时间串**必须带秒**（`%Y-%m-%d %H:%M:%S`），缺秒平台静默返回 0 行、不报错。
  - 票龄方向：`age = now - login_time`（算反了会得负值）。
  - 探针只读、低频（每轮 ≤ GW_TOPN+3 个请求）；避开轮次高峰（:15/:45）少抢资源。
"""
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timedelta


def log(*a):
    print(*a, flush=True)


def load_worker():
    """返回 (Worker, 文件路径)。采集机上优先生产文件 /tmp/bk_worker.py。"""
    p = "/tmp/bk_worker.py"
    if os.path.isfile(p):
        spec = importlib.util.spec_from_file_location("prod_bkw", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        if hasattr(m, "Worker"):
            return m.Worker, p
    sys.path.insert(0, "/opt/v6")
    from master.bk_worker import Worker  # 主控侧回退
    return Worker, "/opt/v6/master/bk_worker.py"


def user_info(w, tok):
    """容错调 user/info：各版本封装方法名/参数形状不一，逐个试。"""
    for name in ("get", "post"):
        f = getattr(w, name, None)
        if not callable(f):
            continue
        for args in (("user/info", tok), ("user/info", {"token": tok})):
            try:
                j = f(*args)
            except Exception:
                continue
            if isinstance(j, dict) and ("code" in j or "data" in j):
                return j
    return None


def probe_one(w, tok):
    """返回 (code, 企业名)。拿到企业名 = 活票；死票实测返回 code=100 系统服务异常。"""
    j = user_info(w, tok)
    if not isinstance(j, dict):
        return ("ERR", "")
    data = j.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    return (j.get("code"), data.get("dwhz") or data.get("qymc") or "")


def main():
    Worker, src = load_worker()
    ctx_path = os.environ.get("BK_CTX", "/tmp/bk8_bf_ctx.json")
    with open(ctx_path, encoding="utf-8") as fh:
        ctx = json.load(fh)
    force = set(x.strip() for x in os.environ.get(
        "GW_FORCE", ",".join(ctx.get("force_accts") or [])).split(",") if x.strip())
    N = int(os.environ.get("GW_N", "16"))
    SLEEP = int(os.environ.get("GW_SLEEP", "150"))
    WIN = int(os.environ.get("GW_WIN", "45"))
    TOPN = int(os.environ.get("GW_TOPN", "8"))
    log("### Worker=%s" % src)
    log("### ctx=%s force=%d %s" % (ctx_path, len(force), sorted(force)))
    out = open("/tmp/gapwatch.jsonl", "a", encoding="utf-8")
    buckets = {}          # 票龄桶 -> [总票数, 活票数]
    for i in range(1, N + 1):
        now = datetime.utcnow()
        st = (now - timedelta(minutes=WIN, hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        en = (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        w = Worker(ctx, 0)
        try:
            w.rail_pages, w.rail_size = 3, 500
        except Exception:
            pass
        try:
            rows, fail = w.rail_rows(st, en)          # ★ 元组，先解包
        except Exception as exc:                       # noqa: BLE001
            log("[%2d/%d] rail 异常: %s" % (i, N, exc))
            if i < N:
                time.sleep(SLEEP)
            continue
        latest = {}                                    # 账号 -> (login_time, token)
        for r in rows or []:
            u = str(r.get("userid") or "")
            if not u or str(r.get("user_type")) not in ("03", "3"):
                continue
            lt = str(r.get("login_time") or "")
            if lt > latest.get(u, ("", ""))[0]:
                latest[u] = (lt, str(r.get("token") or ""))
        pick = sorted(latest.items(), key=lambda kv: kv[1][0], reverse=True)[:TOPN]
        picked = {u for u, _ in pick}
        for u in force:                                # 缺口账号无论多老都必探
            if u in latest and u not in picked:
                pick.append((u, latest[u]))
        log("[%2d/%d] rows=%d fail=%s 窗=%s~%s" % (i, N, len(rows or []), fail, st, en))
        for u, (lt, tok) in pick:
            age = -1
            try:
                age = int(((now + timedelta(hours=8))
                           - datetime.strptime(lt, "%Y-%m-%d %H:%M:%S")).total_seconds() // 60)
            except Exception:
                pass
            code, nm = probe_one(w, tok)
            alive = bool(nm)
            if age >= 0:
                b = buckets.setdefault((age // 30) * 30, [0, 0])
                b[0] += 1
                b[1] += int(alive)
            hot = "★HOT" if u in force else "    "
            log("        %s %-22s 票龄=%s分钟 code=%-5s 存活=%s 企业=%s"
                % (hot, u, age, code, alive, nm))
            out.write(json.dumps({"t": now.isoformat(), "u": u, "lt": lt, "age": age,
                                  "code": code, "name": nm, "force": u in force},
                                 ensure_ascii=False) + "\n")
        out.flush()
        if i < N:
            time.sleep(SLEEP)
    log("=== 票龄→存活率（本机实测）===")
    for k in sorted(buckets):
        tot, ok = buckets[k]
        log("  %3d~%3d 分钟: %d 票 / 活 %d (%.0f%%)" % (k, k + 30, tot, ok, 100.0 * ok / max(tot, 1)))
    out.close()


if __name__ == "__main__":
    main()
