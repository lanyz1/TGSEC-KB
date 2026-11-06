#!/usr/bin/env python3
"""通用 VPS 环境探测脚本(paramiko)。
用法: SSH_PASS='xxx' python probe-vps.py [HOST] [PORT] [USER]
密码只走环境变量,不落盘、不写进脚本。
"""
import os, sys, paramiko

HOST = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("VPS_HOST", "")
PORT = int(sys.argv[2] if len(sys.argv) > 2 else os.environ.get("VPS_PORT", "22"))
USER = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("VPS_USER", "root")
PASS = os.environ.get("SSH_PASS", "")
if not HOST or not PASS:
    print("用法: SSH_PASS=xxx python probe-vps.py HOST [PORT] [USER]"); sys.exit(1)

def run(cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return (stdout.read().decode("utf-8", "replace").strip(),
            stderr.read().decode("utf-8", "replace").strip())

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=20, banner_timeout=20)
    print("=== SSH 连接成功 ===")
    checks = [
        ("系统", "cat /etc/os-release 2>/dev/null | head -2; uname -m"),
        ("CPU/内存/磁盘", "nproc; free -h | head -2; df -h / | tail -1"),
        ("Node/npm", "node -v 2>&1; npm -v 2>&1"),
        ("pm2", "pm2 -v 2>&1"),
        ("caddy", "caddy version 2>&1"),
        ("nginx/宝塔", "nginx -v 2>&1; ls /www/server/panel >/dev/null 2>&1 && echo BT_PRESENT"),
        ("80/443/3000端口", "ss -tlnp | grep -E ':80 |:443 |:3000 ' || echo 空闲"),
        ("Caddyfile(若caddy)", "cat /etc/caddy/Caddyfile 2>/dev/null || echo 无"),
        ("防火墙", "ufw status 2>/dev/null | head -3 || echo 无ufw"),
        ("外网", "curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://www.baidu.com 2>&1"),
        ("出口IP", "curl -s --max-time 8 ifconfig.me 2>&1"),
    ]
    for label, cmd in checks:
        out, err = run(cmd)
        print(f"--- {label} ---"); print(out or err or "(空)")
finally:
    client.close()
