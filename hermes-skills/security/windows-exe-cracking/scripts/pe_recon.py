#!/usr/bin/env python3
"""PE recon: parse header, list sections with entropy, scan packer signatures.

Usage: python pe_recon.py <file.exe>

Prints machine type, section table (size + entropy), and common packer/installer
signatures. Entropy ~8.0 on a large section (esp. .rsrc) means the payload is
compressed/encrypted — extract by RUNNING the binary, not by parsing.
"""
import math
import struct
import sys

PACKER_SIGS = [
    (b"NullsoftInst", "NSIS installer"),
    (b"Inno Setup", "Inno Setup"),
    (b"7z\xbc\xaf\x27\x1c", "7z archive"),
    (b"UPX!", "UPX packed"),
    (b"MEI", "PyInstaller (MEI cookie)"),
    (b"app.asar", "Electron asar"),
    (b"PK\x03\x04", "ZIP container"),
]


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in freq if c)


def main(path: str) -> int:
    try:
        data = open(path, "rb").read()
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"file: {path}  size: {len(data)} bytes")
    if data[:2] != b"MZ":
        print("not a PE (no MZ header)")
        return 1
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        print("not a PE (no PE signature)")
        return 1
    machine, num_sections, timestamp, _, _, opt_size, _ = struct.unpack_from(
        "<HHIIIHH", data, pe + 4
    )
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    print(
        f"machine: 0x{machine:x} ({'x86-64' if machine == 0x8664 else 'x86'})  "
        f"sections: {num_sections}"
    )
    print(
        f"opt magic: 0x{magic:x} ({'PE32+' if magic == 0x20B else 'PE32'})  "
        f"timestamp: 0x{timestamp:x}"
    )
    print("\n=== sections ===")
    sec_off = opt + opt_size
    for i in range(num_sections):
        off = sec_off + i * 40
        name = data[off:off + 8].rstrip(b"\0").decode("latin1")
        vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
        ent = entropy(data[rawptr:rawptr + rawsize])
        flag = ""
        if ent > 7.6 and rawsize > 1024 * 1024:
            flag = "  <-- HIGH ENTROPY (packed/encrypted)"
        print(
            f"{name:10s} vsize={vsize:10d} vaddr=0x{vaddr:x} "
            f"rawsize={rawsize:10d} entropy={ent:5.2f}{flag}"
        )
    print("\n=== packer signatures ===")
    for sig, label in PACKER_SIGS:
        idx = data.find(sig)
        print(
            f"{label:28s} {'found @ 0x%x' % idx if idx >= 0 else 'NOT FOUND'}"
        )
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <file.exe>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
