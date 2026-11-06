#!/usr/bin/env python3
"""字节码 dispatcher 提取 + 与 ABI 对差 —— 找出 ABI 漏报 / 隐藏函数

用法:
  # 已有 hex 字节码
  python3 dispatcher_selectors.py --bytecode-file bc.hex [--abi-file abi.json] [--extra-sigs sigs.txt]
  # 直接从 TronGrid 拉（TRON）
  python3 dispatcher_selectors.py --trongrid <TRON_ADDR> [--extra-sigs sigs.txt]

输入格式:
  bc.hex      : 纯 hex 或 0x 开头的十六进制字节码
  abi.json    : getcontract 返回的 {"abi":{"entrys":[...]}} 或直接 entrys 数组
  sigs.txt    : 每行一个函数签名（如 transferOwnership(address)），用于反查未知 selector

自检: keccak256("owner()")[:4] == 8da5cb5b（不一致说明 keccak 库不对，别往下走）
"""
import argparse
import json
import sys

try:
    from Crypto.Hash import keccak
except ImportError:
    sys.exit("需要 pycryptodome: pip install pycryptodome")


def sel(sig):
    k = keccak.new(digest_bits=256)
    k.update(sig.encode())
    return k.hexdigest()[:8]


def walk(bc):
    """逐指令遍历，跳过 PUSHn 的立即数（否则会把立即数里的字节误当 opcode → 假阳性）"""
    ops, i, n = [], 0, len(bc)
    while i < n - 1:
        try:
            op = int(bc[i:i + 2], 16)
        except ValueError:
            break
        ops.append((i // 2, op))
        i += 2
        if 0x60 <= op <= 0x7f:          # PUSH1..PUSH32
            i += (op - 0x5f) * 2
    return ops


def dispatcher_selectors(bc):
    """dispatcher 模式: PUSH4 <sel> EQ(0x14)"""
    seq = walk(bc)
    out = {}
    for idx, (pos, op) in enumerate(seq):
        if op == 0x63 and idx + 1 < len(seq) and seq[idx + 1][1] == 0x14:
            s = bc[pos * 2 + 2: pos * 2 + 10]
            if len(s) == 8:
                out[s] = pos
    return out


def count_real_opcodes(bc):
    cnt = {}
    for _, op in walk(bc):
        cnt[op] = cnt.get(op, 0) + 1
    return cnt


def abi_sigs(entries):
    out = {}
    for e in entries or []:
        if e.get("type") in ("Function", "Error"):
            s = "%s(%s)" % (e.get("name"), ",".join([(i.get("type") or "") for i in e.get("inputs", [])]))
            out[sel(s)] = ("ERR " if e.get("type") == "Error" else "") + s
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bytecode-file")
    ap.add_argument("--trongrid", help="TRON 地址，自动拉字节码+ABI")
    ap.add_argument("--abi-file")
    ap.add_argument("--extra-sigs", help="每行一个签名，用于反查未知 selector")
    a = ap.parse_args()

    assert sel("owner()") == "8da5cb5b", "keccak 自检失败: sel('owner()') != 8da5cb5b"
    print("[自检] keccak ok (owner() == 8da5cb5b)")

    bc, abi = "", None
    if a.trongrid:
        import subprocess
        body = json.dumps({"value": a.trongrid, "visible": True})
        r = subprocess.run(["curl", "-s", "--noproxy", "*", "-m", "30", "-X", "POST",
                            "https://api.trongrid.io/wallet/getcontract",
                            "-H", "Content-Type: application/json", "-d", body],
                           capture_output=True, timeout=40).stdout.decode(errors="replace")
        j = json.loads(r)
        bc = j.get("bytecode") or ""
        abi = (j.get("abi") or {}).get("entrys", [])
        print("[getcontract] name=%s bytecode=%d bytes ABI=%d entries"
              % (j.get("name"), len(bc) // 2, len(abi)))
    else:
        bc = open(a.bytecode_file).read().strip()
    if bc.startswith("0x"):
        bc = bc[2:]
    if a.abi_file and abi is None:
        d = json.load(open(a.abi_file))
        if isinstance(d, dict) and "abi" in d:
            abi = d["abi"]["entrys"]
        elif isinstance(d, dict):
            abi = d.get("entrys", [])
        else:
            abi = d

    disp = dispatcher_selectors(bc)
    known = abi_sigs(abi)
    print("\n=== dispatcher selector: %d 个 ===" % len(disp))
    extra = []
    for s, pos in sorted(disp.items(), key=lambda x: x[1]):
        if s not in known:
            extra.append((s, pos))
        print("  %s @%-7d %s" % (s, pos, known.get(s, "★未知")))

    hints = {}
    if a.extra_sigs:
        for line in open(a.extra_sigs):
            line = line.strip()
            if line:
                hints[sel(line)] = line

    print("\n=== ★ 字节码有 / ABI 无（隐藏或 ABI 漏报）: %d ===" % len(extra))
    for s, pos in extra:
        print("  ★★ %s @%-7d %s" % (s, pos, hints.get(s, "")))
    print("\n提示：用 --extra-sigs 传候选签名清单（每行一个）可自动反查。"
          "仍查不到的多为 Solidity 内部函数分发表条目（在字节码里会被主流程调用多次），
"
          "属正常现象，不要当后门。")

    print("\n=== 真实 opcode 计数（已跳过立即数）===")
    cnt = count_real_opcodes(bc)
    for op, nm in [(0xf4, "DELEGATECALL"), (0xff, "SELFDESTRUCT"), (0xf5, "CREATE2"),
                   (0xf2, "CALLCODE"), (0xf1, "CALL"), (0xf0, "CREATE"), (0x55, "SSTORE")]:
        print("  %-14s %d" % (nm, cnt.get(op, 0)))
    print("\n判读：DELEGATECALL=0 且 SELFDESTRUCT=0 ⇒ 非代理、无自毁（可据此证伪 is_proxy 假阳性）")


if __name__ == "__main__":
    main()
