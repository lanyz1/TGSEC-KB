#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze a Windows kernel *small memory dump* (minidump) without WinDbg.

Usage:
    python minidump_analyze.py <path-to.dmp> [--stack]

Prints:
  * bugcheck code + parameters
  * module table (name, base, size) parsed from TRIAGE_DUMP64's driver list
  * attribution of every bugcheck argument and call-stack frame to a module
  * per-module stack-frame histogram (the third-party .sys with most frames = suspect)
  * unloaded-driver names

Self-check: parsed module count must equal TRIAGE DriverCount and names must
resolve (otherwise the stride / field offsets need adjusting, see
references/minidump-internals.md).
Stdlib only; validated on Windows 11 24H2/25H2 x64 small dumps.
"""
import argparse
import collections
import re
import struct

TRIAGE_OFFS = (0x2000, 0x1000)      # x64 small dump, x86 fallback
DRIVER_STRIDES = (0x90, 0x78, 0x60)  # Win11 24H2/25H2 = 0x90
KERNEL_MIN = 0xFFFF000000000000


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def u64(d, o):
    return struct.unpack_from('<Q', d, o)[0]


def find_triage(d):
    for off in TRIAGE_OFFS:
        if off + 0x48 > len(d):
            continue
        size, dcount = u32(d, off + 4), u32(d, off + 0x34)
        sp, spsz = u32(d, off + 0x38), u32(d, off + 0x3C)
        if (0 < size <= len(d) + 0x10000 and 10 <= dcount <= 5000
                and 0 < sp < len(d) and 0 < spsz < len(d)):
            return off
    raise SystemExit('TRIAGE_DUMP64 not found: not a supported kernel dump')


def parse_strings(d, off, size):
    """StringPool = repeated {u32 char_count; UTF-16LE; pad to 8 bytes}."""
    names = {}
    p = off
    end = min(off + size, len(d))
    while p + 4 <= end:
        ln = u32(d, p)
        if ln == 0 or ln > 260:
            p += 4
            continue
        s = d[p + 4:p + 4 + ln * 2].decode('utf-16-le', 'replace')
        names[p] = s            # keyed by absolute file offset
        names[p - off] = s      # and by pool-relative offset (build dependent)
        p = (p + 4 + ln * 2 + 7) & ~7
    return names


def parse_modules(d, triage):
    raw_list, dcount = u32(d, triage + 0x30), u32(d, triage + 0x34)
    raw_sp, raw_spsz = u32(d, triage + 0x38), u32(d, triage + 0x3C)
    for sp in (raw_sp, triage + raw_sp):
        try:
            names = parse_strings(d, sp, raw_spsz)
        except struct.error:
            continue
        if len(names) < 10:
            continue
        for lb in (raw_list, triage + raw_list):
            for stride in DRIVER_STRIDES:
                mods, hit = [], 0
                for i in range(dcount):
                    b = lb + i * stride
                    if b + 0x50 > len(d):
                        break
                    nameoff = u32(d, b)
                    base, size = u64(d, b + 0x38), u32(d, b + 0x48)
                    if base >= KERNEL_MIN and size:
                        hit += 1
                    mods.append({'name': names.get(nameoff, '<off %#x>' % nameoff),
                                 'base': base, 'size': size})
                if len(mods) == dcount and hit >= dcount * 0.9:
                    return mods
    raise SystemExit('driver list parse failed: unsupported stride/offsets')


def who(mods, addr):
    if addr < KERNEL_MIN:
        return None, None
    for m in mods:
        if m['base'] and m['size'] and m['base'] <= addr < m['base'] + m['size']:
            return m['name'], addr - m['base']
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dmp')
    ap.add_argument('--stack', action='store_true',
                    help='print every call-stack frame resolved to a module')
    args = ap.parse_args()

    d = open(args.dmp, 'rb').read()
    triage = find_triage(d)
    bc = u32(d, 0x38)
    params = [u64(d, 0x40 + 8 * i) for i in range(4)]

    print('file      : %s (%d bytes)' % (args.dmp, len(d)))
    print('dump type : %d   triage @ %#x' % (u32(d, 0), triage))
    print('bugcheck  : %#010x   args: %s'
          % (bc, ', '.join('%#018x' % p for p in params)))

    mods = parse_modules(d, triage)
    named = sum(1 for m in mods if not m['name'].startswith('<'))
    print('modules   : %d parsed (%d with names)' % (len(mods), named))

    for i, p in enumerate(params, 1):
        n, off = who(mods, p)
        if n:
            print('  param%d  %#018x -> %s+%#x' % (i, p, n, off))

    cs, csz = u32(d, triage + 0x28), u32(d, triage + 0x2C)
    if cs and csz and cs + csz <= len(d) and csz % 8 == 0:
        stack = struct.unpack_from('<%dQ' % (csz // 8), d, cs)
        hist, frames = collections.Counter(), []
        for i, addr in enumerate(stack):
            n, off = who(mods, addr)
            if n:
                hist[n] += 1
                frames.append((i, addr, n, off))
        print('stack     : %d slots, %d resolved to a module' % (len(stack), len(frames)))
        for n, c in hist.most_common(15):
            print('   %4d x %s' % (c, n))
        if args.stack:
            for i, addr, n, off in frames:
                print('   [%4d] %#018x %s+%#x' % (i, addr, n, off))

    ud = u32(d, triage + 0x18)
    if ud and ud < len(d):
        blob = d[ud:ud + 0x1000].decode('latin-1', 'ignore')
        names = sorted(set(re.findall(r'[A-Za-z0-9_.\-]{3,40}\.(?:sys|exe)', blob)))
        print('unloaded  : %s' % (', '.join(names) if names else '(none parsed)'))

    print('\nHINT: the third-party .sys with the most stack frames is the prime suspect. '
          'Cross-check its file timestamp under C:\\Windows\\System32\\drivers and the '
          "vendor install dir (e.g. C:\\Program Files\\<vendor>) against the crash date — "
          'anti-cheat / AV / accelerator drivers are hot-updated in place.')


if __name__ == '__main__':
    main()
