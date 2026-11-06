#!/usr/bin/env python
# Go binary string xref scanner — STRICT rip-relative lea (modrm & 0xC7 == 0x05)
# + movabs imm64 fallback + string content dump.
#
# Pitfall this fixes: naive scanning for b"\x48\x8d" + imm32 matches
# `lea rcx,[rbp+disp32]` (modrm 0x8d) which is a STACK LOCAL, not a string
# reference. Only mod=00 rm=101 (RIP-relative) is a real rodata load.
#
# Usage:
#   python string_xref.py <binary> <va1> [va2 ...]     # VA of target strings
#   python string_xref.py <binary> --strings "kbit 签名验证失败" "TRADE_SUCCESS"
#
# Output: for each target string VA -> list of lea/movabs xref VAs in .text,
# plus decoded string content (try both VA and VA-FILE_BASE offsets).
import re
import struct
import sys

BIN = sys.argv[1]
data = open(BIN, "rb").read()

FILE_BASE = 0x401000          # adjust per binary (Go ELF text section base)
TEXT_LO, TEXT_HI = 0x401000, 0x1800000   # .text VA range to scan

def off2va(off):
    return off + FILE_BASE

def cstr_at_va(va, maxlen=120):
    for cand in (va, va - FILE_BASE):
        if 0 <= cand < len(data):
            s = data[cand:cand + maxlen]
            end = s.find(b"\x00")
            if end >= 0:
                s = s[:end]
            try:
                return s.decode("utf-8")
            except Exception:
                return s.hex()
    return None

def va_from_arg(a):
    if a.startswith("0x"):
        return int(a, 16)
    return int(a)

def find_lea_rip_xrefs(target_va):
    """Scan text for `48 8d <modrm> <imm32>` where (modrm & 0xC7) == 0x05.
    tgt = instr_addr + 7 + imm32 (Go uses end-of-instruction relative)."""
    hits = []
    i = TEXT_LO
    while i < TEXT_HI - 7:
        off = i - FILE_BASE
        if off < 0 or off + 7 > len(data):
            i += 1
            continue
        if data[off] == 0x48 and data[off + 1] == 0x8d:
            modrm = data[off + 2]
            if (modrm & 0xC7) == 0x05:  # mod=00 rm=101 -> RIP-relative
                disp = struct.unpack_from("<i", data, off + 3)[0]
                tgt = i + 7 + disp
                if tgt == target_va:
                    hits.append(i)
        i += 1
    return hits

def find_movabs_xrefs(target_va):
    """Fallback: `48 b8 <imm64>` movabs rax, imm64."""
    pat = b"\x48\xb8" + struct.pack("<Q", target_va)
    hits = []
    pos = 0
    while True:
        j = data.find(pat, pos)
        if j < 0:
            break
        hits.append(j + FILE_BASE)
        pos = j + 1
    return hits

targets = []
if "--strings" in sys.argv:
    idx = sys.argv.index("--strings")
    targets = [va_from_arg(a) for a in sys.argv[2:idx]]
    raw = sys.argv[idx + 1:]
    # strings mode: locate each literal, then xref it
    for s in raw:
        enc = s.encode("utf-8")
        pos = 0
        found = []
        while True:
            j = data.find(enc, pos)
            if j < 0:
                break
            found.append(j + FILE_BASE)
            pos = j + 1
        print(f"=== string {s!r} -> VAs {[hex(x) for x in found]} ===")
        for va in found:
            for h in find_lea_rip_xrefs(va) + find_movabs_xrefs(va):
                print(f"  xref 0x{h:x}")
else:
    targets = [va_from_arg(a) for a in sys.argv[2:]]

for va in targets:
    print(f"=== target 0x{va:x} -> {cstr_at_va(va)!r} ===")
    leas = find_lea_rip_xrefs(va)
    movs = find_movabs_xrefs(va)
    print(f"  lea rip xrefs ({len(leas)}): " + " ".join(hex(x) for x in leas))
    print(f"  movabs xrefs ({len(movs)}): " + " ".join(hex(x) for x in movs))
