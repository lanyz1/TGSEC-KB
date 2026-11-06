#!/usr/bin/env python3
"""字节码 selector 提取 + ABI 对差 + 危险 opcode 普查

用法:
    python3 dispatcher_extract.py <getcontract.json|bytecode.hex> [--abi abi.json]

输入可以是:
  - TronGrid /wallet/getcontract 的原始响应 JSON（自动取 bytecode + abi.entrys）
  - Etherscan getabi 响应 JSON
  - 纯 hex 字节码文件（此时需 --abi 提供 ABI）
输出:
  - 字节码里所有 selector（标注哪些 ABI 里有、哪些没有）
  - 隐藏 selector 的出现次数 + 位置（区分内部跳转表 vs 后门）
  - 危险 opcode 普查（DELEGATECALL / SELFDESTRUCT / CREATE2 / CALLCODE / CALL / CREATE）
  - 可升级函数 selector 命中（全 0 ⇒ 不可升级，可写进报告）
"""
import sys, json
from collections import Counter


def keccak_sel(sig):
    from Crypto.Hash import keccak
    k = keccak.new(digest_bits=256)
    k.update(sig.encode())
    return k.hexdigest()[:8]


def load(path):
    raw = open(path, errors="replace").read()
    try:
        j = json.loads(raw)
    except Exception:
        return raw.strip().replace("0x", ""), []
    bc = ""
    for k in ("bytecode", "deployedBytecode"):
        v = j.get(k)
        if isinstance(v, str) and len(v) > 40:
            bc = v
            break
    if not bc and isinstance(j.get("result"), str) and j["result"].startswith("0x"):
        bc = j["result"]
    bc = (bc or "").replace("0x", "").strip()
    entries = []
    abi = j.get("abi")
    if isinstance(abi, dict):
        entries = abi.get("entrys") or []
    elif isinstance(abi, list):
        entries = abi
    elif isinstance(abi, str):
        try:
            entries = json.loads(abi)
        except Exception:
            entries = []
    return bc, entries


def abi_funcs(entries):
    fns = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        t = str(e.get("type") or "function").lower()
        name = e.get("name")
        if t not in ("function", "") or not name:
            continue
        ins = [(i.get("type") or "") for i in (e.get("inputs") or [])]
        sig = "%s(%s)" % (name, ",".join(ins))
        try:
            fns[keccak_sel(sig)] = sig
        except Exception:
            pass
    return fns


def disasm(bc):
    ops, i, n = [], 0, len(bc)
    while i < n:
        try:
            op = int(bc[i:i + 2], 16)
        except ValueError:
            break
        ops.append((i, op))
        i += 2
        if 0x60 <= op <= 0x7f:
            i += (op - 0x5f) * 2
    return ops


UPGRADE_SIGS = ["upgradeTo(address)", "upgrade(address)", "setImplementation(address)",
                "setImpl(address)", "initialize(address)", "init(address)",
                "setService(address)", "setFactory(address)"]
DANGER = {0xf4: "DELEGATECALL", 0xff: "SELFDESTRUCT", 0xf5: "CREATE2",
          0xf2: "CALLCODE", 0xf1: "CALL", 0xf0: "CREATE", 0x3f: "EXTCODEHASH"}
DICT_VERBS = ("owner admin implementation factory token asset escrow refund fee deposit withdraw "
              "transfer settle cancel approve surplus recover pause set get is can upgrade init "
              "initialize migrate rescue sweep drain collect claim emergency kill destroy swap "
              "delegate impl proxy version create party service mode amount id usdt support").split()
DICT_TYPES = ["()", "(address)", "(uint256)", "(bool)", "(address,address)", "(uint256,address)",
              "(address,bool)", "(uint256,uint256)", "(address,uint256)", "(uint8)", "(bytes)",
              "(bytes32)", "(string)", "(address,address,uint256)", "(uint256,uint8,uint256)"]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    bc, entries = load(sys.argv[1])
    if "--abi" in sys.argv:
        try:
            extra = json.load(open(sys.argv[sys.argv.index("--abi") + 1], errors="replace"))
            if isinstance(extra, dict):
                extra = extra.get("entrys") or extra.get("abi") or []
            entries = list(entries) + list(extra)
        except Exception as e:
            print("abi load failed:", e)
    fns = abi_funcs(entries)
    print("bytecode: %d bytes | ABI 函数: %d" % (len(bc) // 2, len(fns)))
    ops = disasm(bc)
    print("指令数: %d" % len(ops))

    disp = {}
    for idx, (pos, op) in enumerate(ops):
        if op == 0x63 and idx + 1 < len(ops) and ops[idx + 1][1] == 0x14:  # PUSH4 + EQ
            s = bc[pos + 2:pos + 10]
            if len(s) == 8:
                disp[s] = pos
    print("\n=== dispatcher selector (%d) ===" % len(disp))
    extra = []
    for s, pos in sorted(disp.items(), key=lambda x: x[1]):
        nm = fns.get(s)
        if nm is None:
            extra.append(s)
        print("  %s @%06d  %s" % (s, pos // 2, nm or "★ 不在 ABI"))

    print("\n=== ★ 未在 ABI 的 selector (%d) ===" % len(extra))
    for s in extra:
        n = bc.count(s)
        poss, i = [], bc.find(s)
        while i != -1 and len(poss) < 6:
            poss.append(i // 2)
            i = bc.find(s, i + 1)
        guess = ""
        for v in DICT_VERBS:
            for t in DICT_TYPES:
                try:
                    if keccak_sel(v + t) == s:
                        guess = "  猜测 = %s%s" % (v, t)
                        break
                except Exception:
                    pass
            if guess:
                break
        verdict = "内部跳转表(正常)" if n >= 2 else "★ 仅1次, 重点逆"
        print("  %s  出现%d次 @%s  [%s]%s" % (s, n, poss, verdict, guess))

    print("\n=== 危险 opcode 普查 ===")
    cnt = Counter(op for _, op in ops)
    for op, nm in DANGER.items():
        c = cnt.get(op, 0)
        flag = "  ★★ 需人工确认目标" if op in (0xf4, 0xff, 0xf5) and c else ""
        print("  %-14s 0x%02x  %d%s" % (nm, op, c, flag))
    if not cnt.get(0xf4):
        print("\n  ⇒ 无 DELEGATECALL: 不是代理。implementation() 类函数若存在, 很可能只是占位配置。")

    print("\n=== 可升级函数探测 (全 0 ⇒ 不可升级, 可写进报告) ===")
    for sig in UPGRADE_SIGS:
        try:
            s = keccak_sel(sig)
        except Exception:
            continue
        print("  %-34s %s  字节码出现=%d" % (sig, s, bc.count(s)))

    print("\n提示: 未在 ABI 的 selector 用 *原始 calldata* 打一次")
    print("      (triggerconstantcontract 的 data 字段, 绕开 function_selector 解析),")
    print("      观察 revert 是 Unauthorized 还是业务错误 —— 后者说明它真的可被触碰。")


if __name__ == "__main__":
    main()
