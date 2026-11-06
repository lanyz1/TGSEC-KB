#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探针自测模板：起本地假目标（127.0.0.1），验证工具脚本的三条硬规范。

复制到 `tmp/selftest_<组件>.py` 后改两处（下方 TODO）：
  1) FakeHandler 按目标协议回响应，且能造出「已修复」与「未修复」两种行为；
  2) PROBE 指向被测脚本。

三条必须验的行为：① 默认 dry-run 一个包都没发 ② 命中判定正确 ③ 无授权标志时拒绝发包。

为什么必须做：没在本地跑过就宣称工具可用 = 把未验证的东西交给下一个会话；
本地假目标能同时证明闸门与判定，且不碰任何真实资产。
"""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HITS = []  # 假目标收到的请求，用来验证「dry-run 不发包」


class FakeHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        HITS.append(("GET", self.path, self.headers.get("Authorization")))
        # TODO(1): 按目标协议返回。示例=「未修复」行为：无令牌 401，带任意 Bearer 200。
        if self.headers.get("Authorization"):
            return self._send(200, {"ok": True})
        return self._send(401, {"error": "unauthorized"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode("utf-8", "replace")
        HITS.append(("POST", self.path, body))
        return self._send(201, {"client_id": "selftest-cid"})


PROBE = r"D:/<仓库>/tools/ops/<组件>_probe.py"  # TODO(2)


def run(*args):
    env = dict(os.environ)
    # 本机常带全局代理：不清掉会把 127.0.0.1 的请求截走（自测会假失败）
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost"
    p = subprocess.run([sys.executable, PROBE, *args], capture_output=True, text=True, env=env, timeout=90)
    return p.returncode, (p.stdout + p.stderr)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8899), FakeHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:8899"
    try:
        HITS.clear()
        rc, out = run("--target", base)
        print(f"[1] dry-run rc={rc} 假目标收到 {len(HITS)} 个请求 -> "
              + ("OK(未发包)" if not HITS else "FAIL(发了包)"))
        print("    " + (out.strip().splitlines()[0] if out.strip() else "(无输出)"))

        HITS.clear()
        rc2, out2 = run("--target", base, "--authorized", "--json-out", "tmp/_selftest.json")
        print(f"[2] authorized rc={rc2} 假目标收到 {len(HITS)} 个请求")
        print("    " + out2.strip()[-600:])

        HITS.clear()
        rc3, _ = run("--target", base)  # 闸门：无授权标志时不应发包
        print(f"[3] 闸门 rc={rc3} 假目标收到 {len(HITS)} 个请求 -> "
              + ("OK(拒绝发包)" if not HITS else "FAIL(无授权也发包)"))
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
