#!/usr/bin/env python3
"""PE section entropy + packer signature scanner for Windows binaries.

Usage:
    python3 pe_entropy_scan.py <exe-file>

Prints section table with Shannon entropy (high ~8.0 in .rsrc = encrypted/compressed
payload, typical of PyInstaller onefile / Nuitka wrappers) and scans the file for
common packer/bundler signatures.

Pure stdlib — no third-party deps.
"""
import math
import struct
import sys

SIGNATURES = [
    (b"MEI\x0c\x0b\x0a\x0b\x0e", "PyInstaller onefile cookie"),
    (b"UPX!", "UPX packed"),
    (b"app.asar", "Electron asar"),
    (b"NullsoftInst", "NSIS installer"),
    (b"MEI", "PyInstaller marker (noisy)"),
    (b"onefile_", "PyInstaller 6.x onefile extraction ref"),
]


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in freq if c)


def analyze(path: str) -> None:
    data = open(path, "rb").read()
    print(f"file: {path} ({len(data)} bytes)")
    print(f"sha256: {__import__('hashlib').sha256(data).hexdigest()}")

    if data[:2] != b"MZ":
        print("NOT a PE file (no MZ header)")
        return
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        print("PE signature missing")
        return
    pe = e_lfanew
    machine, num_sections, timestamp, _, _, opt_size, chars = struct.unpack_from(
        "<HHIIIHH", data, pe + 4
    )
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    print(f"machine: 0x{machine:x}  sections: {num_sections}  "
          f"opt_magic: 0x{magic:x} ({'PE32+' if magic == 0x20B else 'PE32'})  "
          f"chars: 0x{chars:x}")

    sec_off = opt + opt_size
    print("\n=== sections ===")
    for i in range(num_sections):
        off = sec_off + i * 40
        name = data[off:off + 8].rstrip(b"\0").decode("latin1")
        vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
        secdata = data[rawptr:rawptr + rawsize]
        ent = shannon_entropy(secdata)
        flag = "  <-- HIGH ENTROPY (packed/encrypted)" if ent > 7.5 else ""
        print(f"{name:10s} vsize={vsize:10d} rawsize={rawsize:10d} "
              f"entropy={ent:5.2f}{flag}")

    print("\n=== packer signatures ===")
    for sig, label in SIGNATURES:
        idx = data.find(sig)
        print(f"{label:45s} {'FOUND @ 0x%x' % idx if idx >= 0 else 'not found'}")

    # CJK run count (Chinese business-logic strings often survive Nuitka)
    import re
    cjk = re.findall(rb"[\xe4-\xe9][\x80-\xbf][\x80-\xbf]", data)
    print(f"\nCJK trigram count: {len(cjk)} (high = Chinese strings present)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    analyze(sys.argv[1])
