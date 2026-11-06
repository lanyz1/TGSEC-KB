# -*- coding: utf-8 -*-
# probe_xa79_channels.py — 西安79次(XA79) 审核补齐三探针 (2026-09-12 编制, 首发前未运行)
# 用法(主服): python3 /tmp/probe_xa79_channels.py ; 输出 /tmp/r11_out.txt
# A. startingbiddetailspackage / startingmaterialdetails 按项目ID直查(声明参数 id — 此前从未用对)
# B. biddingandsellingsupplier 名册带日期窗(声明 startDate/endDate)
# C. bid_package_bidder_business23 多窗(全窗只校验 totalSize/样例; 全表负结果已档, 勿重扫)
import json, ssl, socket, urllib.request, urllib.error, time
socket.setdefaulttimeout(22)
CX = ssl.create_default_context(); CX.check_hostname = False; CX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
BASE = "https://cg.95306.cn/proxy/dataplatform/api/findList"
PID = "3a5a0784-7bd6-4ce5-a855-dc56c23026fe"  # 西安79次; 通用化时替换为目标项目ID
OUT = open("/tmp/r11_out.txt", "w")

def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True); OUT.write(s + "\n"); OUT.flush()

def fl(fid, params=None, page=1, size=20, condition=None, appid="system"):
    body = {"funcId": fid, "appId": appid, "pageNum": page, "pageSize": size}
    if params is not None: body["params"] = params
    if condition is not None: body["condition"] = condition
    req = urllib.request.Request(BASE, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    try:
        raw = urllib.request.urlopen(req, timeout=20, context=CX).read().decode()
        return json.loads(raw)
    except urllib.error.HTTPError as e:
        return {"code": "HTTP%d" % e.code, "msg": str(e.read()[:120])}
    except Exception as e:
        return {"code": "ERR", "msg": str(e)[:120]}

def tot(j):
    t = j.get("totalSize")
    return t if t is not None else len(j.get("data") or [])

P("===== A. starting by id =====")
for fid in ("startingbiddetailspackage", "startingmaterialdetails"):
    j = fl(fid, params=[{"key": "id", "value": PID}], size=50)
    rows = j.get("data") or []
    P("A", fid, "code", j.get("code"), "tot", tot(j), "rows", len(rows), "msg", str(j.get("msg"))[:60])
    for r in rows[:16]:
        P("   ", json.dumps(r, ensure_ascii=False)[:360])

P("===== B. roster window =====")
for w in (("2026-08-20", "2026-09-12"),):
    j = fl("biddingandsellingsupplier",
           params=[{"key": "startDate", "value": w[0]}, {"key": "endDate", "value": w[1]}], size=5)
    rows = j.get("data") or []
    P("B", w, "code", j.get("code"), "tot", tot(j))
    if rows:
        P("   S", json.dumps(rows[0], ensure_ascii=False)[:340])

P("===== C. bidder windows =====")
for w in (("0", "2099-12-31 00:00:00"), ("2026-08-01 00:00:00", "2026-09-12 23:59:59"),
          ("2026-08-25 00:00:00", "2026-09-05 23:59:59"), ("2026-09-01 00:00:00", "2026-09-12 23:59:59")):
    j = fl("bid_package_bidder_business23",
           params=[{"key": "start_time", "value": w[0]}, {"key": "end_time", "value": w[1]}], size=3)
    rows = j.get("data") or []
    P("C", w[0][:16], w[1][:16], "code", j.get("code"), "tot", tot(j))
    if rows:
        P("   S", json.dumps(rows[0], ensure_ascii=False)[:340])
P("PROBE_DONE — 发回 /tmp/r11_out.txt, 结论回填 references/2026-09-12-param-form-corrections-and-new-channel-leads.md")
