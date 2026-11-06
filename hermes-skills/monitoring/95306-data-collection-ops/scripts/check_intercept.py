#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""95306 拦截度/覆盖度 一键实测(本机运行; 本地→主服 中转)
用法: python scripts/check_intercept.py
输出: ① drain 监控窗尾部 ② 覆盖基准(ent_coverage/audit_changed/merge) ③ 23家精确缺漏 + 全池新鲜回写
口径与回答框架详见 references/intercept-coverage-measurement.md (勿背旧数, 现场拉)。
"""
import json, os, base64

KEY = os.path.expanduser("~/.ssh/v6_master_key")
M_HOST, M_PORT, M_USER = "128.241.245.73", 12971, "root"

NAMES23 = ["西安融旺商贸有限公司", "西安佳誉环保科技有限公司", "郑州荣法废旧物资有限公司",
    "郑州硕丰废旧物资回收有限公司", "甘肃鑫若芯建筑工程有限公司", "甘肃寻梦者再生资源回收有限公司",
    "淮安泽峰再生资源回收有限公司", "临沂金盛源五金工具有限公司", "临沂源生金属材料有限公司",
    "西安恒丰盛达商贸有限公司", "南京东创金属有限公司", "济南东照盛金属材料有限公司",
    "环宇（临汾）特种材料有限公司", "南京市中亚商贸有限公司", "张掖市荣华再生资源回收有限责任公司",
    "河南崇锐贸易有限公司", "乌鲁木齐欣和庆商贸有限公司", "陕西晨易阳商贸有限公司",
    "新邵县鑫泰再生资源有限公司", "成都顺安永达再生物资回收有限公司", "四川旭华永邦科技有限公司",
    "天津市玉新生再生资源回收有限公司", "四川德阳旌兴废旧物资有限公司"]

PAYLOAD = r'''
import json, glob, os, time, datetime
NAMES = %s
def out(s): print(s, flush=True)
# A. 覆盖基准
for f in ["/opt/v6/ent_coverage.json", "/data_pool/audit_changed.json", "/data_pool/biz_budget.json"]:
    try:
        st = os.stat(f); out("A %s size=%d mtime=%s" % (f, st.st_size, time.strftime("%m-%d %H:%M", time.localtime(st.st_mtime))))
    except Exception:
        out("A %s MISS" % f)
try:
    out("A ent_coverage keys=%d" % len(json.load(open("/opt/v6/ent_coverage.json", encoding="utf-8"))))
except Exception: pass
try:
    ac = json.load(open("/data_pool/audit_changed.json", encoding="utf-8"))
    out("A audit_changed ts=%s n=%d" % (ac.get("ts"), len(ac.get("projects") or [])))
except Exception: pass
# B. merge 尾
try:
    for l in open("/tmp/v6_merge.log", encoding="utf-8", errors="replace").read().splitlines()[-4:]:
        out("B " + l[:160])
except Exception: pass
# C. 23家 精确缺漏(miss_map 配对) + 全池新鲜 backfill 笔数
try:
    mm = (json.load(open("/tmp/bk8_ctx.json", encoding="utf-8")).get("miss_map") or {})
except Exception:
    mm = {}; out("C bk8_ctx MISS")
tot = rec = 0; still = []
for n in NAMES:
    for pid in (mm.get(n) or []):
        tot += 1
        try:
            d = json.load(open("/data_pool/%s/pack_map.json" % pid, encoding="utf-8"))
        except Exception:
            still.append(n[:6] + "|" + pid[:8] + "|nopack"); continue
        ok = False
        for k, v in (d.get("enterprises") or {}).items():
            u = str(v.get("单位") or k); src = str(v.get("来源") or "")
            if (u == n or n[:4] in u or (u and u[:4] in n)) and "backfill" in src:
                ok = True; break
        if ok: rec += 1
        else: still.append(n[:6] + "|" + pid[:8])
out("C 精确缺漏 miss=%d 已回写=%d 未回写=%d" % (tot, rec, len(still)))
out("C 未回写样本: " + ", ".join(still[:12]))
d0 = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%%Y-%%m-%%d")
d1 = datetime.datetime.now().strftime("%%Y-%%m-%%d")
fresh = {}
for pm in glob.glob("/data_pool/*/pack_map.json"):
    try:
        d = json.load(open(pm, encoding="utf-8"))
    except Exception:
        continue
    for k, v in (d.get("enterprises") or {}).items():
        u = str(v.get("单位") or k); src = str(v.get("来源") or ""); t = str(v.get("时间") or "")
        if "backfill" not in src or not (t.startswith(d0) or t.startswith(d1)):
            continue
        for n in NAMES:
            if u == n or n[:4] in u or (u and u[:4] in n):
                fresh[n] = fresh.get(n, 0) + 1
out("C2 近2日新鲜backfill笔数: " + json.dumps(fresh, ensure_ascii=False))
'''

def main():
    # ① 本机 drain 监控窗尾部
    mon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..",
                       "cron", "output", "e93ac7f7b11a", "monitor_last_output.txt")
    print("== DRAIN 监控窗(本机) ==")
    try:
        tail = open(mon, encoding="utf-8", errors="replace").read().splitlines()[-25:]
        print("\n".join(tail))
    except Exception as ex:
        print("monitor skip:", ex)
    # ② 主服侧
    import paramiko
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(M_HOST, port=M_PORT, username=M_USER, key_filename=KEY, timeout=25)
    pay = PAYLOAD % json.dumps(NAMES23, ensure_ascii=False)
    b64 = base64.b64encode(pay.encode("utf-8")).decode()
    cmd = "echo %s | base64 -d > /tmp/check_intercept_pay.py && timeout 300 python3 /tmp/check_intercept_pay.py; rm -f /tmp/check_intercept_pay.py" % b64
    i, o, e = cli.exec_command(cmd, timeout=360)
    print("\n== 主服侧实测 ==")
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("[stderr]", err[:500])
    cli.close()
    print("CHECK-INTERCEPT DONE")

if __name__ == "__main__":
    main()
