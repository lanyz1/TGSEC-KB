#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Qavlixor 生产 DB 查询脚本上传执行器（paramiko 环境修复版）

用法:
  1. 写查询逻辑到 _q.mjs（ESM 语法：await import("@prisma/client")；读 .env.local 正则注入 env）
  2. python qav-prod-query.py _q.mjs

连接配置从项目 scripts/deploy.py 读取（HOST/PORT/USER/PWD），勿硬编码（红线：禁凭证入 memory）。

paramiko 环境坑（2026-08-12 实测）:
  - hermes venv 的 paramiko 已坏（cryptography 版本不匹配 ImportError）
  - 全局 PYTHONPATH 指向 hermes site-packages → 新建 venv 也被污染
  - 修复: unset PYTHONPATH + python -m venv + pip install paramiko，然后跑本脚本
"""
import re
import sys

import paramiko

# 从 deploy.py 读连接配置
deploy_path = r"D:\跨境商城\qavlixor-marketplace\scripts\deploy.py"
with open(deploy_path, encoding="utf-8") as f:
    src = f.read()
m = re.search(r'HOST, PORT, USER, PWD = "([^"]+)", (\d+), "([^"]+)", "([^"]+)"', src)
if not m:
    print("deploy.py 连接配置解析失败"); sys.exit(1)
HOST, PORT, USER, PWD = m.group(1), int(m.group(2)), m.group(3), m.group(4)

if len(sys.argv) < 2:
    print("用法: python qav-prod-query.py <本地查询脚本.mjs>")
    sys.exit(1)
local = sys.argv[1]
remote = "/www/tiktok/_q_tmp.mjs"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=PORT, username=USER, password=PWD, timeout=60,
          allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
sftp.put(local, remote)
sftp.close()

stdin, stdout, stderr = c.exec_command(f"cd /www/tiktok && node {remote} 2>&1", timeout=120)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
c.exec_command(f"rm -f {remote}")  # 清理，防残留

print(out)
if err.strip():
    print("=== STDERR ===")
    print(err[:3000])
c.close()
