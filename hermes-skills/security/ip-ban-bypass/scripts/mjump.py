#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mjump —— 多台跳板机并行执行同一个脚本 (变量隔离实验 / 换出口对比)。

用法:
    python3 mjump.py <host_key> <本地脚本> [参数...]        # 单台
    python3 mjump.py all <本地脚本> [参数...]               # 全部可用机器

host_key:
    ningbo    宁波电信 110.42.103.114:56102  root/[REDACTED]   ✅
    neimeng   内蒙古电信 43.240.221.227:22   root/vLAZ5fL4Zzfo   ✅
    shaoxing  绍兴电信 124.248.67.181:22     root/[REDACTED]   ✅
    shenzhen  深圳电信 103.109.21.198:22     (2026-09 起不可达, 保留占位)

为什么要"多机并行跑同一脚本"：
    区分「权限拒绝」与「IP 限流」的标准手法 —— 同一请求在多台干净 IP 上各跑一遍,
    若各机返回一致且稳定, 是权限问题; 若出现"第 N 次后状态跃变", 是限流。
    (实例见 security/baidu-netdisk-share-recon 的 errno:2 → too fast 曲线)

依赖: paramiko  (本机 python 已装, 无需在跳板机上装)
"""
import os
import sys
import paramiko

HOSTS = {
    "ningbo":   ("110.42.103.114", 56102, "root", "[REDACTED]"),
    "neimeng":  ("43.240.221.227",    22, "root", "vLAZ5fL4Zzfo"),
    "shaoxing": ("124.248.67.181",    22, "root", "[REDACTED]"),
    "shenzhen": ("103.109.21.198",    22, "root", "3VUe9OjleEss"),
}

REMOTE_DIR = "/root/mjump"


def connect(spec, timeout=20):
    host, port, user, pwd = spec
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, port=port, username=user, password=pwd,
              timeout=timeout, banner_timeout=timeout, auth_timeout=timeout)
    return c


def run_on(name, local_script, args, timeout=300):
    spec = HOSTS[name]
    print("=" * 74)
    print(f"### {name}  {spec[0]}:{spec[1]}")
    print("=" * 74)
    try:
        c = connect(spec)
    except Exception as e:
        print(f"  !! 连接失败: {e}")
        return
    try:
        sftp = c.open_sftp()
        try:
            sftp.mkdir(REMOTE_DIR)
        except IOError:
            pass
        remote = f"{REMOTE_DIR}/{os.path.basename(local_script)}"
        sftp.put(local_script, remote)
        sftp.close()
        cmd = "cd %s && python3 %s %s" % (REMOTE_DIR, remote, args)
        _, out, err = c.exec_command(cmd, timeout=timeout)
        o = out.read().decode("utf-8", "replace")
        e = err.read().decode("utf-8", "replace")
        if o:
            print(o)
        if e.strip():
            print("[STDERR]", e)
        print(f"--- {name} done ---\n")
    except Exception as e:
        print(f"  !! 执行失败: {e}")
    finally:
        c.close()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    target, local_script = sys.argv[1], sys.argv[2]
    args = " ".join("'%s'" % a.replace("'", "") for a in sys.argv[3:])
    names = list(HOSTS) if target == "all" else [target]
    if target != "all" and target not in HOSTS:
        print(f"未知 host_key: {target}  (可选: {', '.join(HOSTS)}, all)")
        return 2
    for n in names:
        run_on(n, local_script, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
