#!/usr/bin/env python3
# labpool.py — 本地靶池生成器（模拟真实资产池分布，供 strike.sh 全流程实战演练）
# 用法: python3 labpool.py              # 起靶池 + 生成 /tmp/pool-targets.txt
#       python3 labpool.py --stop       # 停掉靶池
#       python3 labpool.py --list       # 列出池内目标与预期命中
import socketserver, threading, json, os, sys, signal
from http.server import BaseHTTPRequestHandler, HTTPServer

PIDFILE = "/tmp/.labpool.pid"
TARGETS = "/tmp/pool-targets.txt"
LOGP = "/tmp/.labpool.log"
KILL = os.path.exists("/tmp/.labpool.kill")

def rec(t):
    with open(LOGP, "a") as f: f.write(t + "\n")

# ---------- 通用 http 服务 ----------
def make_handler(kind, ip):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _j(self, c, o):
            self.send_response(c); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps(o).encode())
        def do_GET(self):
            rec(f"{ip}{kind} GET {self.path}")
            if kind == "docker" and self.path.startswith("/info"):
                self._j(200, {"ServerVersion": "24.0.9", "Docker Root Dir": "/var/lib/docker"})
            elif kind == "docker":
                self._j(200, [])
            elif kind == "gpustack" and self.path.startswith("/v2/models"):
                self._j(200, {"data": [{"id": "qwen", "state": "running"}]})
            elif kind == "comfy" and self.path.startswith("/internal/folder_paths"):
                self._j(200, {"checkpoints": ["/root/ComfyUI/models/checkpoints"], "input": ["/root/ComfyUI/input"]})
            elif kind == "comfy" and self.path.startswith("/history/"):
                pid = self.path.split("/")[2]
                self._j(200, {pid: {"prompt_id": pid, "status": {"status_str": "success"}}})
            elif kind == "comfy" and not self.path.startswith("/prompt"):
                self._j(404, {})
            else:
                self._j(404, {})
        def do_POST(self):
            b = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            rec(f"{ip}{kind} POST {self.path} {b[:120]}")
            if kind == "comfy" and self.path.startswith("/prompt"):
                self._j(200, {"prompt_id": "pid-" + self.path[-6:], "number": 1, "node_errors": {}})
            elif kind == "docker" and "/containers/create" in self.path:
                self._j(201, {"Id": "a" * 64, "Warnings": []})
            elif kind == "docker" and "/start" in self.path:
                self._j(204, {})
            elif kind == "gpustack" and self.path.startswith("/v2/models"):
                self._j(201, {"id": "newmodel", "name": "svc"})
            else:
                self._j(404, {})
        def do_DELETE(self):
            rec(f"{ip}{kind} DELETE {self.path}")
            self._j(204, {})
    return H

def serve(kind, ip, port):
    HTTPServer((ip, port), make_handler(kind, ip)).serve_forever()

# ---------- redis raw ----------
class RedisH(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            try:
                d = self.rfile.readline()
                if not d: break
                rec(f"redis CMD {d[:60]}")
                self.wfile.write(b"+PONG\r\n" if b"PING" in d else b"+OK\r\n")
            except Exception:
                break

# ---------- 池拓扑：4 台可命中 + 1 台情报面 + 2 台普通机 ----------
POOL = [
    # ip              chans
    ("127.0.0.2",     [("docker", 2375), ("comfy", 8188)]),          # 预期: docker ROOT + comfy StringFormat ROOT
    ("127.0.0.3",     [("gpustack", 30003), ("redis", 6379)]),       # 预期: gpustack ROOT + redis ROOT
    ("127.0.0.4",     [("comfy", 8188)]),                             # 预期: comfy StringFormat ROOT
    ("127.0.0.5",     [("redis", 6379)]),                             # 预期: redis ROOT
    ("127.0.0.6",     [("ollama", 11434), ("ray", 8265), ("kubelet", 10250)]),  # 情报面
    ("127.0.0.7",     []),                                            # 普通机: 0 命中
    ("127.0.0.8",     []),                                            # 普通机: 0 命中
]

def main():
    if "--stop" in sys.argv:
        if os.path.exists(PIDFILE):
            os.kill(int(open(PIDFILE).read()), signal.SIGKILL)
            os.unlink(PIDFILE)
            print("靶池已停")
        return
    if "--list" in sys.argv:
        for ip, ch in POOL:
            print(f"{ip}: " + (", ".join(k for k, _ in ch) or "普通机"))
        return
    open(PIDFILE, "w").write(str(os.getpid()))
    open(LOGP, "w").close()
    with open(TARGETS, "w") as f:
        for ip, ch in POOL:
            f.write(ip + "\n")
    for ip, chans in POOL:
        for kind, port in chans:
            if kind == "redis":
                threading.Thread(target=hredis, args=(ip, port), daemon=True).start()
            else:
                threading.Thread(target=serve, args=(kind, ip, port), daemon=True).start()
    print(f"靶池已起: {len(POOL)} 台 ✅ 目标清单: {TARGETS}")

def hredis(ip, port):
    socketserver.ThreadingTCPServer((ip, port), RedisH).serve_forever()

if __name__ == "__main__":
    main()
