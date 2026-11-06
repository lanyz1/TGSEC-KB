#!/usr/bin/env python3
"""Try decrypting base64 blobs with candidate AES keys/modes (anti-block list pattern).

Usage: python3 decrypt_b64_candidates.py <blob_file_or_dir> [key_hex_or_utf8str ...]

Key forms tried per candidate: utf8 bytes, hex-decoded bytes.
Modes: ECB, CBC(iv=0), CBC(iv=key[:16]).
Hit = plaintext contains http:// or a domain-like token.
"""
import base64, glob, os, re, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def candidates_from_key(k: str):
    outs = []
    b = k.encode()
    if len(b) in (16, 24, 32):
        outs.append(('utf8', b))
    try:
        h = bytes.fromhex(k)
        if len(h) in (16, 24, 32):
            outs.append(('hex', h))
    except Exception:
        pass
    return outs


def try_decrypt(raw: bytes, key: bytes):
    hits = []
    for mode_name, iv in [('ECB', None), ('CBC0', b'\x00' * 16), ('CBCk', key[:16])]:
        try:
            if mode_name == 'ECB':
                dec = AES.new(key, AES.MODE_ECB).decrypt(raw)
            else:
                dec = AES.new(key, AES.MODE_CBC, iv).decrypt(raw)
            for v in (dec, dec[: len(dec) // 16 * 16]):
                try:
                    pt = unpad(v, 16)
                except Exception:
                    continue
                try:
                    t = pt.decode('utf-8')
                except Exception:
                    continue
                if re.search(r'https?://|\.(com|cn|net|xyz|top|vip|cc|la|io)\b', t, re.I):
                    hits.append((mode_name, t))
        except Exception:
            pass
    return hits


def load_blobs(path):
    blobs = []
    files = glob.glob(os.path.join(path, '*')) if os.path.isdir(path) else [path]
    for f in files:
        try:
            txt = ''.join(open(f).read().split())
        except Exception:
            continue
        if '<' in txt[:5] or 'DOCTYPE' in txt[:40] or 'Attention' in txt:
            continue  # HTML/CF block page, not a blob
        try:
            blobs.append((os.path.basename(f), base64.b64decode(txt)))
        except Exception:
            pass
    return blobs


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    blobs = load_blobs(sys.argv[1])
    keys = sys.argv[2:] or ['e0df2f9aa60f4bd70fd05714d5d7cea0']
    print(f'blobs: {len(blobs)} | keys: {len(keys)}')
    total = 0
    for name, raw in blobs:
        for k in keys:
            for form, kb in candidates_from_key(k):
                for mode, pt in try_decrypt(raw, kb):
                    total += 1
                    print(f'*** HIT [{name}] key={form}:{k[:16]}.. mode={mode}')
                    print('    ', pt[:500].replace('\n', ' '))
    print('hits:', total)


if __name__ == '__main__':
    main()
