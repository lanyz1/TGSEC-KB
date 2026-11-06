#!/usr/bin/env python3
"""Discuz authcode DECODE — 从 cookie 票取 uid / sid / expiretime。

用法:
    python3 authcode_decode.py '<密文>' '<SYS_KEY>'
    python3 authcode_decode.py '<密文>' 'key1,key2,key3'     # 多候选密钥

判据要点(见 SKILL.md §1):
  * keystream 只用 keya, md5 完整性校验用 keyb
    => 校验失败 **不代表**密钥错
  * 明文头 10 字节恰为 b"0000000000" 即 keystream 正确(概率 1e-10)
    此时直接取 plain[26:] 当载荷
"""
import base64
import hashlib
import sys


def _rc4(data: bytes, cryptkey: str) -> bytes:
    box = list(range(256))
    rndkey = [ord(cryptkey[i % len(cryptkey)]) for i in range(256)]
    j = 0
    for i in range(256):
        j = (j + box[i] + rndkey[i]) % 256
        box[i], box[j] = box[j], box[i]
    out = bytearray()
    a = j = 0
    for ch in data:
        a = (a + 1) % 256
        j = (j + box[a]) % 256
        box[a], box[j] = box[j], box[a]
        out.append(ch ^ box[(box[a] + box[j]) % 256])
    return bytes(out)


def _hash_family(s: str) -> str:
    return {32: "md5", 40: "sha1", 64: "sha256"}.get(len(s), "unknown")


def decode(token: str, key: str):
    """returns (plain, keystream_ok, md5_ok)"""
    keyc = token[:4]
    b64 = token[4:]
    b64 += "=" * ((-len(b64)) % 4)          # 手动补 padding
    raw = base64.b64decode(b64)
    k = hashlib.md5(key.encode()).hexdigest()
    keya = hashlib.md5(k[:16].encode()).hexdigest()
    keyb = hashlib.md5(k[16:].encode()).hexdigest()
    cryptkey = keya + hashlib.md5((keya + keyc).encode()).hexdigest()
    plain = _rc4(raw, cryptkey)
    keystream_ok = plain[:10] == b"0000000000"
    try:
        md5_ok = (hashlib.md5(plain[26:].decode("latin1").encode() + keyb.encode())
                  .hexdigest()[:16] == plain[10:26].decode("latin1"))
    except Exception:
        md5_ok = False
    return plain, keystream_ok, md5_ok


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    token = sys.argv[1].strip()
    for key in [k for k in sys.argv[2].split(",") if k]:
        plain, ks_ok, md5_ok = decode(token, key)
        if not ks_ok and not md5_ok:
            continue
        payload = plain[26:]
        print(f"[+] key={key[:8]}…  keystream={'OK' if ks_ok else '?'}  "
              f"md5={'OK' if md5_ok else 'MISMATCH (忽略, keystream 已自证)'}")
        print(f"    payload repr = {payload!r}")
        parts = payload.split(b"\t")
        if len(parts) < 2:
            print("    [!] 载荷不是 uid\\tsid\\texp 形状, 手动判读上面的 repr")
            return 0
        sid = parts[1].decode("latin1")
        print(f"    uid  = {parts[0].decode('latin1')}")
        print(f"    sid  = {sid}   (len={len(sid)} -> {_hash_family(sid)})")
        if len(parts) >= 3:
            print(f"    exp  = {parts[2].decode('latin1')}")
        print("\n    => sid 长度即哈希家族; 长度不符 = 公式还有未知材料, 去取真 token 做差分")
        return 0
    print("[-] 所有候选 key 都解不出可辨认载荷")
    return 2


if __name__ == "__main__":
    sys.exit(main())
