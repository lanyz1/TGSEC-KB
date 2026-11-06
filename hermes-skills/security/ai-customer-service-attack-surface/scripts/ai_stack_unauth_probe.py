#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 应用 / 客服系统 未授权面批量探测 —— 指纹 → 产品识别 → 打权威配置端点

用法:
    python ai_stack_unauth_probe.py 1.2.3.4:3000 5.6.7.8 9.10.11.12:8081
    python ai_stack_unauth_probe.py --file hosts.txt      # 每行 host[:port]

纪律: 全程只 GET、零注册、零爆破、零写入。
输出: P|主机|端口|协议|产品|端点|状态|关键字段
"""
import concurrent.futures as cf
import json
import re
import ssl
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; ai-surface-recon)",
      "Accept": "application/json, text/html;q=0.8"}
CTX = ssl.create_default_context()
CTX.check_hostname = False          # 纯探测: 证书不校验(常见自签/裸 IP)
CTX.verify_mode = ssl.CERT_NONE
TIMEOUT = 9

# ★ 用户指定的无授权目标(禁区): 一律不发任何请求, 勿移除
BANNED = {"121.15.0.233", "106.54.23.164", "221.12.174.78",
          "121.199.45.153", "27.185.14.145"}

DEFAULT_PORTS = [80, 443, 3000, 3001, 8000, 8080, 8081, 8090, 11434]

# 产品识别: 产品 -> (marker 正则, 权威配置端点, [关键字段])
PRODUCTS = {
    "OpenWebUI":   (r'"name"\s*:\s*"Open WebUI"|<title>Open WebUI',
                    "/api/config", ["version", "enable_signup", "enable_login_form",
                                    "enable_ldap", "auth_trusted_header"]),
    "LibreChat":   (r'LibreChat|librechat',
                    "/api/config", ["registrationEnabled", "emailEnabled", "serverDomain",
                                    "openidLoginEnabled", "passwordResetEnabled"]),
    "Dify":        (r'Dify|/console/api/setup',
                    "/console/api/setup", ["step", "setup_at"]),
    "Flowise":     (r'Flowise',
                    "/api/v1/version", ["version"]),
    "Langflow":    (r'Langflow|langflow',
                    "/api/v1/version", ["version"]),
    "RAGFlow":     (r'RAGFlow|ragflow',
                    "/v1/system/version", ["code", "message"]),
    "AnythingLLM": (r'AnythingLLM|anythingllm',
                    "/api/v1/admin/is-multi-user-mode", ["isMultiUserMode", "message"]),
    "Chatwoot":    (r'Chatwoot|chatwoot|/cable',
                    "/api", ["version"]),
    "FastGPT":     (r'FastGPT|fastgpt',
                    "/api/system/getInitData", ["code", "data"]),
    "Onyx":        (r'Onyx|Danswer|danswer',
                    "/api/health", ["status"]),
    "Ollama":      (r'Ollama is running',
                    "/api/tags", ["models"]),
}
# 额外必测端点(多产品共用): auto_login 是 Langflow 接管面
EXTRA = {"Langflow": ("/api/v1/auto_login", ["auto_login"])}


def get(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                  timeout=TIMEOUT, context=CTX)
        return r.status, r.read(6000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, (e.read(1500).decode("utf-8", "ignore") if e.fp else "")
    except Exception as e:
        return "ERR", str(e)[:60]


def fields(body, keys):
    out = []
    try:
        j = json.loads(body)
    except Exception:
        return out

    def walk(o, depth=0):
        if depth > 4:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if k in keys and not isinstance(v, (dict, list)):
                    out.append("%s=%s" % (k, v))
                walk(v, depth + 1)
        elif isinstance(o, list):
            for x in o[:2]:
                walk(x, depth + 1)
    walk(j)
    return out


def probe(target):
    ip, _, port = target.partition(":")
    if ip in BANNED:
        print("P|%s|%s|SKIP|BANNED|禁区(无授权),未发请求" % (ip, port or "-"))
        return
    ports = [int(port)] if port else DEFAULT_PORTS
    for p in ports:
        for proto in ("http", "https"):
            netloc = ip if (proto == "http" and p == 80) or (proto == "https" and p == 443) \
                else "%s:%d" % (ip, p)
            st, body = get("%s://%s/" % (proto, netloc))
            if st == "ERR" and ("CERTIFICATE" in body or "timed out" in body):
                continue
            hit = None
            blob = body
            for name, (marker, _cfg, _keys) in PRODUCTS.items():
                if re.search(marker, blob, re.I):
                    hit = name
                    break
            if not hit:
                if st in (200, 302, 401, 403):
                    print("P|%s:%d|%s|?|%s|未知产品(无匹配指纹)" %
                          (ip, p, proto, st))
                continue
            cfg_path, keys = PRODUCTS[hit][1], PRODUCTS[hit][2]
            st2, b2 = get("%s://%s%s" % (proto, netloc, cfg_path))
            fs = fields(b2, keys) or [b2[:70].replace("\n", " ")]
            print("P|%s:%d|%s|%s|%s|%s|%s" %
                  (ip, p, proto, hit, cfg_path, st2, " ".join(fs[:6])))
            if hit in EXTRA:
                ep, ek = EXTRA[hit]
                st3, b3 = get("%s://%s%s" % (proto, netloc, ep))
                fs3 = fields(b3, ek) or [b3[:70].replace("\n", " ")]
                print("P|%s:%d|%s|%s|%s|%s|%s" %
                      (ip, p, proto, hit, ep, st3, " ".join(fs3[:4])))
            break


def main(argv):
    targets = []
    if "--file" in argv:
        with open(argv[argv.index("--file") + 1], encoding="utf-8") as f:
            targets = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    else:
        targets = [a for a in argv[1:] if not a.startswith("-")]
    if not targets:
        print(__doc__)
        return
    print("P|host|port|proto|product|endpoint|status|fields")
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(probe, targets))
    print("### done %d targets" % len(targets))


if __name__ == "__main__":
    main(sys.argv)
