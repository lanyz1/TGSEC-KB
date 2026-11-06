#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报名总表对账探针（只读，零平台请求）。

用法：
  本地分析导出的表：
    python regcsv_recon.py csv "C:/Users/x/Downloads/报名总表_XX.csv"
  主控上做三口径对账（只读 /data_pool）：
    python regcsv_recon.py pool OY002026092117022359 [--pid <池目录名>]

csv 模式：行数 / 三类分档行数 / 去重企业家数 / 缺联系人·法人·手机号的企业名单
pool 模式：定位池目录 → 平台名单 vs 池内采集 vs 三方差集 → 缺号企业到 企业档案/供应商 逐家探测
"""
import csv
import io
import json
import os
import sys

POOL = "/data_pool"
# 导出表列序：0 数据状态, 1 报名时间, 2 企业全称, 3 登录账号, 4 联系人, 5 法人, 6 手机号
C_ST, C_TIME, C_UNIT, C_ACCT, C_LINK, C_LEGAL, C_PHONE = range(7)
CONTACT_COLS = ((C_LINK, "联系人"), (C_LEGAL, "法人"), (C_PHONE, "手机号"))
SUP_DIRS = ("企业档案", "供应商")
CONTACT_KEYS = ("手机号", "法人", "联系人", "信用代码", "注册地址")


def norm(s):
    """归一：去空白（含全角空格）后比对，避免全称/简称以外的空格差异造成假差集。"""
    return "".join(str(s or "").split()).replace("\u3000", "")


def read_csv_rows(path):
    raw = open(path, "rb").read()
    txt = raw.decode("utf-8-sig", "replace")
    return list(csv.reader(io.StringIO(txt)))


def mode_csv(path):
    rows = read_csv_rows(path)
    body = [r for r in rows[1:] if any((c or "").strip() for c in r)]
    print("文件:", os.path.basename(path))
    print("表头:", rows[0] if rows else "-")
    print("数据行:", len(body))
    stat = {}
    units = {}
    for r in body:
        st = (r[C_ST] if len(r) > C_ST else "").strip()
        unit = norm(r[C_UNIT] if len(r) > C_UNIT else "")
        stat[st] = stat.get(st, 0) + 1
        units.setdefault(unit, {"rows": 0, "st": st, "acct": (r[C_ACCT] if len(r) > C_ACCT else "").strip()})
        units[unit]["rows"] += 1
    print("分档行数:", stat)
    print("去重企业家数:", len(units))
    by_st = {}
    for u, v in units.items():
        by_st[v["st"]] = by_st.get(v["st"], 0) + 1
    print("分档家数:", by_st)
    # 缺联系方式
    miss = {}
    for r in body:
        unit = norm(r[C_UNIT] if len(r) > C_UNIT else "")
        acct = (r[C_ACCT] if len(r) > C_ACCT else "").strip()
        absent = [label for idx, label in CONTACT_COLS if not (r[idx] if len(r) > idx else "").strip()]
        if absent:
            miss.setdefault((unit, acct), set()).update(absent)
    print("缺联系方式企业家数:", len(miss))
    for (unit, acct), cols in sorted(miss.items()):
        print("  - %s (%s) 缺: %s" % (unit, acct, "/".join(sorted(cols))))
    return units


def find_pool_dir(code):
    hits = []
    for name in sorted(os.listdir(POOL)):
        d = os.path.join(POOL, name)
        info_f = os.path.join(d, "项目信息.json")
        if not os.path.isfile(info_f):
            continue
        try:
            info = json.load(open(info_f, encoding="utf-8"))
        except Exception:
            continue
        if str(info.get("projCode") or "").strip() == code:
            hits.append((d, info))
    return hits


def load_plat(code):
    try:
        pm = json.load(open(os.path.join(POOL, "plat_enroll_map.json"), encoding="utf-8"))
    except Exception as e:
        print("!! 平台名单读不到:", e)
        return []
    ent = (pm.get("projs") or {}).get(code) or {}
    print("平台名单: 条目存在=%s 企业数字段=%s 名单条数=%s" % (bool(ent), ent.get("企业数"), len(ent.get("企业") or [])))
    return list(ent.get("企业") or [])


def load_pack_map(d, pid):
    p = os.path.join(d, "pack_map.json")
    if not os.path.isfile(p):
        print("!! 无 pack_map.json:", p)
        return {}
    doc = json.load(open(p, encoding="utf-8"))
    ents = doc.get("enterprises") or {}
    print("池内 enterprises: %d 个账号键 (targetProj=%s)" % (len(ents), doc.get("targetProj")))
    return ents


def mode_pool(code, pid=None):
    plat = load_plat(code)
    hits = find_pool_dir(code)
    print("池目录命中: %d" % len(hits))
    for d, info in hits:
        print("  dir=%s 目录名=%s info.projId=%s 名称=%s"
              % (d, os.path.basename(d), info.get("projId"), info.get("projName")))
    if not hits:
        return
    d = hits[0][0]
    if pid:
        print("  (显式指定 pid=%s，只用于核对，读盘仍用扫到的目录)" % pid)
    ents = load_pack_map(d, pid)
    if not ents:
        return
    # 池内企业全称（单位字段），列出字段名便于确认维度
    sample = next(iter(ents.values()))
    print("单条字段名:", sorted(sample.keys()))
    pool_units = {}
    for acct, v in ents.items():
        u = norm(v.get("单位") or v.get("用户") or acct)
        pool_units.setdefault(u, []).append(acct)
    print("池内去重企业(单位): %d" % len(pool_units))
    pset = set(norm(x) for x in plat)
    only_plat = [n for n in plat if norm(n) not in pool_units]
    only_pool = [u for u in pool_units if u not in pset]
    print("平台\\池内 = %d 家: %s" % (len(only_plat), only_plat))
    print("池内\\平台 = %d 家: %s" % (len(only_pool), only_pool))
    # 近失配（简称/包含关系）提示，避免把假差集当结论
    for u in only_pool:
        near = [p for p in plat if u and (u in norm(p) or norm(p) in u)]
        if near:
            print("  ~ 近失配(疑简称归一): 池内 %r ↔ 平台 %s" % (u, near))


def probe_contacts(names, base=POOL):
    """对给定企业全称在 企业档案/供应商 里做文件名包含匹配，打印命中字段原值。只读。"""
    listing = {}
    for sub in SUP_DIRS:
        sd = os.path.join(base, sub)
        listing[sub] = os.listdir(sd) if os.path.isdir(sd) else []
        print("[%s] %s 文件数=%d" % (sub, sd, len(listing[sub])))
    for nm in names:
        kw = norm(nm).lower()
        print("== %s" % nm)
        for sub in SUP_DIRS:
            hit = None
            for fn in listing[sub]:
                if fn.endswith(".json") and kw and kw in fn[:-5].lower():
                    hit = fn
                    break
            if not hit:
                print("   %s: 无命中" % sub)
                continue
            try:
                rec = json.load(open(os.path.join(base, sub, hit), encoding="utf-8"))
            except Exception as e:
                print("   %s: %s 解析失败 %s" % (sub, hit, e))
                continue
            vals = {k: repr(rec.get(k)) for k in CONTACT_KEYS if k in rec}
            print("   %s: %s -> %s" % (sub, hit, vals))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    mode = sys.argv[1]
    if mode == "csv":
        mode_csv(sys.argv[2])
    elif mode == "pool":
        pid = None
        if "--pid" in sys.argv:
            pid = sys.argv[sys.argv.index("--pid") + 1]
        mode_pool(sys.argv[2], pid)
        if len(sys.argv) > 4 and sys.argv[3] == "--probe":
            probe_contacts(sys.argv[4].split(","))
    else:
        print(__doc__)
        sys.exit(2)
