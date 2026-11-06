#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""crack_encrypted_envelope.py — 前端 AES 信封逆向:捞候选密钥 + 零依赖(openssl)解密

适用:响应 JSON 形如 {"...","data":"<base64 长串>","t":1789302597407,"encrypt":true}
先看 references/encrypted-envelope-and-whitelist-enum.md 第 1 节(如何从前端确认算法/密钥来源)。

本脚本做两件事:
  1) 从 JS 里捞出**被拆成单字符数组**的 16 字符密钥:["V","4","L",...] → join('') (打包器常见做法)
  2) 用 openssl 原生 AES-ECB/CBC 逐个对撞(跳板机/纯净机没有 pycryptodome 也能跑)

用法:
  python3 crack_encrypted_envelope.py --js /root/x/umi.js /root/x/home.js --payload resp.json
  python3 crack_encrypted_envelope.py --keys V4LQVMHF55VgGo4d xcNgtUIgnc8Fq9oL --b64 "<data>"
  # CBC 变体:--mode cbc --iv <16字符iv>
"""
import argparse
import base64
import binascii
import json
import re
import subprocess
import sys

ARR = re.compile(r'\[((?:\s*`[A-Za-z0-9]`\s*,){15}\s*`[A-Za-z0-9]`\s*)\]')
# 明显是 UI/CSS/状态名的"16 字符"假阳性,避免噪声
NOISE = ("ant-", "icon", "save", "update", "export", "transition", "slide", "zoom", "move-",
         "background", "border", "wrapper", "overlay", "get", "set", "fetch", "modify",
         "router", "rejection", "Formatted", "modal", "usergroup", "file-", "copyright")


def harvest_keys(jsfiles):
    out = []
    for f in jsfiles:
        s = open(f, errors="replace").read()
        for m in ARR.finditer(s):
            k = re.sub(r'[`,\s]', '', m.group(1))
            if len(k) != 16 or k in out:
                continue
            if any(k.lower().startswith(n.lower()) for n in NOISE):
                continue
            out.append(k)
    return out


def aes_dec(b64, key, mode="ecb", iv=None, unpad=True):
    ct = base64.b64decode(b64.replace(" ", "+") + "=" * (-len(b64) % 4))
    open("/tmp/_ct.bin", "wb").write(ct)
    cmd = ["openssl", "enc", "-d", "-aes-%d-%s" % (len(key) * 8, mode),
           "-K", binascii.hexlify(key.encode()).decode(), "-nopad",
           "-in", "/tmp/_ct.bin", "-out", "/tmp/_pt.bin"]
    if mode == "cbc":
        cmd += ["-iv", binascii.hexlify((iv or key).encode()).decode()]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:120])
    pt = open("/tmp/_pt.bin", "rb").read()
    if unpad and pt:
        p = pt[-1]
        if 1 <= p <= 16 and pt[-p:] == bytes([p]) * p:
            pt = pt[:-p]
    return pt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--js", nargs="*", default=[])
    ap.add_argument("--keys", nargs="*", default=[], help="已知密钥(可多个,逐个试)")
    ap.add_argument("--payload", help="响应 JSON 文件(自动取 t/encrypt/data)")
    ap.add_argument("--b64", help="直接给 base64 密文")
    ap.add_argument("--mode", default="ecb", choices=["ecb", "cbc"])
    ap.add_argument("--iv", help="CBC 的 IV(16 字符)")
    ap.add_argument("--dump", help="命中后把明文写到该文件")
    a = ap.parse_args()

    keys = list(dict.fromkeys(a.keys + harvest_keys(a.js)))
    if not keys:
        sys.exit("没有候选密钥:--js 指前端包,或 --keys 直接给")
    print("候选密钥 %d 把: %s%s" % (len(keys), keys[:10], " ..." if len(keys) > 10 else ""))

    b64 = a.b64
    if a.payload:
        j = json.load(open(a.payload, encoding="utf-8"))
        b64 = j.get("data") if isinstance(j.get("data"), str) else b64
        print("信封 t=%s encrypt=%s 密文长度=%s" % (j.get("t"), j.get("encrypt"), len(b64 or "")))
    if not b64:
        sys.exit("没有密文:--payload 或 --b64")

    for k in keys:
        try:
            pt = aes_dec(b64, k, a.mode, a.iv)
        except Exception:
            continue
        s = pt.decode("utf-8", "replace")
        if s[:1] in "[{\"":
            print("★ 命中 key=%s  明文 %d B" % (k, len(pt)))
            print(s[:800])
            if a.dump:
                open(a.dump, "w", encoding="utf-8").write(s)
                print("→ 已写 %s" % a.dump)
            return
    print("✗ 全部候选未命中。回 JS 里再捞:搜 Base64.parse / AES.decrypt 的**调用点**"
          "(不是 crypto 库内部),确认算法、模式与密钥是否还由 t / 日期派生")


if __name__ == "__main__":
    main()
