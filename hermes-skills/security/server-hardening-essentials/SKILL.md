---
name: server-hardening-essentials
description: >-
  测绘引擎·加固 Linux 生产服务器（SSH 密钥+fail2ban+nginx gzip/ETag+端口探测）。
owned: true
tier: ops
pack: survey-skill
---

# server-hardening-essentials（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/server-hardening-essentials/`

溯源（仅标记）：`hermes/devops`

---

# 生产服务器加固与优化（Linux）

## When to Use

- 用户要求给生产服务器做安全加固（SSH 密钥登录/禁密码、fail2ban、防火墙核查）
- nginx 开了 gzip 但 JSON 响应仍很大（gzip_types 被注释）
- 爬虫/浏览器重复拉全量 JSON 接口（ETag 304 优化）
- 需要判断公网哪些端口可达（防火墙核查）

在 qavlixor 生产服务器（202.95.1.135:12125, Ubuntu, UFW+nginx+CF）实测通过的通用流程。任何同类 Linux 服务器可复用。

## SSH 密钥登录（顺序铁律：先开密钥→验证→再禁密码）

```python
# 1. 本机生成密钥对（Windows git-bash）
ssh-keygen -t ed25519 -f ~/.ssh/<name> -N "" -C "desc"
# 2. 公钥写入服务器 authorized_keys（paramiko sftp 追加），chmod 600/700
# 3. sshd_config 先开密钥：sed -i 's/^#\?PubkeyAuthentication no/PubkeyAuthentication yes/' → systemctl reload sshd
# 4. 用 pkey 登录验证成功
# 5. 再禁密码：sed -i 's/^#\?PasswordAuthentication yes/PasswordAuthentication no/' → reload
# 6. 验证：密钥 OK + 密码被拒（Bad authentication type; allowed types: ['publickey']）
```

- **reload sshd 后 ~30 秒连接会断**（10060 超时）——正常，等 30s 重试，勿以为服务器挂了；网站 200 + 端口可达 = 服务器活着
- 改完通知所有依赖密码登录的脚本（如 deploy.py）改用 pkey，否则部署直接 BadAuthenticationType
- 私钥是本机唯一钥匙：提醒用户备份到 U 盘，勿微信/QQ 传输

## fail2ban（暴力破解自动封 IP）

```bash
apt-get install -y fail2ban   # dpkg interrupted 时先 dpkg --configure -a
# /etc/fail2ban/jail.local:
# [DEFAULT] bantime=1h findtime=10m maxretry=5 ignoreip=127.0.0.1/8 ::1
# [sshd] enabled=true port=<非默认端口> logpath=/var/log/auth.log
systemctl enable fail2ban && systemctl restart fail2ban
fail2ban-client status sshd   # 验证 jail 生效
```

## nginx gzip 坑（压缩看似开了实际没压）

- `gzip on` 只是开关；**gzip_types 常被注释** → 只压 text/html，JSON/JS 不压缩
- 打开：`gzip_vary on; gzip_comp_level 6; gzip_types text/plain text/css application/json application/javascript text/xml image/svg+xml;`
- 验证：`curl --compressed -H 'Accept-Encoding: gzip' -o /dev/null -w '%{size_download}' URL` 对比未压缩

## ETag 304 坑（CF 前缀）

- **Cloudflare 会给响应 ETag 加 `W/` 前缀 + 引号**：服务端生成 `"abc"`，客户端收到 `W/"abc"`
- 比较必须剥干净：`ifNoneMatch.replace(/^W\//,'').replace(/^"|"$/g,'')`，且与自己存的 etag 也去引号比
- 实测：直接 `ifNoneMatch === etag` 永远 200，剥 W/ 后仍 200（引号未剥），两层都剥才 304

## 公网端口探测（勿用 curl 判可达）

curl 超时也返回 000，不可判"可达"。用 python socket TCP connect：
```python
import socket
s = socket.socket(); s.settimeout(4)
try: s.connect((ip, port)); print("开放")
except Exception: print("关闭/过滤")
```

## 防火墙现状核查（Ubuntu UFW）

- `ufw status`：INPUT policy DROP + 白名单（80/443 只放 CF 网段 173.245.48.0/20 等 8 段；SSH 用 LIMIT 限速）
- 应用只监听 127.0.0.1（`ss -tlnp` 确认），Nginx 对外代理
- PostgreSQL：`listen_addresses` 注释（默认 localhost）+ pg_hba 仅 local/127.0.0.1 = 公网不可达，无需改

## 管理端密码占位符坑

- 登录 401 "账号或密码不正确" 时查 AdminUser/User 表 passwordHash：若是 `"session-auth"` 之类非哈希占位 → 用项目 lib/password.ts 的 hashPassword（`sha256:salt:hash` 格式）重写
- 重置前先确认哈希格式函数，别直接存明文

## 参考
- qavlixor 实例完整操作：会话 2026-08-12（fail2ban v0.11.2 + ed25519 + gzip 5.1MB→1MB + ETag 304 实测）
- 项目专属运维（部署/psql/产物验证）见 user-owned skill `qavlixor-prod-ops`（受保护，勿改）
