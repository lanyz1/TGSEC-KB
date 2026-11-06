#!/usr/bin/env python3
"""只读全参数空间扫描（TRON triggerconstantcontract）—— 绝不广播。

用途：
  1) 用 view 函数反推未文档化的业务语义（mode / amount 各是什么）
  2) 用 energy_used 判定「参数是否被读取」与「角色是否走特权分支」
  3) 三态判读：result.result / energy_used / 自定义错误 selector

用法：
  python3 view_param_sweep.py <合约> <调用者> 'previewRefund(uint256,uint8,uint256)' \
      --grid=6,0|1|2|3|255,0|1000000|10**12

注意：地址类参数请用 addr_arg() 生成（见下方注释），不要手拼。
"""
import json, subprocess, sys, os, itertools

for _k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
    os.environ.pop(_k, None)

ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(a):
    n = 0
    for ch in a:
        n = n * 58 + ALPH.index(ch)
    return n.to_bytes(25, "big")


def addr_arg(a):
    """base58 地址 -> 32 字节左补零参数。

    ★ 必须取 hex[2:42]（跳过 0x41 版本位 + 去掉 4 字节校验和）。
      取 [-40:] 会带上校验和字节 => 所有带地址参数的 view 全回 0（高频事故）。
    反向（ABI 64 字符字 -> base58）要取 [-40:]。两个方向相反，别混。
    """
    return "%024x%s" % (0, b58decode(a).hex()[2:42])


def uint(x):
    return "%064x" % x


def call(contract, caller, selector, params="", timeout=30):
    body = {"owner_address": caller, "contract_address": contract,
            "function_selector": selector, "parameter": params, "visible": True}
    out = subprocess.run(["curl", "-s", "--noproxy", "*", "-m", str(timeout), "-X", "POST",
                          "https://api.trongrid.io/wallet/triggerconstantcontract",
                          "-H", "Content-Type: application/json", "-d", json.dumps(body)],
                         capture_output=True, timeout=timeout + 10).stdout.decode(errors="replace")
    try:
        j = json.loads(out)
    except Exception:
        return {"ok": None, "energy": None, "msg": out[:80], "sel": "", "raw": ""}
    res = j.get("result") or {}
    cr = (j.get("constant_result") or [""])[0]
    return {"ok": res.get("result"), "energy": j.get("energy_used"),
            "msg": res.get("message", ""), "sel": cr[:8], "raw": cr}


# 常见 escrow/托管类错误 selector（实测字典，可继续扩）
ERR = {"82b42900": "Unauthorized", "8e78f0cb": "WrongStatus", "f1d80ab1": "EscrowNotFound",
       "2c5211c6": "InvalidAmount", "c1ab6dc1": "InvalidToken", "929ce051": "InvalidParticipants",
       "5274afe7": "SafeERC20FailedOperation", "3ee5aeb5": "ReentrancyGuardReentrant",
       "4d2b57f6": "InvalidMode(未知,实测写路径用)", "f9984565": "UnexpectedTokenAmount",
       "d6bda275": "FailedCall", "9996b315": "AddressEmptyCode"}


def describe(r):
    """三态判读。ok=True 不代表成功，必须配 energy 看执行深度。"""
    if r["ok"] is None:
        return "请求失败 %s" % r["msg"][:40]
    if r["sel"]:
        return "拒绝: %s (energy=%s)" % (ERR.get(r["sel"], r["sel"]), r["energy"])
    ws = [int(r["raw"][i:i + 64] or "0", 16) for i in range(0, len(r["raw"]), 64)]
    if ws:
        shown = [("%.6fU" % (x / 1e6) if x >= 10 ** 4 else x) for x in ws[:4]]
        return "★ 返回 %s (energy=%s)" % (shown, r["energy"])
    # 空返回 = 歧义：无返回值函数成功时也长这样 => 只能靠 energy 判深度
    deep = "业务逻辑已跑完" if (r["energy"] or 0) > 50000 else "疑似提前中止"
    return "(空返回) %s energy=%s" % (deep, r["energy"])


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    contract, caller, selector = sys.argv[1], sys.argv[2], sys.argv[3]
    grid = next((a.split("=", 1)[1] for a in sys.argv[4:] if a.startswith("--grid=")), None)
    print("合约 %s\n调用者 %s\n函数 %s" % (contract, caller, selector))
    if not grid:
        print("  " + describe(call(contract, caller, selector)))
        return

    def ev(e):
        try:
            return int(eval(e, {"__builtins__": {}}, {}))
        except Exception:
            return int(e)

    cols = [g.split("|") for g in grid.split(",")]
    seen = {}
    for combo in itertools.product(*cols):
        vals = [ev(c) for c in combo]
        r = call(contract, caller, selector, "".join(uint(v) for v in vals))
        print("  args=%-30s %s" % (vals, describe(r)))
        seen.setdefault(r["energy"], []).append(vals)

    print("\n=== energy 分组（相同 energy ⇒ 同代码路径；同函数内 ⇒ 被改动的参数未被读取）===")
    for en, argss in seen.items():
        mark = "  ★ 该参数未影响路径（死参数）" if len(argss) > 1 else ""
        print("  energy=%-8s x%d%s   例: %s" % (en, len(argss), mark, argss[0]))


if __name__ == "__main__":
    main()
