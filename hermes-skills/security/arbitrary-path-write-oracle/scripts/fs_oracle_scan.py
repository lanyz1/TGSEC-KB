#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fs_oracle_scan.py — 磁盘 oracle 扫描器

把"任意路径写原语"（接口接受服务器路径参数并落盘）变成文件系统测绘探针。
典型：Geth debug_writeMemProfile / debug_writeBlockProfile / debug_writeMutexProfile。

设计约束：
  * 只写探测路径，不猜内容，不读回
  * 默认串行 + 限速（授权要求低频，勿改成高并发）
  * 五态分类：WRITABLE / DIRECTORY / SOCKET_DEV / DENIED / NO_PARENT / EROFS / OTHER

用法：
  python3 fs_oracle_scan.py --rpc https://rpc.example/eth \
      --method debug_writeMemProfile --paths paths.txt --delay 0.4 --out result.json
  python3 fs_oracle_scan.py --selftest          # 用内置 mock 自证分类逻辑
"""

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request

# 顺序敏感：先匹具体错误，再匹通用
STATE_RULES = [
    ("DIRECTORY", ("is a directory", "eisdir", "directory not empty")),
    ("SOCKET_DEV", ("no such device or address", "not a regular file", "enxio")),
    ("DENIED", ("permission denied", "access is denied", "eacces", "operation not permitted")),
    ("NO_PARENT", ("no such file or directory", "cannot find the path", "enoent")),
    ("EROFS", ("read-only file system", "erofs")),
    ("BUSY", ("text file busy", "device or resource busy", "ebusy")),
]


def classify(payload):
    """把 JSON-RPC 响应体归到五态。返回 (state, detail)。"""
    if not isinstance(payload, dict):
        return "OTHER", "non-json / no body"
    if "result" in payload:
        return "WRITABLE", "result=%r" % (payload["result"],)
    err = payload.get("error")
    if err is None:
        return "OTHER", json.dumps(payload, ensure_ascii=False)[:200]
    msg = str(err.get("message", "")) if isinstance(err, dict) else str(err)
    low = msg.lower()
    for state, keys in STATE_RULES:
        for k in keys:
            if k in low:
                return state, msg
    return "OTHER", msg


def rpc_call(url, method, path, timeout=15, headers=None):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": [path]}).encode()
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        if not raw.strip():
            return {"__state": "OTHER", "__detail": "HTTP %s (empty body)" % e.code}
    except Exception as e:  # 网络层
        return {"__state": "ERROR", "__detail": "%s: %s" % (type(e).__name__, e)}
    try:
        payload = json.loads(raw)
    except Exception:
        return {"__state": "OTHER", "__detail": "non-json: %s" % raw.strip()[:200]}
    st, detail = classify(payload)
    return {"__state": st, "__detail": detail, "__raw": raw.strip()[:400]}


def scan(rpc, method, paths, delay=0.4, timeout=15, headers=None, out=None, quiet=False):
    results = []
    lock = threading.Lock()

    def report(i, p, res):
        line = "[%3d/%3d] %-11s %s" % (i, len(paths), res.get("__state", "?"), p)
        if res.get("__state") not in ("WRITABLE", "DIRECTORY"):
            line += "   <- %s" % res.get("__detail", "")[:90]
        with lock:
            print(line, flush=True)

    for i, p in enumerate(paths, 1):
        res = rpc_call(rpc, method, p, timeout=timeout, headers=headers)
        res["path"] = p
        results.append(res)
        report(i, p, res)
        if i < len(paths):
            time.sleep(max(delay, 0))

    summary = {}
    for r in results:
        summary.setdefault(r.get("__state", "?"), []).append(r["path"])

    if not quiet:
        print("\n=== 汇总 ===")
        for st in ("WRITABLE", "DIRECTORY", "SOCKET_DEV", "DENIED", "NO_PARENT", "EROFS", "BUSY", "OTHER", "ERROR"):
            if st in summary:
                print("%-11s %d" % (st, len(summary[st])))
                if st in ("WRITABLE", "SOCKET_DEV"):
                    for p in summary[st]:
                        print("            %s" % p)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"rpc": rpc, "method": method, "summary": summary, "results": results},
                      f, ensure_ascii=False, indent=2)
        print("\n结果已写: %s" % out)
    return summary


MOCK_RULES = [
    ("/tmp/probe", {"result": None}),
    ("/home/geth", {"result": None}),
    ("/home/geth/mainnet/", {"error": {"code": -32000, "message": "is a directory"}}),
    ("/home/geth/mainnet/geth.ipc", {"error": {"code": -32000, "message": "no such device or address"}}),
    ("/usr/share/nginx/html/", {"error": {"code": -32000, "message": "permission denied"}}),
    ("/home/nobody", {"error": {"code": -32000, "message": "no such file or directory"}}),
]


def selftest():
    """离线自证：分类表 + mock 响应映射是否符合预期。"""
    import http.server
    import socketserver

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            try:
                req = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                req = {}
            p = (req.get("params") or [""])[0]
            body = {"jsonrpc": "2.0", "id": 1}
            for pref, resp in MOCK_RULES:
                if p == pref:
                    body.update(resp)
                    break
            else:
                body["error"] = {"code": -32000, "message": "no such file or directory"}
            raw = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/" % port
    paths = [r[0] for r in MOCK_RULES] + ["/home/bsc/mnemonic.txt"]
    print("mock geth JSON-RPC @ %s\n" % url)
    got = scan(url, "debug_writeMemProfile", paths, delay=0, quiet=True)
    srv.shutdown()

    expect = {
        "/tmp/probe": "WRITABLE",
        "/home/geth": "WRITABLE",
        "/home/geth/mainnet/": "DIRECTORY",
        "/home/geth/mainnet/geth.ipc": "SOCKET_DEV",
        "/usr/share/nginx/html/": "DENIED",
        "/home/nobody": "NO_PARENT",
        "/home/bsc/mnemonic.txt": "NO_PARENT",
    }
    ok = True
    for p, want in expect.items():
        st = next((s for s, ps in got.items() if p in ps), "MISSING")
        if st != want:
            ok = False
        print("%s %-32s got=%-10s want=%s" % ("OK " if st == want else "BAD", p, st, want))
    print("\nSELFTEST: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="磁盘 oracle 扫描器（任意路径写原语 → 文件系统五态测绘）")
    ap.add_argument("--rpc", help="JSON-RPC 端点，如 https://rpc.example/eth")
    ap.add_argument("--method", default="debug_writeMemProfile")
    ap.add_argument("--paths", help="路径清单文件，一行一条（# 开头为注释）")
    ap.add_argument("--delay", type=float, default=0.4, help="每请求间隔秒（默认 0.4，低频纪律）")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--header", action="append", default=[], help="额外请求头 k:v，可多次")
    ap.add_argument("--out", help="结果 JSON 落地路径")
    ap.add_argument("--selftest", action="store_true", help="离线自证（内置 mock 服务）")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not (a.rpc and a.paths):
        ap.error("--rpc 与 --paths 必填（或用 --selftest）")
    with open(a.paths, encoding="utf-8") as f:
        paths = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    headers = {}
    for h in a.header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()
    print("目标 %s  method=%s  %d 条路径  delay=%.2fs\n" % (a.rpc, a.method, len(paths), a.delay))
    scan(a.rpc, a.method, paths, delay=a.delay, timeout=a.timeout, headers=headers, out=a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
