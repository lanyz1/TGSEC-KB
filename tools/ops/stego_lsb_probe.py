#!/usr/bin/env python3
"""LSB stego probe: bit-plane extraction from PNG/BMP images."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def extract(path: Path, bits: int = 1) -> bytes:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    out = bytearray()
    byte = 0
    n = 0
    for y in range(im.height):
        for x in range(im.width):
            px = im.getpixel((x, y))
            for c in px:
                byte = (byte << bits) | (c & ((1 << bits) - 1))
                n += bits
                if n >= 8:
                    out.append(byte & 0xFF)
                    byte = 0
                    n = 0
                    if out[-1] == 0 and len(out) > 32:
                        return bytes(out)
    return bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="LSB 隐写提取")
    ap.add_argument("--path", "-p", required=True)
    ap.add_argument("--bits", type=int, default=1, choices=[1, 2, 3])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    data = extract(Path(args.path), args.bits)
    printable = sum(1 for b in data if 32 <= b < 127 or b in (9, 10, 13))
    text = data.decode("utf-8", "replace")
    out = {"path": args.path, "bits": args.bits, "bytes": len(data), "printable_ratio": round(printable / max(1, len(data)), 3),
           "preview": text[:500]}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"bytes={out['bytes']} printable={out['printable_ratio']}")
        print(text[:1000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
