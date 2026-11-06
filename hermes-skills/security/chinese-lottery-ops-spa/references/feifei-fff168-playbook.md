# Playbook · 菲菲/fff168 计划室运营 SPA

**Target sample:** `http://202.95.8.69/` · 证书 SAN `fff168.cc`,`qqq168.cc`,`www.*`  
**Title:** 菲菲团队 · 运营版  
**Date:** 2026-09-24  
**Stack:** nginx · PHP/8.1.29 · 单页内联 JS · MySQL · CF 前置可选

---

## Recon dump

```
80/443  nginx 业务
3306    MySQL  Host 'x' is not allowed
23389   RDP/TLS  CN=DESKTOP-0STM83J  (X.224 Confirm)
26888   nginx 404 + Trace-Id
64993   SIP OPTIONS 200
64994   TLS handshake fail
7680    open 无 banner
```

- 域名 A → CF `188.114.96/97.3`；**源站 = 用户 IP**（Host+body 与直连一致）。
- 证书 NotAfter 2026-09-22（评估日 09-24 已过期）。

## Auth register（VALIDATED 高）

```bash
JAR=/tmp/ff.cj
curl -sk -c $JAR -b $JAR http://IP/api/auth/me.php -o /tmp/me.json
CSRF=$(python3 -c 'import json;print(json.load(open("/tmp/me.json"))["csrf_token"])')
DEV=$(python3 -c 'import uuid;print(uuid.uuid4().hex)')
curl -sk -c $JAR -b $JAR -X POST http://IP/api/auth/register.php \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" -H "X-FF-Device-ID: $DEV" \
  --data-binary '{"username":"zz1","password":"Test@123456","phone":"<PHONE-REDACTED>"}'
# 窗口期: ok=true role=member membership_active +30d
# 后期同 IP: REGISTRATION_VERIFICATION_UNAVAILABLE | TOO_FREQUENT
```

已知测试号（战役内）：`zz1790241571`/`Test@123456` id=22；`pt241533`/`Test@123456` id=21。

登录锁文案：`失败次数过多，请15分钟后再试`（会员+后台）。

## Plan room

```bash
# 游客 CSRF 会话
curl … -X POST /api/plan/start.php -H "X-CSRF-Token:…" -H "Content-Type: application/json" \
  --data-binary '{"confirm":true}'
curl … "/api_plan.php?all=1"   # ~68KB plans
curl … "/api_jssc_latest.php?id=56"   # 常无授权
curl … "/api_jssc_history.php?id=56"
```

篡改 start 的 `session_minutes`/`is_vip` 无效。

## Moments / support

- `GET /api/moments/list.php` 未登录可读（昵称 7777/pentest1 等）。
- 会员 FormData create；图片内容校验严（php/双后缀 422）。
- support：`open` → `session.id`；`send` FormData `session_id`+`content|image`；跨 session poll → `FORBIDDEN`。
- API 存裸 HTML；前端 `memberEscape` 挡会员 XSS。

## like id 假 SQLi

| id | 结果 |
|----|------|
| `1` / `1 OR 1=1` / `1' OR '1'='1` | 当 int 1 切换 like |
| `2-1` / `1.9` | 落到 2/1 |
| `abc`/`0`/`-1`/`99999` | 该动态不能点赞 |
| sleep 串 | 无延迟 |

## Admin（共用 FFSID · 2026-09-24 深挖）

- 存在页：`users` `moments` `support` `settings` `online` `staff`（登录后）；`plans/members/dashboard/home.php` 曾 404
- **会话差分（硬）：**
  - 游客 `/admin/users.php` → **302** `/admin/login.php`
  - 会员 FFSID → **403** `没有权限`（已登录，非 admin）
  - 会员 CSRF === 后台 `_csrf`（同 48hex）；无 role 写 admin 仍 403
- 主题弱口令 + 少量 SQLi（`admin'--` 等）→ 统一「账号或密码错误」/15 分钟锁；**停喷**
- mass-assign / Device-ID / Host / Method-Override **未**抬 role
- 提权目标：`role=admin|support` 或后台口令或 RCE

## 上传 RCE 假阳性

polyglot 写入 `/uploads/moments/.../*.jpg` 后：
- `Content-Type: image/jpeg`，魔数 `FF D8`，body 含字面 `PWN`/`<?php` = **静态文件**
- `path?.php` / `%00.php` 未变成短文本 exec
- **真 RCE 判据：** 非 image CT + 无图魔数 + 可控短输出（如仅 `PWN`）

## JS CONFIG（首页内联）

```js
CONFIG={inviteCode:"7777777", telegram:"https://t.me/feifei987654321",
  registerUrl:"https://97o3.my", apkUrl:"#"}
REGISTER_LINES: 97o3.my / 97j7.cyou / 97f8.bond / 97u8.icu  // 评估时无 A 记录
```

`invite_code` 字段未在限流期验证出旁路；线路域 Host 打源站 IP 仍回同一 SPA。

## 勿做

- 长喷 admin/RDP/MySQL
- 对唯一 live jar `logout` 不备份
- 把会员端已 escape 的 UGC 报成高危 XSS
- 把 like 整型强转 / 图内嵌 PHP 字节 报成 SQLi/RCE
- 把会员 403「没有权限」写成「未登录/未共用会话」
- 锁面下打同 /24 其它 IP 当主线

## Loot 路径（本机战役）

`/root/loot_202_95_8_69/REPORT.md` · `retry_member.cj` · home/main.js/moments/plan dumps。
