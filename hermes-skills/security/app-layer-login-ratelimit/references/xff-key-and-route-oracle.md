# XFF 限速键 · 全局 401 写中间件 · 真路由 oracle

**锚点案例：** `https://qilin.7scloud.eu.org/login`（2026-10-02）标题「记账账单系统」。

## 指纹摘要

| 项 | 值 |
|----|-----|
| 登录 | `POST /login` 仅 `secret=`；placeholder「输入管理密码」 |
| 失败 | `密码错误，请稍后重试` |
| 锁 | `登录尝试过多，请15分钟后再试` |
| 会话 | 成功 `auth=`；`GET /logout` 清 cookie |
| CSRF JS | 读 `_csrf_token` → `X-CSRF-Token`（未登录可能无 cookie） |
| 健康 | `GET /health` → `{"status":"ok","timestamp":"…微秒"}` |
| CDN | Cloudflare only；源站未暴露（疑似 Tunnel） |
| 真页 | `GET /` `/admin` `/group/{int}` → 302 `/login` |
| 真 API | `GET /api/bills/{数字}` → `401 {"error":"unauthorized"}` |
| 假 API | `GET /api/bills`、`/api/xxx/1`、`/api/bills/abc` → HTML 404 ~8739B |
| 写中间件 | `POST/PUT/DELETE` **任意** path → 同形 401 JSON |
| PATCH | 统一 500 美化页（无栈） |

## XFF 差分实录形状

```
基线 peer 锁 → 「登录尝试过多…」
X-Forwarded-For: 203.0.113.10 + secret=unique → 「密码错误」  ← 信任 XFF
X-Real-IP / True-Client-IP 同效
CF-Connecting-IP: 8.8.8.8 → Cloudflare 403
Tor 同出口 192.42.116.51 粘锁；NEWNYM 到 185.220.101.37 可重新「密码错误」
```

轮换 XFF 打 ~70 主题词（qilin/7scloud/jizhang/admin123/年份…）→ 全 ERR，**停喷**。

## 路由 oracle 最小矩阵

```
GET  /api/bills/1     → 401 JSON     = 真
GET  /api/bills/2     → 401 JSON     = 真（id 通配）
GET  /api/bills/abc   → 404 HTML     = 类型约束
GET  /api/bills       → 404 HTML     = 无集合路由或未挂
GET  /api/nope        → 404 HTML     = 不存在
POST /totally_unknown → 401 JSON     = 全局写中间件（非路由）
POST /api/bills/1     → 401 JSON     = 与未知 POST 同形，需 GET 才能证存在
OPTIONS /api/bills/1  → Allow: HEAD, OPTIONS, GET
OPTIONS /login        → Allow: HEAD, OPTIONS, GET, POST
```

## 旁品牌 / Wayback（recon only）

- TLS SAN：`7scloud.eu.org` + `*.7scloud.eu.org`（Google WE1）≠ 源站 IP
- `freecloud.7scloud.eu.org` → `15.235.227.117`（dasg1.hostypanel **共享机**）：
  - 默认页；**3306** MariaDB `10.11.18-cll-lve-log`；root 常见密 1045
  - FTP 21 Pure-FTPd TLS，**禁匿名**；22/2222 常超时
  - 探 `/webmail`/`/phpmyadmin` 后对本出口可整站变 **cPGuard** 人机页（同 hash ~33KB）— 旁机 soft 探要控频
  - Host `qilin…` 打到该 IP ≠ qilin 源站
- Wayback：`123.7scloud.eu.org` 历史 = Vue **WebSSH/文件管理**（`/file/list` `/term?sshInfo=` `/check`，Render+CF），现 NX
  - **禁止**把 123 路径当 qilin 同源交叉主线；打过去无命中才算证伪
- `hk.5scloud.eu.org` → `38.47.106.232`（与 wzhk 同 IP 线索）：端口常不通，只记账
- 不同 A 记录 = 邻机；锁面不切主线除非用户明文

## 认证绕过死端（本型已证伪，别空转）

- 路径编码 / `..;/` / 大小写 / `%00` / X-Original-URL / Method-Override / Host localhost：无效
- `auth=1|true|admin|base64|jwt-none`：仍 302 `/login`（服务端 token）
- 全角/西里尔 `secret`（`ａｄｍｉｎ` / `аdmin`）→ **500 美化页无栈**（unicode 炸处理，非后门）
- 嵌套墙：`GET /group/{int}/stats` 等同 `GET /group/{int}` → 302 `/login`（进门后有嵌套，门外无数据）

## 报告口径

- 中危：限速信任 XFF（可无限试密）
- 低：`/health` 未授权；旁机 3306 暴露（若授权旁线）
- **非**高危：全局 POST 401、主题密未中、WebSSH 历史子域、cPGuard 页
- 运营三档（数据/接管/资金）：未打穿就直说没有；「继续深挖」= 换未测格子或要密码/扩 scope，不是加长字典
