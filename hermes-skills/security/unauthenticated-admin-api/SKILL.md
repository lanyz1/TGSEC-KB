---
name: unauthenticated-admin-api
description: >-
  测绘引擎·管理API整面未鉴权。FastAPI/OpenAPI后台。openapi.json列路由→无Token直读。
  422 鉴权判据（缺字段 422=无鉴权、401=有守卫）；未授权 管理接口 直读/直写。
---

# unauthenticated-admin-api（测绘引擎）

目标须在 `config/scope*.json`。本库已有专链时专卡赢。

## 真源

- 长文：`docs/learning/shizhan-pack/skills/redteam/unauthenticated-admin-api/SKILL.md`
- 手法：`docs/playbooks/业务API未授权与越权手法.md`
- 工具：`python3 tools/ops/core_web_surface_probe.py --help`
- 路由：`python3 tools/ops/shizhan_pack_route.py --name unauthenticated-admin-api`

---

# 管理 API 未鉴权 · OpenAPI 直读手册

> 应对 FastAPI 后台/管理面板（标题含"管理后台"、Vite 单页+FastAPI 栈）。核心：**`/openapi.json` 或 `/api/docs` 把全部管理路由列出来 → 不带 Authorization 直打照样 200 → 等同超管读数据面**。

## 目标判定（先认栈，别撞登录）
- `GET /` 返回 `<title>XX管理后台</title>` + Vite `/assets/index-*.js` → 是管理面板，不是会员站。
- 下一步按 FastAPI 默认探文档，不要扫 WordPress。

## 文档面（未登录）
| URL | 用途 |
|-----|------|
| `GET /openapi.json` | 200 JSON，`info.title` 暴露系统名，全部 path 落表 |
| `GET /api/docs` | Swagger UI |
| `GET /health` | 存活探测 |

## 证明"未鉴权"（关键）
对每条管理 GET（及无破坏的 POST）发请求：
- **不带** Authorization / Cookie
- Host/Origin 用站点自己的即可

对照：若鉴权正常应 401/403；本案全部 **200**。

常见未鉴权管理口（FastAPI 后台族）：
```text
/api/admin/stats
/api/admin/accounts
/api/admin/accounts/{id}/download
/api/admin/bots（含 token 字段）
/api/admin/system-config（api_id/api_hash/路径）
/api/admin/message-config
/api/admin/change-credentials
/api/admin/restart
```

## 每口做什么
- `stats`：先拿数字（total/active/inactive/unauthorized/two_fa_enabled）。
- `bots`：Bot Token 从这里出。只做 getMe 验活，**改 webhook 是破坏面先问**。
- `accounts`：手机号/UID/2FA/状态。`batch-check` 探活可能惊动号；DELETE 毁库存，**默认不要打**。
- `system-config`：api_id/api_hash/session 目录/webhook 基址，按泄露处理。
- `login`：字典未中也要记录（阴性不能结案：读口已把数据吐完）。
- `restart`/delete/change-credentials：**移出默认脚本**，误触会重启服务。

## 前端 JS 陷阱
JS 里若有 `axios.defaults.headers` / `Bearer`，只说明客户端打算带；**服务端没验**。以无头 curl 为准。

## 诚实纪律
- 未鉴权 ≠ 破解了密码；弱口没打中不影响"数据面已拿"。
- 误触 restart 后服务恢复，不要当"已稳定 RCE"。
- Bot Token/api_hash/账号表按已泄露轮换。

## 变体：未鉴权失败 → 弱口令登录 → 配置泄露横向（Wenfxl 实战）
未鉴权口若 401/403，别放弃，转两条路：弱口令 + 文档面继续挖。

### 攻击链（2026-08 Wenfxl Codex Manager 实战验证）
```
1. 扫出 FastAPI 特征（uvicorn + /docs）
2. openapi.json → 101 端点全暴露（含未授权 /api/system/version）
3. 未鉴权口 401 → 试 admin/admin 弱口令登录 → 拿 token
4. 带 token 全量导出：accounts/config/mailboxes
5. config 里翻出 Cloudflare API Key + Clash 代理池 + 邮箱系统 → 横向接管
```

### 弱口令字典（管理面板优先试）
```text
admin/admin  admin/123456  admin/admin888  admin/123  root/root  test/test
```
管理面板（标题"管理后台/Manager/Admin"）优先 admin/admin，命中率最高。

### 配置泄露 → 横向利用清单
拿到 `config.json`/`config_full.json` 后按值翻：
| 字段 | 利用 |
|------|------|
| `cf_api_key` + `cf_api_email` | 验证 Cloudflare 账号 → 域名/Worker/DNS/邮件路由全控 |
| `admin_token`/`admin_auth` | 通用鉴权 token，试在其它口复用 |
| clash 订阅 URL/token | 代理池提取，换出口 IP |
| 批量账号表（email+password） | 上游资源，image2api/CPA 平台复用 |
| 邮箱系统 webhook_secret | 临时邮箱 → 批量注册链路 |
| Worker 源码 | 读取 = 拿到反向代理逻辑，可改可部署 |

### Cloudflare Key 验证（拿下后先验）
```bash
# 用 cf_api_email + cf_api_key 查账号
curl -s "https://api.cloudflare.com/client/v4/accounts" \
  -H "X-Auth-Email: <email>" -H "X-Auth-Key: <key>"
# 列域名
curl -s "https://api.cloudflare.com/client/v4/zones" \
  -H "X-Auth-Email: <email>" -H "X-Auth-Key: <key>" | jq '.result[].name'
# 列 Worker
curl -s "https://api.cloudflare.com/client/v4/accounts/<acct_id>/workers/scripts" \
  -H "Authorization: Bearer <key>"
```
验证通过 = 域名 DNS / Worker / 邮件路由（Catch-all → 临时邮箱）全控，这是重度泄露。

### 教训要点
- openapi.json 列出的口不止数据面，还有 `/restart`、`/change-credentials` 等破坏口，误触会重启/改密，**移出默认脚本**。
- "admin/admin 能登录" 本身是高危项（弱口令），即使数据面没多大价值也是确认漏洞。
- config 里的凭据常是**一套复用到多处**（cf key 同时当 cloudmail admin_password），拿到一个等于一串。

## 422 探针：错误码暴露鉴权从未执行（2026-10 141.164.60.204）
- FastAPI 接口回 422（字段缺失）而不是 401/403 = 鉴权依赖在验证层之后，根本没跑
- 探法：不带任何凭据直接发空 body，观察是 401（有鉴权）还是 422（先验参）
- 422 时把 body 补全（哪怕伪造 uuid）→ 多数直接 200 出数据
- 判据：同时存在 401 与 422 两种响应 = 鉴权按路由遗漏，按路径逐个试

## 27 端点数据面 + 写端点接管（2026-09 Titan Dashboard 实战）
- 空 cookie 打 `/api/*` 全集 → 27 条 200，含用户/订单/配置；写端点同样无鉴权 → 建管理员、改配置
- TG Bot Token 随会员档案直接返回（未脱敏）→ `getMe`/`getUpdates` 验证活性，可接管告警频道
- 判据：GET 与 POST 都不带 Cookie 均 200；建出的管理员能登录
- 顺序：先只读探测全量，再挑一个写端点做最小验证（建一次性账号，事后删）
