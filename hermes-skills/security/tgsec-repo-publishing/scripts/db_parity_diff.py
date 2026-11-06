#!/usr/bin/env python3
"""对比两个 arsenal.db 的 skills 字段差异 + 表行数 + status 直方图。

用途：同一套技能卡在两台机器上检索结果不同时，定位到底是哪个字段不一致。
用法：python3 db_parity_diff.py <A.db> <B.db>
只读打开，不会修改任何库。
"""
import hashlib
import sqlite3
import sys

SKIP = {"id"}


def load(path):
    con = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    cols = [r[1] for r in con.execute("PRAGMA table_info(skills)")]
    fields = [c for c in cols if c not in SKIP]
    sel = ",".join(fields)
    rows = {}
    for r in con.execute("SELECT name,%s FROM skills" % sel):
        name = r[0]
        vals = r[1:]
        blob = "\x00".join("" if v is None else str(v) for v in vals)
        rows[name] = (hashlib.md5(blob.encode()).hexdigest(), dict(zip(fields, vals)))
    tables = {t: con.execute("SELECT count(*) FROM \"%s\"" % t).fetchone()[0]
              for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return rows, tables, fields


def main():
    a_path = sys.argv[1] if len(sys.argv) > 1 else "/root/.hermes/arsenal/arsenal.db"
    b_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/local.db"
    ra, ta, fields = load(a_path)
    rb, tb, _ = load(b_path)

    print("A=%s rows=%d" % (a_path, len(ra)))
    print("B=%s rows=%d" % (b_path, len(rb)))
    print("only_A", sorted(set(ra) - set(rb))[:10], "count", len(set(ra) - set(rb)))
    print("only_B", sorted(set(rb) - set(ra))[:10], "count", len(set(rb) - set(ra)))

    print("\n-- table rows --")
    for t in sorted(set(ta) | set(tb)):
        if ta.get(t) != tb.get(t):
            print("  %-18s A=%-8s B=%s" % (t, ta.get(t), tb.get(t)))

    diff = [n for n in set(ra) & set(rb) if ra[n][0] != rb[n][0]]
    print("\ndiffering rows: %d / %d" % (len(diff), len(set(ra) & set(rb))))
    for n in diff[:15]:
        fa, fb = ra[n][1], rb[n][1]
        for f in fields:
            va, vb = fa.get(f), fb.get(f)
            if va != vb:
                print("  %-30s %-12s A=%-28r B=%r" % (n, f, str(va)[:28], str(vb)[:28]))
                break

    if "status" in fields:
        print("\n-- status histogram --")
        for label, rows in (("A", ra), ("B", rb)):
            hist = {}
            for _, d in rows.values():
                hist[d.get("status")] = hist.get(d.get("status"), 0) + 1
            print("  %s %s" % (label, hist))


if __name__ == "__main__":
    main()
