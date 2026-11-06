#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fake license server for Electron 卡密 bypass (假授权服务器).

用法:
  1. 在 main.js 里把授权服务器 URL 改成 http://127.0.0.1:13818
     (minified: const wo=new Ko.default,fu="http://<原IP>:<port>" → fu="http://127.0.0.1:13818")
  2. 重打包 asar:  npx --yes @electron/asar pack out_dir resources/app.asar
  3. 启动本服务器: python3 fake_license_server.py
  4. 启动应用(直启,绕过 launcher token):
     cp main.dll main.exe
     XHS_ANON_LAUNCH_TOKEN=<main.js 首行的原值> ./main.exe
  5. 在 UI 卡密输入框填任意字符 → 验证请求打到本服务器 → code=1 → 登录成功

注意:无已存卡密时应用启动阶段不会发 /api/check(心跳短路)——
验证请求在用户 UI 提交卡密时才触发,别干等服务器日志。
electron-store 已存 license_key 时会启动即验证(%APPDATA%/<app名>/config.json 可预置)。
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class FakeLicense(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默

    def _reply(self):
        resp = json.dumps({
            "code": 1,          # 1=永久授权, 2=限时; -1过期 -2无效 -3已绑定其他设备
            "msg": "ok",
            "expire": "2099-12-31",
            "days_left": 99999,
            "promote": ""
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8', 'replace')
        print(f"[授权请求] {self.path} | body={body[:200]}")
        self._reply()

    def do_GET(self):
        self._reply()


if __name__ == "__main__":
    print("[*] 假授权服务器: http://127.0.0.1:13818  (任何卡密+机器码返回 code=1)")
    HTTPServer(("127.0.0.1", 13818), FakeLicense).serve_forever()
