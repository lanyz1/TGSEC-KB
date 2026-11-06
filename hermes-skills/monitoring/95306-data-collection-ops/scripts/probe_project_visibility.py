#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_project_visibility.py —— 只读:某项目在池里的哪一组、第几位、时间字段为什么是空的。

用法(在代码树里跑,树 = cwd):
    T=/opt/v6/lib/<rel>; cd $T
    PYTHONPATH=$T python3 -u /tmp/v6mplan/probe_project_visibility.py '135次'
    # 多个关键词 = 任一命中即算;加 --all 只打印各组规模+🟡 前几条

只读:不写盘、不发消息、不联网。判据逐字复刻 bot/menus.py::groups()(不调渲染层)。
"""
import json
import os
import re
import sys

T = os.getcwd()
sys.path.insert(0, T)
POOL = os.environ.get("V6_POOL_DIR", "/data_pool")

from collector.conf import Conf  # noqa: E402
from bot.pool import Pool  # noqa: E402

try:
    from bot.menus import _deadline_dt
except Exception as e:  # 判据函数改名/搬家时早暴露
    print("IMPORT_FAIL bot.menus._deadline_dt: %s" % e)
    _deadline_dt = None

TIMEISH = ("time", "Time", "date", "Date", "日期", "时间", "开始", "结束")


def ndigits(v):
    return len(re.sub(r"\D", "", str(v or "")))


def raw_json(pid, name):
    p = os.path.join(POOL, pid, name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("   RAW_PARSE_FAIL %s: %s" % (name, e))
        return None


def dump_timeish(tag, obj, limit=14):
    if not isinstance(obj, dict):
        return
    n = 0
    for k, v in obj.items():
        if not any(t in str(k) for t in TIMEISH):
            continue
        if isinstance(v, (dict, list)):
            continue
        print("   %s %-16s = %-22r 位数=%d" % (tag, k, v, ndigits(v)))
        n += 1
        if n >= limit:
            break


def main(argv):
    all_mode = "--all" in argv
    kws = [a for a in argv if not a.startswith("--")]
    p = Pool(Conf(os.path.join(T, "conf", "master.ini")))
    projs = p.all_projects()
    now = p._bj_now()
    print("树=%s\n池内项目=%d ｜ now=%s" % (T, len(projs), now))

    hits = []
    for pid, info in projs.items():
        info = info or {}
        txt = "%s|%s|%s" % (pid, info.get("projName") or "", info.get("projCode") or "")
        if all_mode or any(k in txt for k in kws):
            hits.append((pid, info))
    print("关键词 %s ⇒ 命中 %d" % (kws or "(--all)", len(hits)))

    # ---- 复刻 groups():候选集过滤 -> 四组 ----
    cands = [(pid, i or {}) for pid, i in projs.items()
             if str((i or {}).get("stage") or "") in ("报名中", "待竞价", "竞价中")]
    ns, en, pb = [], [], []
    for pid, info in cands:
        if str(info.get("stage") or "") == "报名中":
            rd = _deadline_dt(info.get("regEndtime") or info.get("sellEnddate")) if _deadline_dt else None
            if rd and now and rd < now:
                pb.append((pid, info))
            elif int(info.get("enterpriseCount", 0) or 0) > 0:
                en.append((pid, info))
            else:
                ns.append((pid, info))
        else:
            pb.append((pid, info))
    print("候选=%d ⇒ 🔵未开始报名=%d ｜ 🟢报名进行中=%d ｜ 🟡报名结束未竞价=%d"
          % (len(cands), len(ns), len(en), len(pb)))
    for nm, lst in (("🔵", ns), ("🟢", en), ("🟡", pb)):
        nonempty = len([1 for _p, i in lst if str((i or {}).get("bidStarttime") or "")])
        print("   %s 排序键 bidStarttime 非空 = %d / %d" % (nm, nonempty, len(lst)))
    if all_mode:
        for pid, info in pb[:8]:
            print("   🟡 %s stage=%s %s" % (pid, info.get("stage"), str(info.get("projName"))[:44]))

    for pid, info in hits[:8]:
        print("\n=== %s" % pid)
        print("   stage=%s status=%s 家数(enterpriseCount)=%s"
              % (info.get("stage"), info.get("status"), info.get("enterpriseCount")))
        print("   名称=%s" % str(info.get("projName"))[:70])
        for gname, lst in (("🔵", ns), ("🟢", en), ("🟡", pb)):
            ids = [x[0] for x in lst]
            if pid in ids:
                print("   ★归属 %s 第 %d / %d 位" % (gname, ids.index(pid) + 1, len(ids)))
        print("   --- 索引 info 的时间字段 ---")
        dump_timeish("idx", {k: info.get(k) for k in ("regEndtime", "sellEnddate", "bidStarttime",
                                                     "bidEndtime", "projEndtime", "noticeDate")})
        for fn in ("项目信息.json", "bid_status.json"):
            obj = raw_json(pid, fn)
            print("   --- %s %s ---" % (fn, "缺失" if obj is None else ""))
            dump_timeish("raw", obj)
    print("PROBE_DONE")


if __name__ == "__main__":
    main(sys.argv[1:])
