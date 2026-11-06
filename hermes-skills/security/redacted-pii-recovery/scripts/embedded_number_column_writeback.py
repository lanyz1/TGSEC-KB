#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「内嵌在自由文本列里的明文手机号」写回电话列, 并剔除拿不到明文号的行。

场景(2026-09 K11 实战):用户原话
  「把地址内嵌的手机号放到 E 列里面,做成明文手机号,然后剩下的没内嵌的是虚拟手机号的给我排除掉」
输入:原始订单 CSV(电话列已被服务端脱敏:掩码 / 虚拟转接号 / 空)
输出:同列序同列数的 CSV,电话列原位换成明文号, 尾列追加 `真号来源`;无明文号的行整行丢弃。

口径与实测数字见 SKILL.md §3.1。

用法
----
python embedded_number_column_writeback.py \
    --src  K11_订单_含用户信息.csv \
    --out  K11_订单_E列明文手机号.csv \
    --tel-col 4 --addr-col 5 --alt-addr-col 8 --name-cols 2,3,6 \
    --pool-file D:/渗透/<目标>/_ext/all_mob.tsv \
    --report report.txt

  --tel-col/--addr-col/... 用列号(0 基)或列名(自动读表头)。
  --pool-file: 每行 `号码\t次数\tvirt标志\t...`, virt=1 视为虚拟号池主号 ⇒ 剔除(可省)。
  --report: 把来源分布 / 验收指标写成文本, 直接可贴给用户。
"""
from __future__ import annotations

import argparse
import collections
import csv
import os
import re
import sys

csv.field_size_limit(10 ** 9)

RE_MOBILE = re.compile(r'1[3-9][0-9]{9}')
RE_FULL = re.compile(r'^1[3-9][0-9]{9}$')
RE_MASK = re.compile(r'^1(\d{2})\*+(\d{2,4})$')      # 159*****820 / 136****7200
RE_WAYBILL_PREFIX = re.compile(r'[A-Z]{2,8}$')       # ★JDVE<PHONE-REDACTED> ⇒ 京东运单号, 必剔


def load_pool(path):
    pool = set()
    if not path or not os.path.exists(path):
        return pool
    with open(path, encoding='utf-8', errors='replace') as f:
        for ln in f:
            if ln.startswith('#SRCMAP'):
                continue
            a = ln.rstrip('\n').split('\t')
            if len(a) >= 3 and a[0].isdigit() and a[2] == '1':
                pool.add(a[0])
    return pool


def candidates(value, pool):
    """字段内所有明文手机候选(剔运单号 / 剔号池主号), 按出现顺序返回。"""
    out = []
    if not value or len(value) < 11 or '1' not in value:
        return out
    for m in RE_MOBILE.finditer(value):
        if RE_WAYBILL_PREFIX.search(value[:m.start()]):   # 前导大写字母串 = 运单号
            continue
        n = m.group(0)
        if n in pool:
            continue
        out.append(n)
    return out


def pick_number(row, tel_i, addr_i, altaddr_i, name_is, pool, stat):
    """按 §3.1 择优顺序返回 (明文号, 来源标签), 拿不到返回 ('', '')。"""
    tel = (row[tel_i] or '').strip()
    if RE_FULL.match(tel) and tel not in pool:
        return tel, 's_tel原值明文'

    m = RE_MASK.match(tel)
    addr = candidates(row[addr_i] if addr_i is not None else '', pool)
    src = 'addr-col'
    if not addr and altaddr_i is not None:
        addr, src = candidates(row[altaddr_i] or '', pool), 'alt-addr-col'
    if addr:
        if m:
            p3, s3 = '1' + m.group(1), m.group(2)
            hit = [x for x in addr if x.startswith(p3) and x.endswith(s3)]
            if hit:
                return hit[-1], src + '(前3后3通过)'
            stat['未过前3后3'] += 1
            return addr[-1], src + '(未过前3后3,取末位)'
        return addr[-1], src

    for i in name_is:
        c = candidates(row[i] if i is not None else '', pool)
        if c:
            return c[-1], 'name-col'
    return '', ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--tel-col', default='4', help='列号(0基)或列名, 默认 4(E列 s_tel)')
    ap.add_argument('--addr-col', default='5')
    ap.add_argument('--alt-addr-col', default='8')
    ap.add_argument('--name-cols', default='2,3,6')
    ap.add_argument('--pool-file', default='')
    ap.add_argument('--report', default='')
    ap.add_argument('--progress-every', type=int, default=500000)
    a = ap.parse_args()

    pool = load_pool(a.pool_file)
    stat = collections.Counter()
    src_c = collections.Counter()
    lines = []
    first = True
    hdr = None

    def col_index(spec, hdr_row, default=None):
        if spec in ('', 'none', '-1'):
            return None
        if hdr_row is not None and not spec.lstrip('-').isdigit():
            try:
                return hdr_row.index(spec)
            except ValueError:
                raise SystemExit('列名不存在: %s' % spec)
        if spec.lstrip('-').isdigit():
            return int((hdr_row.index(spec) if hdr_row and not spec.lstrip('-').isdigit() else spec))
        return default

    rows = []
    with open(a.src, encoding='utf-8-sig', newline='', errors='replace') as f:
        rd = csv.reader(f)
        for row in rd:
            if first:
                hdr = row[:]
                # 若 --tel-col 是列名, 此处解析
                if not a.tel_col.isdigit() and a.tel_col in hdr:
                    a.tel_col = str(hdr.index(a.tel_col))
                if not a.addr_col.isdigit() and a.addr_col in hdr:
                    a.addr_col = str(hdr.index(a.addr_col))
                if a.alt_addr_col not in ('', 'none') and not a.alt_addr_col.isdigit() and a.alt_addr_col in hdr:
                    a.alt_addr_col = str(hdr.index(a.alt_addr_col))
                a.name_cols = ','.join(str(hdr.index(x)) if (x and not x.isdigit() and x in hdr) else x
                                       for x in a.name_cols.split(',') if x)
                lines.append(hdr + ['真号来源'])
                first = False
                continue
            stat['扫描行'] += 1
            if a.progress_every and stat['扫描行'] % a.progress_every == 0:
                print('  行%d 保留%d' % (stat['扫描行'], stat['保留']), file=sys.stderr, flush=True)

            tel_i = int(a.tel_col)
            addr_i = None if a.addr_col in ('', 'none') else int(a.addr_col)
            alt_i = None if a.alt_addr_col in ('', 'none') else int(a.alt_addr_col)
            name_is = [int(x) for x in a.name_cols.split(',') if x]

            num, src = pick_number(row, tel_i, addr_i, alt_i, name_is, pool, stat)
            if not num:
                stat['剔除'] += 1
                continue

            out = row[:]
            while len(out) <= tel_i:
                out.append('')
            out[tel_i] = num                      # ★ E 列原位换成明文号
            lines.append(out + [src])
            stat['保留'] += 1
            src_c[src] += 1
    del rows

    with open(a.out, 'w', encoding='utf-8-sig', newline='') as fo:
        csv.writer(fo).writerows(lines)

    # ---- 验收 ----
    nums, orders, bad = set(), set(), 0
    with open(a.out, encoding='utf-8-sig', newline='', errors='replace') as f:
        rd = csv.reader(f)
        hdr2 = next(rd)
        ti = hdr2.index('s_tel') if 's_tel' in hdr2 else int(a.tel_col)
        for row in rd:
            if row and RE_FULL.match(row[ti] or ''):
                nums.add(row[ti])
            else:
                bad += 1
            orders.add(row[0])

    lines_out = [
        '扫描行 = %d | 保留 = %d | 剔除 = %d' % (stat['扫描行'], stat['保留'], stat['剔除']),
        '唯一明文号 = %d | 唯一订单 = %d | 电话列非法值 = %d' % (len(nums), len(orders), bad),
        '来源分布:',
    ]
    lines_out += ['   %-34s %d' % (k, v) for k, v in src_c.most_common()]
    lines_out.append('写出: %s (%d B)' % (a.out, os.path.getsize(a.out)))
    text = '\n'.join(lines_out)
    print(text)
    if a.report:
        with open(a.report, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    if bad:
        print('!! 电话列有 %d 行不是 11 位明文 —— 不满足验收硬指标, 先查正则/候选逻辑' % bad,
              file=sys.stderr)


if __name__ == '__main__':
    main()
