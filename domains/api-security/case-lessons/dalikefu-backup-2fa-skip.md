# 案例课：目录 403 但文件直读 + 2FA 不校验 = 客服后台接管

> 来源：报告包 dalikefu（2026-10）· 域：api-security / PHP 客服工作台

## 一句话

`/data/` 目录列表 403，不代表文件不可读——`/data/backups/<name>.sql.gz`、`/data/app.db` 直接 GET 200。备份里有管理员 bcrypt 与**明文 TOTP 密钥**；登录接口密码对即过，`code` 缺失/空/`000000` 全成功。

## 链

1. 目录 403 → 按命名规律直接请求文件：`/data/backups/<app>-YYYYMMDD-HHMMSS.sql.gz`、`/data/app.db`
2. 备份里取 `agents` 表：bcrypt + `totp_secret` + role
3. 离线破解 bcrypt（cost=12 约 20+/s，小字典即可）
4. `POST /api.php?a=login`（先取 CSRF）→ `{"ok":true}`
5. `code` 缺失/空/`000000` 均成功（`totp_enabled=0` 无感；启用后仍不校验）
6. `WBSESS` 会话 → `api.php?a=state` 返回 `role=admin`
7. 后台动作全集：`agent_list/stats/backup_list/settings_get/qr_list/faq_list/tg_status/tg_chats/tg_mentions/tg_messages/file.php`

## 关键点

- `file.php?id=` 可读真实附件
- `settings` 表常有 bot_token、webhook_secret、tg_api_id/hash、收款地址 → 控制机器人
- `/logs/error.log` 公开可读：SQL 异常、PHP 行号、备份操作时间线
- `login_attempts` 表 0 行 = 无登录审计，接管不留痕

## 边界

- 2FA 不校验只在密码正确后可见；没密码先解决密码
- 备份文件名规律要先从 error.log/页面 JS 找
- 别把目录 403 当不可读，也别把 200 当一定可解析

## 检查清单

- [ ] `/data/`、`/backup/`、`/logs/` 目录 403 后按名直取
- [ ] 备份表结构与 TOTP 字段
- [ ] 登录 code 空值绕过
- [ ] 后台 API 动作枚举
- [ ] 登录审计缺失

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
