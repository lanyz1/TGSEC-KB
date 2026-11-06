# -*- coding: utf-8 -*-
"""db_value_sweep.py — MSSQL 实例级「值穷举」探针 (data-gap-closure-verification 第 7b 节)

用途:本地 dump / 导出侧扫空后,对方说「直接去数据库里面找」时,
在本实例(全部在线库)把号码/标识类列一次扫穿,要么命中,要么给出可写进交付的
「源侧不存在」证据(扫了哪些库/列/多少行/哪些模式)。

关键设计(每条都对应一次踩过的坑):
  * 库清单现查 sys.databases —— 不用硬编码库名清单,否则漏库。
  * 列清单取自 information_schema.columns —— 它覆盖视图(sys.tables 看不到 view)。
  * 行数取 sys.partitions —— 0 行表直接跳过;`_YYYYMMDD` 日切片/日志分片族整族跳过。
  * 每列先 top 3 抽样 —— 全 '0'/全空的死列不再跑 LIKE。
  * 搜索一律 cast(col as nvarchar(400)) collate --collate like ... —— 防 collation/数值列静默零命中。
  * 命中打印列名 + 值 —— 审计/签名表里的命中多是 md5 随机数字,先复核再上报。

用法:
  python db_value_sweep.py --host 127.0.0.1 --port 11433 --user sa --pass '***' \\
      --a 987 --b 267 [--only-ordered] [--colregex PHONE_RE] [--max-rows 300000] [--sample-only]

  --a/--b 都给 => 同时搜 '%A%B%'(前段后段,不限序位)与 "A%B"、''0A%B'' 等拼法;
  只给 --a   => 只搜 '%A%'。结果按库→表→列打印,末尾输出 ALL DONE 便于日志判定完成。
"""
import argparse
import re
import sys

import pymssql

DEFAULT_COLRE = (
    r"(mobile|phone|tel|fone|celular|contato|whatsapp|zap|telephone|bindphone|"
    r"accountid|roleid|invitecode|userid|cardno|cpf|pix|document)"
)
SHARD_RE = re.compile(r"_\d{8}$|_\d{6}$|_(19|20)\d{2}(0[1-9]|1[0-2])$")
SYSTEM_DBS = {"master", "tempdb", "model", "msdb"}
CONTEXT_COLS = {"sign", "pwd", "password", "token", "secret", "salt", "hash", "signstr"}


def q(cur, sql):
    cur.execute(sql)
    return cur.fetchall()


def text_cols(cur, db):
    return q(cur, """
        select c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE
        from [%s].INFORMATION_SCHEMA.COLUMNS c with (nolock)
        where c.DATA_TYPE in ('char','varchar','nchar','nvarchar','text','ntext')
          and c.TABLE_NAME not like 'sys%%'
        order by c.TABLE_NAME, c.COLUMN_NAME
    """ % db)


def row_counts(cur, db):
    rows = q(cur, """
        select t.name, sum(p.rows)
        from [%s].sys.partitions p with (nolock)
        join [%s].sys.tables t with (nolock) on t.object_id = p.object_id
        where p.index_id in (0,1)
        group by t.name
    """ % (db, db))
    return {n: int(r) for n, r in rows}


def patterns(a, b):
    pats = []
    if a and b:
        pats += ["%%%s%%%s%%" % (a, b), "%s%%%s" % (a, b), "0%s%%%s" % (a, b), "%s%%%s%%" % (a, b)]
    if a:
        pats.append("%%%s%%" % a)
    if b:
        pats.append("%%%s%%" % b)
    out = []
    for p in pats:
        if p not in out:
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1433)
    ap.add_argument("--user", required=True)
    ap.add_argument("--pass", dest="pw", required=True)
    ap.add_argument("--a", help="片段前半(如前 3 位)")
    ap.add_argument("--b", help="片段后半(如后 3 位)")
    ap.add_argument("--colregex", default=DEFAULT_COLRE)
    ap.add_argument("--collate", default="Latin1_General_CI_AS")
    ap.add_argument("--max-rows", type=int, default=300000, help="行数超过此值的表跳过整表扫描")
    ap.add_argument("--sample-only", action="store_true", help="只抽样列形态,不搜目标值")
    ap.add_argument("--dbs", help="逗号分隔的库白名单,默认全部在线库")
    args = ap.parse_args()

    colre = re.compile(args.colregex, re.I)
    pats = patterns(args.a, args.b)
    print("搜索模式: %s" % pats, flush=True)

    cn = pymssql.connect(server=args.host, port=args.port, user=args.user, password=args.pw,
                         database="master", charset="UTF-8", autocommit=True,
                         login_timeout=20, timeout=300)
    cur = cn.cursor()
    if args.dbs:
        dbs = [d.strip() for d in args.dbs.split(",") if d.strip()]
    else:
        dbs = [r[0] for r in q(cur, "select name from sys.databases where state_desc='ONLINE'")]
    print("实例在线库 %d 个: %s" % (len(dbs), dbs), flush=True)

    hits = []
    for db in dbs:
        if db.lower() in SYSTEM_DBS:
            print("== %s: 系统库跳过" % db, flush=True)
            continue
        try:
            cols = [c for c in text_cols(cur, db) if colre.search(c[1])]
        except Exception as e:
            print("== %s: 读列清单失败 %s" % (db, str(e)[:60]), flush=True)
            continue
        if not cols:
            print("== %s: 无号码/标识类列" % db, flush=True)
            continue
        try:
            rc = row_counts(cur, db)
        except Exception as e:
            print("== %s: 取行数失败 %s" % (db, str(e)[:60]), flush=True)
            rc = {}
        seen, skipped = set(), 0
        for tbl, col, _typ in cols:
            key = (db, tbl, col)
            if key in seen:
                continue
            seen.add(key)
            if SHARD_RE.search(tbl):
                skipped += 1
                continue
            n = rc.get(tbl)
            if n == 0:
                continue
            if n is not None and n > args.max_rows:
                skipped += 1
                continue
            fq = "[%s].dbo.[%s]" % (db, tbl)
            ce = "cast([%s] as nvarchar(400))" % col
            try:
                sample = [str(r[0])[:26] for r in q(cur, "select top 3 %s from %s with (nolock) where [%s] is not null" % (ce, fq, col))]
            except Exception as e:
                print("   %-34s %-26s 抽样失败 %s" % (tbl, col, str(e)[:40]), flush=True)
                continue
            if sample and all(s in ("0", "") for s in sample):
                print("   %-34s %-26s 死列(全 '0'/空),跳过" % (tbl, col), flush=True)
                continue
            if args.sample_only:
                print("   %-34s %-26s 行=%-8s 样例=%s" % (tbl, col, n, sample), flush=True)
                continue
            for p in pats:
                try:
                    cnt = q(cur, "select count(*) from %s with (nolock) where %s collate %s like '%s'" % (fq, ce, args.collate, p))[0][0]
                except Exception as e:
                    print("   查询失败 %s.%s %s" % (tbl, col, str(e)[:40]), flush=True)
                    continue
                if not cnt:
                    continue
                vals = [str(r[0])[:40] for r in q(cur, "select distinct top 8 %s from %s with (nolock) where %s collate %s like '%s'" % (ce, fq, ce, args.collate, p))]
                noise = " ⚠疑似哈希/签名列,须复核" if col.lower() in CONTEXT_COLS else ""
                line = "   ★ %s.%s.%s 模式 %s = %d 行=%s 值=%s%s" % (db, tbl, col, p, cnt, n, vals, noise)
                print(line, flush=True)
                hits.append(line)
        if skipped:
            print("   (%s 库跳过空表/超表/日切片 %d 张)" % (db, skipped), flush=True)

    print("\n== 汇总: %d 处命中 ==============" % len(hits), flush=True)
    for h in hits:
        print(h, flush=True)
    print("\nALL DONE", flush=True)
    cn.close()


if __name__ == "__main__":
    sys.exit(main())
