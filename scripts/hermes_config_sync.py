#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在一台 Hermes 主机上把 config.yaml 的 skills.disabled 对齐到源配置。

用法: hermes_config_sync.py <目标config> <源config>
只替换顶层 `skills:` 段，其余字节保持不动；先备份再写。
"""
import re, sys, shutil, datetime, yaml

if len(sys.argv) < 3:
    print("usage: hermes_config_sync.py <dst_config> <src_config>"); sys.exit(2)
DST, SRC = sys.argv[1], sys.argv[2]


def section(text, key="skills"):
    m = re.search(rf"^{key}:\s*$", text, re.M)
    if not m:
        return None
    nxt = re.search(r"^[A-Za-z_][\w-]*:\s", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    return m.start(), end


src_text = open(SRC, encoding="utf-8").read()
dst_text = open(DST, encoding="utf-8").read()
sb, db = section(src_text), section(dst_text)
if not sb or not db:
    print(f"FATAL 找不到 skills 段 src={bool(sb)} dst={bool(db)}"); sys.exit(1)

new = src_text[sb[0]:sb[1]]
if not new.endswith("\n"):
    new += "\n"
shutil.copy2(DST, DST + ".bak-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
open(DST, "w", encoding="utf-8").write(dst_text[:db[0]] + new + dst_text[db[1]:])

c = yaml.safe_load(open(DST, encoding="utf-8"))
print(f"OK disabled={len((c.get('skills') or {}).get('disabled') or [])} 顶层键={len(c)}")
