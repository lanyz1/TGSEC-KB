#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mock PHP-FPM：按 FastCGI 协议解析请求，验证 fcgi_client.py 发出的包是否合法。
模拟 FPM 关键行为:
  - BEGIN_REQUEST contentLength 必须 == 8（写 7 字节 → 跟 php-src 一样判定非法, 返回 rawlen=0 错误）
  - role 必须 = 1 (FCGI_RESPONDER)，否则请求作废
  - SCRIPT_FILENAME 不存在/非 .php → STDERR "Access to the script ... has been denied"（security.limit_extensions）
  - PHP_ADMIN_VALUE 含 auto_prepend_file=php://input + allow_url_include=On → 把 STDIN 当 PHP 执行(回显标记)
"""
import socket, struct, sys, threading, os

FCGI = {1: "BEGIN_REQUEST", 2: "ABORT_REQUEST", 3: "END_REQUEST", 4: "PARAMS", 5: "STDIN", 6: "STDOUT", 7: "STDERR"}
SCRIPTS_ON_DISK = {"/var/www/html/index.php", "/www/wwwroot/index.php"}


def rec(t, content=b""):
    pad = (8 - len(content) % 8) % 8
    return struct.pack(">BBHHBB", 1, t, 1, len(content), pad, 0) + content + b"\x00" * pad


def decode_params(body):
    p, i = {}, 0
    while i < len(body):
        n = body[i]; i += 1
        if n & 0x80:
            n = struct.unpack(">I", body[i - 1:i + 3])[0] & 0x7FFFFFFF; i += 3
        name = body[i:i + n]; i += n
        v = body[i]; i += 1
        if v & 0x80:
            v = struct.unpack(">I", body[i - 1:i + 3])[0] & 0x7FFFFFFF; i += 3
        val = body[i:i + v]; i += v
        p[name.decode()] = val.decode(errors="replace")
    return p


def handle(conn):
    f = conn.makefile("rb")
    env, stdin, log = {}, b"", []
    bad = None
    while True:
        hdr = f.read(8)
        if not hdr or len(hdr) < 8:
            break
        ver, t, rid, clen, pad, _ = struct.unpack(">BBHHBB", hdr)
        body = f.read(clen)
        if pad:
            f.read(pad)
        log.append(f"{FCGI.get(t,t)} len={clen}")
        if t == 1:
            if clen != 8:            # php-src main/fastcgi.c: len == sizeof(fcgi_begin_request)
                bad = f"BEGIN_REQUEST contentLength={clen} != 8 -> 请求作废 (rawlen=0)"
                break
            role = (body[0] << 8) | body[1]
            if role != 1:
                bad = f"role={role} 非法(非 RESPONDER) -> 请求作废"
                break
            log.append(f"  role=RESPONDER flags={body[2]}")
        elif t == 4:
            env.update(decode_params(body))
        elif t == 5:
            if clen == 0:
                break
            stdin += body
    sfn = env.get("SCRIPT_FILENAME", "")
    if bad:
        conn.sendall(rec(7, bad.encode()) + rec(3, b"\x00" * 8))
    elif sfn not in SCRIPTS_ON_DISK and not sfn.endswith(".php"):
        conn.sendall(rec(7, f"Access to the script '{sfn}' has been denied (see security.limit_extensions)".encode())
                     + rec(3, b"\x00" * 8))
    elif sfn not in SCRIPTS_ON_DISK:
        conn.sendall(rec(7, b"Primary script unknown") + rec(3, b"\x00" * 8))
    else:
        ini = env.get("PHP_ADMIN_VALUE", "")
        out = f"MOCK-EXEC ".encode()
        if "auto_prepend_file=php://input" in ini and "allow_url_include=On" in ini:
            out += b"open_basedir=[" + ini.split("open_basedir=")[1].split("\n")[0].encode() + b"] CODE=" + stdin
        else:
            out += b"(no prepend)"
        if env.get("extension"):
            out += b" EXT=" + env["extension_dir"].encode() + b"/" + env["extension"].encode()
        if env.get("SCRIPT_NAME") == "/status":
            out = b'{"pool":"www","processes":4}'
        conn.sendall(rec(6, out) + rec(3, b"\x00" * 8))
    print("REQUEST:", " | ".join(log))
    print("  ENV:", {k: v for k, v in env.items() if k in
                     ("SCRIPT_FILENAME", "PHP_ADMIN_VALUE", "extension_dir", "extension", "CONTENT_LENGTH", "SCRIPT_NAME")})
    conn.close()


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:19000"
    if target.startswith("unix://"):
        path = target[7:]
        if os.path.exists(path):
            os.unlink(path)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(path)
    else:
        host, _, port = target.rpartition(":")
        srv = socket.socket()
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, int(port)))
    srv.listen(8)
    print("mock-fpm listening on", target, flush=True)
    for _ in range(12):
        try:
            c, _a = srv.accept()
        except Exception:
            break
        threading.Thread(target=handle, args=(c,), daemon=True).start()
    print("mock-fpm done", flush=True)


if __name__ == "__main__":
    main()
