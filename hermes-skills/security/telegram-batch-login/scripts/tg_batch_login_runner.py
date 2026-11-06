# -*- coding: utf-8 -*-
"""TG 批量做号 runner（类级模板，断点续跑）
用法:
    TG_API_ID=xxx TG_API_HASH=yyy python tg_batch_login_runner.py accounts.txt
清单: 每行 `phone|code_api_url`；`#` 开头为注释。
前提: pip install telethon requests python-socks
提示: Telethon 不读系统代理，必须显式传 proxy=；设备指纹要成对一致（别 Windows 系统配 Android app_version）。
"""
import json
import os
import random
import re
import sys
import time
import zipfile
from datetime import datetime

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "accounts.txt")
RESULT_JSONL = os.path.join(BASE, "results.jsonl")
PROGRESS_LOG = os.path.join(BASE, "progress.log")

API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
PROXY = {"proxy_type": "socks5", "addr": "127.0.0.1", "port": 10808, "rdns": True}
HTTP_PROXIES = {"http": "socks5h://127.0.0.1:10808", "https": "socks5h://127.0.0.1:10808"}

POLL_INTERVAL = 5
POLL_WINDOWS = {"didiapi": 75, "aixhs": 60, "62-us": 300, "tgflare": 60}  # 活源给长窗
GAP = (12, 25)
SYS_VER, APP_VER, LANG = "Windows 8.1", "1.8.9.4(46584)", "en-US"
DEV_TYPES = ["Desktop", "SMARTPHONE", "Pad"]
DEV_PRE = list("KZATUPSQM")
DEV_NUM = ["1", "2", "3", "5", "9", "10", "20", "30", "50", "70", "100"]
DEV_SUF = ["i", "E", "Pro", "ProMax"]
DEV_VER = ["5G", "4G"]


def log(msg):
    line = "[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(PROGRESS_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def gen_device():
    return "WitchMagic %s %s%s%s %s" % (random.choice(DEV_TYPES), random.choice(DEV_PRE),
                                         random.choice(DEV_NUM), random.choice(DEV_SUF),
                                         random.choice(DEV_VER))


def http_get(url, proxies=None, timeout=15):
    """直连失败自动回落代理（给定代理时反之亦然）。"""
    order = [proxies, None if proxies else HTTP_PROXIES]
    last = None
    for p in order:
        try:
            r = requests.get(url, proxies=p, timeout=timeout)
            return r.status_code, r.text
        except Exception as e:
            last = e
            time.sleep(1.5)
    return None, str(last)


def _json(txt):
    try:
        return json.loads((txt or "").strip())
    except Exception:
        return None


# ---- 码源适配：统一 (kind, value, password)；契约见 references/code-relay-source-adapters.md
def fetch_didiapi(url):
    st, txt = http_get(re.sub("GetHTML", "GetJSON", url, flags=re.I))
    if st is None:
        return ("err", "请求失败:%s" % txt, None)
    m = re.search(r"等待\s*(\d+)\s*秒", txt or "")
    if m:
        return ("wait", int(m.group(1)), None)
    d = _json(txt)
    if not isinstance(d, dict):
        return ("err", "非JSON:%s" % (txt or "")[:60], None)
    msg = str(d.get("msg", "")).replace("\n", " ")
    if d.get("status") == 0 and d.get("code"):
        return ("code", str(d["code"]), d.get("password"))
    if "掉线" in msg:
        return ("pending", "设备掉线(仍尝试)", None)  # 掉线可能恢复，别直接判死
    return ("pending", "%s:%s" % (d.get("status"), msg[:50]), None)


def fetch_text(url):
    """纯文本 no|暂无验证码 系（62-us）。"""
    st, txt = http_get(url)
    if st is None:
        return ("err", "请求失败:%s" % txt, None)
    txt = (txt or "").strip()
    if not txt:
        return ("pending", "空响应", None)
    parts = [p.strip() for p in txt.split("|")]
    if parts[0].lower() in ("no", "none") or "暂无" in txt:
        return ("pending", txt[:40], None)
    for p in parts[1:]:
        if re.fullmatch(r"\d{3,8}", p):
            rest = [x for x in parts[1:] if x and x != p]
            pw = rest[0] if rest and not re.fullmatch(r"\d{3,8}", rest[0]) else None
            return ("code", p, pw)
    m = re.search(r"(\d{4,8})", txt)
    return ("code", m.group(1), None) if m else ("pending", txt[:40], None)


def fetch_json_token(url):
    """{code:0,msg:'token不存在',data:{...}} 系（tgflare）。"""
    st, txt = http_get(url)
    if st is None:
        return ("err", "请求失败:%s" % txt, None)
    d = _json(txt)
    if not isinstance(d, dict):
        return ("err", "非JSON:%s" % (txt or "")[:60], None)
    msg = str(d.get("msg", ""))
    if "不存在" in msg or "参数不能为空" in msg:
        return ("dead", msg, None)
    data = d.get("data") or {}
    c = str(data.get("code") or "").strip()
    return ("code", c, data.get("password")) if c else ("pending", msg or "no code", None)


def fetch_code(url):
    h = (url or "").lower()
    if "didiapi" in h:
        return fetch_didiapi(url)
    if "tgflare" in h:
        return fetch_json_token(url)
    if "62-us" in h or "aixhs" in h or "get_sms" in h or "message?" in h:
        return fetch_text(url)
    return ("err", "未知码源，需加 dispatch 分支", None)


def save_json(phone, code, password, device, user):
    digits = re.sub(r"\D", "", phone)
    fn = os.path.join(BASE, digits + ".json")
    out = {"phone": phone, "code": code, "password": password, "2fa": password,
           "api_id": API_ID, "api_hash": API_HASH, "device_model": device,
           "system_version": SYS_VER, "app_version": APP_VER, "system_lang_code": LANG}
    for k in ("id", "user_id", "first_name", "last_name", "username"):
        out[k] = getattr(user, k, None) if user else None
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=4)
    return fn


def login_one(phone, url):
    from telethon.errors import (FloodWaitError, PhoneCodeExpiredError,
                                 PhoneCodeInvalidError, SessionPasswordNeededError)
    from telethon.sync import TelegramClient

    digits = re.sub(r"\D", "", phone)
    jf = os.path.join(BASE, digits + ".json")
    if os.path.exists(jf):
        return {"phone": phone, "ok": True, "reason": "已存在(跳过)", "files": []}

    kind, val, pw = fetch_code(url)
    log("%s 源预检: %s %s" % (phone, kind, str(val)[:50]))
    if kind == "dead":
        return {"phone": phone, "ok": False, "reason": "码源不可用:%s" % val, "fast": True}

    window = 150
    for key, w in POLL_WINDOWS.items():
        if key in url.lower():
            window = w
    device, sess = gen_device(), os.path.join(BASE, digits + ".session")
    last = "%s:%s" % (kind, str(val)[:40])

    try:
        client = TelegramClient(sess, API_ID, API_HASH, device_model=device,
                                system_version=SYS_VER, app_version=APP_VER,
                                system_lang_code=LANG, proxy=PROXY,
                                connection_retries=3, retry_delay=3, timeout=20)
    except Exception as e:
        return {"phone": phone, "ok": False, "reason": "客户端初始化失败:%s" % e}
    try:
        client.connect()
        if not client.is_connected():
            return {"phone": phone, "ok": False, "reason": "Telegram连接失败(查代理)"}
        try:
            client.send_code_request(phone)
            log("%s 已发码(窗口%ss)，等取码…" % (phone, window))
        except FloodWaitError as e:
            return {"phone": phone, "ok": False, "reason": "FloodWait %ss" % e.seconds}
        except Exception as e:
            return {"phone": phone, "ok": False, "reason": "发码失败:%s" % e}

        deadline, code, password = time.time() + window, None, pw
        while time.time() < deadline:
            time.sleep(POLL_INTERVAL)
            k, v, p = fetch_code(url)
            last = "%s:%s" % (k, str(v)[:40])
            if k == "wait":
                time.sleep(min(int(v), 60))
            elif k == "code":
                code, password = str(v), (p or password)
                break
            elif k == "dead":
                return {"phone": phone, "ok": False, "reason": "码源中断:%s" % v}
        if not code:
            return {"phone": phone, "ok": False, "reason": "等码超时(%s)" % last}

        try:
            client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            if not password:
                return {"phone": phone, "ok": False, "reason": "需要2FA但码源未给密码"}
            try:
                client.sign_in(password=password)
            except Exception as e:
                return {"phone": phone, "ok": False, "reason": "2FA失败:%s" % e}
        except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
            return {"phone": phone, "ok": False, "reason": "验证码错/过期:%s" % type(e).__name__}
        except Exception as e:
            return {"phone": phone, "ok": False, "reason": "登录异常:%s" % e}

        if client.is_user_authorized():
            me = client.get_me()
            files = [sess, save_json(phone, code, password, device, me)]
            jr = sess + "-journal"
            if os.path.exists(jr):
                files.append(jr)
            return {"phone": phone, "ok": True, "files": files, "device": device}
        return {"phone": phone, "ok": False, "reason": "登录后未授权"}
    except Exception as e:
        return {"phone": phone, "ok": False, "reason": "异常:%s" % e}
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def load_accounts():
    out = []
    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            phone, url = line.split("|", 1)
            out.append((phone.strip(), url.strip()))
    return out


def main():
    if not (API_ID and API_HASH):
        print("缺 TG_API_ID / TG_API_HASH 环境变量")
        sys.exit(1)
    accounts = load_accounts()
    log("载入 %d 个号" % len(accounts))
    results = []
    for i, (phone, url) in enumerate(accounts, 1):
        log("===== [%d/%d] %s =====" % (i, len(accounts), phone))
        try:
            r = login_one(phone, url)
        except Exception as e:
            r = {"phone": phone, "ok": False, "reason": "顶层异常:%s" % e}
        r["url"] = url
        results.append(r)
        with open(RESULT_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        log("%s => %s" % (phone, "OK" if r.get("ok") else "FAIL " + str(r.get("reason"))))
        if i < len(accounts):
            time.sleep(3 if r.get("fast") else random.randint(*GAP))

    ok = [r for r in results if r.get("ok") and r.get("files")]
    files = [f for r in ok for f in r["files"]]
    if files:
        zname = os.path.join(BASE, "Telegram_Sessions_%d个.zip" % len(ok))
        with zipfile.ZipFile(zname, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                if os.path.exists(f):
                    z.write(f, os.path.basename(f))
        log("打包完成: %s" % zname)
    fails = [(r["phone"], r.get("reason")) for r in results if not r.get("ok")]
    if fails:
        with open(os.path.join(BASE, "failed_accounts.txt"), "w", encoding="utf-8") as f:
            for p, why in fails:
                f.write("%s  # %s\n" % (p, why))
    log("完成: 成功 %d / 失败 %d" % (len(ok), len(fails)))
    print(json.dumps({"ok": [r["phone"] for r in ok], "fail": fails}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
