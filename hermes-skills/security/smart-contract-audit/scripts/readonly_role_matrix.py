#!/usr/bin/env python3
"""只读「角色 × 函数」权限矩阵仿真 —— 智能合约权限边界审计主力工具

原理：triggerconstantcontract（TRON）/ eth_call（EVM）不广播、不改状态，
却会真实执行权限检查 ⇒ 逐格跑一遍即可画出完整权限矩阵。

判读：
  Unauthorized()              => 权限门拦住
  业务错误(WrongStatus 等)     => 已通过权限门，仅业务规则拦住
  SafeERC20FailedOperation    => 权限门已通过并走到 token 转账层（仿真禁止状态变更故 revert）
                                 ⇒ 该角色确实拥有此能力的最强证据，不要写成"不可利用"

用法：改下方 CONTRACT / USDT / ROLES / TESTS 后直接跑，或 import 复用。
注意：地址参数编码见 arg_addr()，方向搞反会导致全回 0 的假阴性。
"""
import json
import subprocess

from Crypto.Hash import SHA256

# ---------------- 地址编码（★方向相反，别混用） ----------------
ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base58_to_hex25(a):
    n = 0
    for ch in a:
        n = n * 58 + ALPH.index(ch)
    return n.to_bytes(25, "big").hex()


def arg_addr(a):
    """base58 -> 调用参数（取 [2:42]：去版本位与校验和）"""
    return "%024x%s" % (0, base58_to_hex25(a)[2:42])


def word_to_base58(word64):
    """ABI 64 字符字 -> base58（取 [-40:]）"""
    raw = bytes.fromhex("41" + word64[-40:])
    ck = SHA256.new(SHA256.new(raw).digest()).digest()[:4]
    n = int.from_bytes(raw + ck, "big")
    s = ""
    while n > 0:
        n, r = divmod(n, 58)
        s = ALPH[r] + s
    for b in raw:
        if b == 0:
            s = "1" + s
        else:
            break
    return s


# ---------------- 自定义错误字典（命中即为"过权限"的证据） ----------------
ERR = {
    "82b42900": "Unauthorized", "8e78f0cb": "WrongStatus", "c1ab6dc1": "InvalidToken",
    "2c5211c6": "InvalidAmount", "f1d80ab1": "EscrowNotFound", "5274afe7": "SafeERC20Fail",
    "929ce051": "InvalidParticipants", "9c8d2cd2": "InvalidRecipient",
    "ed28d089": "DepositBelowMinimum", "cf479181": "InsufficientBalance",
    "3ee5aeb5": "ReentrancyGuardReentrantCall", "9e87fac8": "Paused",
    "b06ebf3d": "FailedDeployment", "f4b3b1bc": "NativeTransferFailed",
    "f9984565": "UnexpectedTokenAmount", "d6bda275": "FailedCall", "9996b315": "AddressEmptyCode",
}


def sim(contract, caller, fn, args_hex="", rpc="https://api.trongrid.io"):
    """TRON 只读仿真。EVM 请换 eth_call(to=contract, data=0x<selector+args>)。"""
    body = {"owner_address": caller, "contract_address": contract,
            "function_selector": fn, "parameter": args_hex, "visible": True}
    r = subprocess.run(["curl", "-s", "--noproxy", "*", "-m", "25", "-X", "POST",
                        rpc + "/wallet/triggerconstantcontract",
                        "-H", "Content-Type: application/json", "-d", json.dumps(body)],
                       capture_output=True, timeout=35).stdout.decode(errors="replace")
    try:
        j = json.loads(r)
        # ★ revert selector 在 constant_result 前缀，不在 result.data
        cr = (j.get("constant_result") or [""])[0]
        return cr, (j.get("result") or {}).get("message", "")
    except Exception:
        return "", r[:120]


def verdict(r, msg):
    if r:
        return ERR.get(r[:8], r[:8])
    return "(空=成功!)" if "REVERT" not in msg.upper() else "REVERT:" + msg[:24]


def passed(r):
    """是否通过权限门（Unauthorized 即未通过）"""
    return not r.startswith("82b42900")


# ---------------- 自检：读路径验证（回 0 先怀疑编码，再怀疑链上） ----------------
def selftest_read_path(token, caller, known_holders):
    """known_holders = {地址: 期望数量}；对照不过就说明参数编码有问题"""
    r, _ = sim(token, caller, "symbol()")
    print("[自检] symbol() 有返回: %s" % bool(r))
    for a, expect in known_holders.items():
        r, _ = sim(token, caller, "balanceOf(address)", arg_addr(a))
        try:
            got = int(r, 16) / 1e6
        except Exception:
            got = -1
        print("  %s expect=%.6f got=%.6f %s"
              % (a[:16], expect, got, "OK" if abs(got - expect) < 0.01 else "★不匹配 → 检查编码"))


# ---------------- 示例配置（按任务替换） ----------------
CONTRACT = "<TRON_CONTRACT>"
USDT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
ROLES = {
    "owner": "<OWNER_ADDR>",
    "admin": "<ADMIN_ADDR>",
    "party": "<PARTY_ADDR>",
    "random": "<任意无关地址>",
}
TESTS = [
    ("transferAsset(address,address,uint256)", lambda a: arg_addr(USDT) + arg_addr(a) + "%064x" % 1000000),
    ("setAdmin(address,bool)", lambda a: arg_addr(a) + "%064x" % 1),
    ("setPause(bool)", lambda a: "%064x" % 1),
    ("transferOwnership(address)", lambda a: arg_addr(a)),
    ("deposit(uint256,uint256)", lambda a: "%064x%064x" % (1, 1000000)),
]

if __name__ == "__main__":
    print("=== 只读权限矩阵（不广播、不改状态）===")
    for tag, addr in ROLES.items():
        print("\n--- %s %s ---" % (tag, addr))
        for fn, argf in TESTS:
            r, m = sim(CONTRACT, addr, fn, argf(addr))
            print("  %-46s %-26s %s" % (fn.split("(")[0], verdict(r, m), "★过权限" if passed(r) else ""))
