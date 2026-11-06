---
name: browser-session-handoff
description: "Use when a challenge wall needs real Chrome, then curl."
version: 1.0.0
license: MIT
platforms: [linux, macos]
---

# 过墙一次,会话移交给 CLI

> 带 JS 挑战 / 地域墙 / 无头检测的站点,只用 curl 硬刚是纯烧时间。正确形状是:**真浏览器过一次墙 → 把 cookie 导出成 jar → 后面所有批量活(curl/nuclei/sqlmap/ffuf)全继承这个已解会话**。

## 触发场景
- 目标回 "One moment, please…" / `Loader` / `Checking your browser` / 一段混淆 JS,curl 拿不到业务体
- 目标按**来源地区**分流(美国 IP 弹客服页,换地区出口就不弹)
- 已经有一个跳板/出口,但希望浏览器也走它(而不是走本机直连)
- 同一站点要跑几百发探测,不可能每发都过一次挑战

---

## 第一步:先判墙,不要先补头

三种墙的症状高度相似,**处置完全不同**。判错就是把一整轮耗在补 `Sec-Fetch-*` 上。

| 墙型 | 指纹 | 决定性测试 | 处置 |
|---|---|---|---|
| **边缘硬封(ASN/网段级)** | 403 + 大厂错误页(`Sorry, you have been blocked` / Cloudflare Ray ID / AWS WAF) | 换 **N 个不同出口**(本机机房 / 跳板机房 / 第三方中转如 `r.jina.ai`)+ 换方法(GET/POST/OPTIONS)+ 换协议(http/https),**全部同码** ⇒ 规则打在**客户端网络**上 | **停手,别补头**。转源站 IP 发现 / 换非机房住宅出口 |
| **JS / 挑战壳** | 200 但 body 只有几 KB 引导 JS、`location.reload()`、`document.cookie=` 写入后跳转 | 真浏览器一发就过;curl 补全浏览器头族仍过不了 | 走本卡下半场:代理浏览器 + cookie 移交 |
| **地域墙** | 200 但内容是"联系客服/返回首页"+ 回显你的 IP(`IP: x.x.x.x, Host: y`) | 换地区出口立刻正常 ⇒ 判地域 | 选**目标地区**的出口,再按 JS 挑战处理 |

**铁律:同一 URL 在 ≥3 个不同出口 × ≥2 种方法 × 2 种协议下读数一致,才允许下"硬封"结论。**
单出口 403 既可能是硬封,也可能是那次探测没带 cookie —— 不做对照就下结论,会把自己劝退在能打的目标前面。
**反向也成立**:中转/镜像服务(`r.jina.ai` 等)走的是**它自己的**出口与 ASN。它回 403 **不能**证明站点挂了或你被封 —— 它只是另一个被封的机房 IP。

---

## 第二步:架出口(SSH 动态 SOCKS)

```bash
ssh -f -N -D 127.0.0.1:1080 -p <port> -i <key> \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes <user>@<host>
ss -lntp | grep 1080          # 必须看到 LISTEN 才算成
curl -s --socks5-hostname 127.0.0.1:1080 https://ipinfo.io/json   # 验证出口
```

- 用 `-f -N -D`(**不要** `setsid … &`;那样常起不来且无监听,`ExitOnForwardFailure=yes` 会让它直接暴露失败)。
- `--socks5-hostname` 而非 `--socks5`:**DNS 在出口侧解析**,目标侧的 DNS 污染/分流绕开。
- 给 nmap/sqlmap 这类不认 SOCKS 参数的工具配 proxychains:**`/etc/proxychains4.conf` 常被沙箱拒写**(`Refusing to write to sensitive system path`)⇒ 写自己的配置,用 `-f` 指定:
  ```
  strict_chain
  proxy_dns
  remote_dns_subnet 224
  socks5 127.0.0.1 1080
  ```
  然后 `proxychains4 -f /root/px.conf <cmd>`。

---

## 第三步:第二个 Chrome 绑出口

**另开一个实例、另一个 CDP 端口、独立 profile**,不动正在用的主浏览器。

```bash
google-chrome --no-sandbox \
  --remote-debugging-port=9334 \
  --proxy-server="socks5://127.0.0.1:1080" \
  --user-data-dir=/tmp/cp_my \
  --disable-blink-features=AutomationControlled \
  --window-size=1280,900 about:blank
curl -s http://127.0.0.1:9334/json/version     # 有 JSON 才算活
```

- **容器/root 下必须 `--no-sandbox`**,否则 CDP 端口不响应(首试就是漏了它)。
- 无头容易被识别 ⇒ 本机有 Xvfb 就 `DISPLAY=:99` 起有头;`--user-data-dir` 必须独立,共享 profile 会让新实例直接退出。
- 用 CDP 打开目标页、等导航完成、确认 body 已不是挑战页,再进入下一步。

## 第四步:会话移交(cookie → Netscape jar)

`scripts/cdp_cookie_jar.py` 直接从 CDP 拉 `Network.getAllCookies` 落成 Netscape jar:

```bash
python3 scripts/cdp_cookie_jar.py 9334 <target-domain> /tmp/t.jar
curl -s --socks5-hostname 127.0.0.1:1080 -b /tmp/t.jar https://<target>/wp-json/ -o /tmp/r.json
```

移交成功后,原来被封的面会一次性打开:路由表、用户枚举、目录探测、批量扫描全部恢复常规速度。
**这一步才是目的** —— 浏览器只是过墙器,不是终点。

---

## 坑

- **jar 必须按目标域过滤**。带上别的域的 cookie 无害,但目标域的 cookie 一条没带就等于没过墙;导出后先 `curl -b` 验一发再批量。
- **换取到的会话可能绑 IP**。挑战 token 类 cookie 常与出口绑定 ⇒ **后面的 curl 必须继续走同一个出口**,换出口会立刻掉回挑战页。
- **cookie 有时效**。挑战通过后的通行证通常几十分钟到几小时;批量任务前重跑第三/四步,别复用上一轮的 jar。
- **地域判定看出口,不看 UA/locale**。`Accept-Language`/时区伪造不改变服务端按 IP 的引流。
- **别在一台被封 IP 上反复过墙**。挑战通过 ≠ 解封;若业务面仍 403,是另一条规则,回到第一步重判。
- **过墙成功后要记账**:哪些请求是浏览器发的、哪些是 curl 带的 jar —— 报告里要能说清每条结论出自哪个会话。

## 收尾自证

1. 出口:`curl --socks5-hostname … ifconfig.me` 回的是预期 IP;
2. 会话:`curl -b jar` 打一个**已知需要会话**的端点,拿到业务体而不是挑战页;
3. 收工:关掉独立 Chrome 与隧道,不留监听端口。

## 配套
- `scripts/cdp_cookie_jar.py` —— CDP 导 cookie 成 Netscape jar(依赖 `websocket-client`)
- `references/wall-fieldnotes.md` —— 三类墙的实测读数样本(含"硬封"与"我方才问题"的对照记录)
