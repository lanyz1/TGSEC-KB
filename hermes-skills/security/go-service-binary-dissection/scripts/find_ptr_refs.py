#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE64 pointer-slot scanner for Go binary dissection.

Find every little-endian 64-bit occurrence of one or more VAs anywhere in a
binary. Used to walk data-segment pointer chains when a string/address has no
code xref: string-header {ptr,len} table entries, slice descriptors
{ptr,len,cap}, globals, route/whitelist tables, etc.

Usage:
    python find_ptr_refs.py <binary> <delta> <VA> [<VA> ...]

    delta = VA - file_offset (Go ELF commonly 0x400000; VERIFY before trusting:
take a symtab function VA, read its first bytes at VA-delta, compare with the
objdump disassembly).
    VAs accept hex with or without 0x prefix.

Output: per VA, every file offset (+recomputed VA) where the LE64 value sits
(40 shown max per VA). Hit slots in .data are data pointers worth chasing; hits
in .text are instruction immediates (false positives) -- check with objdump -h
section table.
"""
import os
import struct
import sys


def scan(data, va):
    pat = struct.pack("<Q", va)
    offs, start = [], 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        offs.append(i)
        start = i + 1
    return offs


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    binp, delta = sys.argv[1], int(sys.argv[2], 0)
    if not os.path.exists(binp):
        print("not found:", binp)
        sys.exit(1)
    vas = [int(a, 16) if a.lower().startswith("0x") else int(a, 0)
           for a in sys.argv[3:]]
    data = open(binp, "rb").read()
    print("bin=%s size=%d delta=0x%x" % (binp, len(data), delta))
    for va in vas:
        offs = scan(data, va)
        print("VA 0x%x: %d hit(s)" % (va, len(offs)))
        for o in offs[:40]:
            print("   fileoff 0x%x  (VA 0x%x)" % (o, o + delta))
        if len(offs) > 40:
            print("   ... %d more" % (len(offs) - 40))


if __name__ == "__main__":
    main()
