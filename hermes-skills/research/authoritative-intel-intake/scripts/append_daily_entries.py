#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增量补录：把新条目 append 进「按日期分片的 data JSON」，并往配套报告里插一节。

纪律（对应 SKILL.md §1/§2）：只 append 不重排 · 聚合计数只 `+=` · 锚点断言 · 写完回读校验。
默认 **dry-run**，看清计划再 `--apply`。

用法：
  python scripts/append_daily_entries.py \
      --day-json  <仓库>/data/<主题>/YYYY-MM-DD.json \
      --new-entries tmp/_new_entries.json \
      --report <仓库>/reports/<主题>-YYYY-MM-DD.md \
      --section-file tmp/_section.md \
      --report-anchor '## 本库当日变更' \
      --apply

--new-entries：`[{...与 entries 同键...}, ...]`（或 `{"entries": [...]}`）；先按既有 entries[0] 的键集对齐。
--section-file：要插进报告的 markdown 片段，插在 --report-anchor 之前（锚点须存在且唯一）。
"""
import argparse
import json
import sys


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day-json", required=True, help="按日期分片的 data JSON（须含 entries[]）")
    ap.add_argument("--new-entries", required=True)
    ap.add_argument("--report")
    ap.add_argument("--section-file")
    ap.add_argument("--report-anchor", default="## 本库当日变更")
    ap.add_argument("--key", default="cve_id", help="主键字段名（去重用）")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    if a.section_file and not a.report:
        print("[ERR] 给了 --section-file 就要同时给 --report")
        return 1

    day = load(a.day_json)
    entries = day.setdefault("entries", [])
    have = {e.get(a.key) for e in entries}
    tmpl_keys = list(entries[0].keys()) if entries else None

    new = load(a.new_entries)
    if isinstance(new, dict):
        new = new.get("entries", [])

    fresh, dup = [], []
    for e in new:
        k = e.get(a.key, "<缺主键>")
        if k in have:
            dup.append(str(k))
            continue
        if tmpl_keys:
            # 多余键塞进 tags 保留信息，缺键补 None，保持 schema 一致
            for extra in [x for x in e if x not in tmpl_keys]:
                tags = e.setdefault("tags", [])
                if isinstance(tags, list) and extra not in tags:
                    tags.append(extra)
                e.pop(extra)
            for kk in tmpl_keys:
                e.setdefault(kk, None)
        fresh.append(e)

    st = day.setdefault("stats", {})
    delta = {
        "critical": sum(1 for e in fresh if str(e.get("severity", "")).lower() == "critical"),
        "high": sum(1 for e in fresh if str(e.get("severity", "")).lower() == "high"),
        "exploited_in_wild": sum(1 for e in fresh if e.get("exploited_in_wild")),
        "recorded_here": len(fresh),
    }
    print(f"[plan] 新增 {len(fresh)} 条 / 已在库跳过 {len(dup)} 条")
    for e in fresh:
        print(f"  + {e.get(a.key)} {e.get('severity')} {e.get('product')}")
    if dup:
        print("  跳过（已在库）: " + ", ".join(dup))
    print("[plan] stats 增量: " + json.dumps(delta, ensure_ascii=False))

    section = None
    if a.report:
        txt = open(a.report, encoding="utf-8").read()
        n = txt.count(a.report_anchor)
        if n != 1:
            print(f"[ERR] 报告锚点出现 {n} 次（须为 1）：{a.report_anchor!r} —— 未写入任何改动")
            return 1
        section = open(a.section_file, encoding="utf-8").read().rstrip() + "\n\n"
        print(f"[plan] 报告在锚点前插入 {len(section)} 字符章节")

    if not a.apply:
        print("[dry-run] 未写入。确认无误后加 --apply")
        return 0

    entries.extend(fresh)
    for k, v in delta.items():
        st[k] = int(st.get(k) or 0) + v
    dump(a.day_json, day)
    if section:
        open(a.report, "w", encoding="utf-8").write(txt.replace(a.report_anchor, section + a.report_anchor, 1))

    # 回读校验：条数一致 + 新增主键确实在
    back = load(a.day_json)
    ids = {e.get(a.key) for e in back["entries"]}
    ok = len(back["entries"]) == len(entries) and all(e.get(a.key) in ids for e in fresh)
    print(f"[write] entries={len(back['entries'])} stats={json.dumps(back['stats'], ensure_ascii=False)}")
    print("[verify] " + ("OK" if ok else "FAILED —— 立即人工复查"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
