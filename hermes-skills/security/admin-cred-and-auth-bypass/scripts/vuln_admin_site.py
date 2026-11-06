#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本机靶场:模拟一个"凭据到处漏"的管理后台,用来验证 admin_cred_hunter.py。
   python vuln_admin_site.py 8899
   /admin   → 正常后台(默认口令 admin/admin888 可进)
   /admin2  → 带锁定策略的后台(5 次失败即锁,正确口令不在样本里)
"""
import json
import re
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
SPA_CATCHALL = len(sys.argv) > 2 and sys.argv[2] == "spa"   # 模拟 SPA 站:未知路径一律 200 兜底页

FILLER = ("<!-- padding padding padding padding padding padding padding padding -->\n" * 6)
CATCHALL = ("<!doctype html><html><head><title>404 Not Found</title></head><body>"
            "<h1>404</h1><p>The requested URL was not found on this server.</p>" + FILLER + "</body></html>")

MAIN_JS = """
/* build: 2026-09-01 */
const API_BASE = "/prod-api";
const appid = "a8f3c1e0b7d29f45";
const appSecret = "<REDACTED>";
const jwtSecret = "MySuperSecretJwtSigningKey2026";
const aesKey = "1234567890abcdef";
const db = "jdbc:mysql://10.20.30.40:3306/admin_db?user=root&password=<REDACTED>";
const oss = "LTAI_REDACTED";
const internal = "http://admin.control.internal:8080/api";
const sign = (o) => md5(encodeURI(JSON.stringify(o)) + appSecret);
// TODO: 上线前删掉 测试账号 admin/admin888
const endpoints = ["/prod-api/system/user/list","/prod-api/system/role/list",
                   "/api/base/login","/api/admin/list","/prod-api/system/user/export"];
const bearer = "Bearer [REDACTED-JWT]";
"""

HOME = """<!doctype html><html><head><meta charset="utf-8"><title>运营管理后台</title>
<link rel="stylesheet" href="/static/app.css"></head><body>
<div id="app"></div>
<script src="/js/chunk-vendors.js"></script>
<script src="/js/main.js"></script>
<script>window.__CFG__={"api":"/prod-api","uploadCdn":"https://oss.example.com"};</script>
</body></html>"""

LOGIN_FORM = """<!doctype html><html><head><title>登录</title></head><body>
<form action="/login" method="post">
<input name="username" placeholder="用户名"><input name="password" type="password">
<button>登录</button></form></body></html>"""

ENV_FILE = """APP_NAME=admin
APP_KEY=base64:Q2hhbmdlTWVQbGVhc2VUaGlzS2V5MTIzNDU2Nzg=
APP_DEBUG=false
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=admin_prod
DB_USERNAME=root
DB_PASSWORD=149fe47f0a9b347e
JWT_SECRET=MySuperSecretJwtSigningKey2026
REDIS_PASSWORD=r3d1s_p@ss_2026
"""

ACTUATOR_ENV = json.dumps({
    "activeProfiles": ["prod"],
    "propertySources": [{"name": "application.yml", "properties": {
        "spring.datasource.url": {"value": "jdbc:mysql://10.20.30.41:3306/admin_db"},
        "spring.datasource.username": {"value": "root"},
        "spring.datasource.password": {"value": "Adm1n@Db2026"},
        "jwt.signing-key": {"value": "4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c"},
    }}]}, ensure_ascii=False)

ROBOTS = """User-agent: *
Disallow: /admin
Disallow: /prod-api/
Disallow: /operate-center/
Disallow: /backup/
"""

COOKIE_JAR = {}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "nginx"
    sys_version = ""

    def _send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p in ("/admin", "/admin/", "/", "/admin2"):
            return self._send(200, HOME)
        if p == "/js/main.js":
            return self._send(200, MAIN_JS, "application/javascript")
        if p == "/js/chunk-vendors.js":
            return self._send(200, "/*vendor*/var _v=1;", "application/javascript")
        if p in ("/.env", "/.env.production"):
            return self._send(200, ENV_FILE, "text/plain")
        if p == "/actuator/env":
            return self._send(200, ACTUATOR_ENV, "application/json")
        if p == "/actuator":
            return self._send(200, json.dumps({"_links": {"env": {}, "heapdump": {}, "mappings": {}}}), "application/json")
        if p == "/actuator/httptrace":
            return self._send(200, json.dumps({"traces": [{"request": {"uri": "/prod-api/system/user/export",
                     "headers": {"authorization": ["Bearer <BEARER-REDACTED>"]}}}]}), "application/json")
        if p == "/robots.txt":
            return self._send(200, ROBOTS, "text/plain")
        if p == "/prod-api/system/user/list":
            return self._send(200, json.dumps({"code": 200, "rows": [{"userId": 1, "userName": "admin",
                     "password": "$2a$10$abcdefghijklmnopqrstuv"}]}), "application/json")
        if p in ("/login", "/admin2/login"):
            return self._send(200, LOGIN_FORM)
        if p == "/storage/logs/laravel.log":
            return self._send(200, "[2026-09-01] production.ERROR: login attempt {\"user\":\"admin\",\"pass\":\"Admin@2026\"}\n", "text/plain")
        if p.startswith("/.git"):
            return self._send(403, "<html><head><title>403 Forbidden</title></head><body>nginx</body></html>")
        # catch-all:SPA 站所有未知路径回同一个 200 兜底页(最容易刷出假阳性,基线法专治这个)
        if SPA_CATCHALL:
            return self._send(200, CATCHALL)
        return self._send(404, CATCHALL)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode("utf-8", "replace")
        q = urllib.parse.parse_qs(body)
        u = (q.get("username") or [""])[0]
        pw = (q.get("password") or [""])[0]

        if p == "/login":
            if u == "admin" and pw == "admin888":
                return self._send(200, json.dumps({"code": 200, "msg": "登录成功",
                     "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.localdev", "role": "administrator"}),
                     "application/json", {"Set-Cookie": "admin_token=abc123; Path=/"})
            return self._send(200, json.dumps({"code": 401, "msg": "用户名或密码错误"}), "application/json")

        if p == "/admin2/login":
            COOKIE_JAR["fails"] = COOKIE_JAR.get("fails", 0) + 1
            if COOKIE_JAR["fails"] > 5:
                return self._send(200, json.dumps({"code": 423, "msg": "账号已锁定,请稍后再试"}),
                                  "application/json")
            if u == "admin" and pw == "NotInAnyWordlist!2026":
                return self._send(200, '{"code":200,"token":"t"}', "application/json")
            return self._send(200, json.dumps({"code": 401, "msg": "用户名或密码错误"}), "application/json")
        return self._send(404, CATCHALL)


if __name__ == "__main__":
    print(f"[靶场] http://127.0.0.1:{PORT}/admin  (admin/admin888 可进)")
    print(f"[靶场] http://127.0.0.1:{PORT}/admin2 (5 次失败后锁定)")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
