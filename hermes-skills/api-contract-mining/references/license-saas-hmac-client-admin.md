# License SaaS 授权控制台：admin/agent/client 三面（2026-09-20）

指纹：标题「License SaaS 授权控制台」；Vite+Naive UI；`/api/setup/status` → `{"installed":true}`；`/api/health` 200。

## 路由族
- Admin：`POST /api/admin/login`；`GET /api/admin/{apps,users,agents,card-types,stats,cloud-vars}`；`POST /api/admin/cards/generate`
- Agent：`POST /api/agent/login`；`GET /api/agent/me|scopes`；发卡/余额日志
- Client（**全要 HMAC**）：`/api/client/{app-info,cloud-vars,register,login,card-login,recharge,unbind,account-unbind,card-unbind,heartbeat}`
- Setup：`POST /api/setup/admin`（已 installed 则不能重建）

## 登录
- admin/agent：JSON `{username,password}`；错密 `账号或密码错误`；缺 token 读接口 `missing token`。
- 无用户枚举差异（同文案）。

## 客户端签名（文档写在 SPA 里）
- 头：`X-App-Key` `X-Timestamp`（unix 秒）`X-Nonce` `X-Signature`（HMAC-SHA256 **小写 hex**）
- 原文（`D1`）：`METHOD\nPATH_WITH_QUERY\nTIMESTAMP\nNONCE\nBODY_JSON`
- GET：body 空字符串，**仍保留最后换行语义**（文档：「GET body 为空，但签名原文末尾仍要有最后一个换行」）—— 变体要 A/B。
- 密钥 = 软件 `client_secret`（仅 admin 软件管理可见）；示例 app_key `demo-app`。
- 预言机：
  - `软件不存在或已禁用` = app_key 错
  - `签名校验失败` = **app 存在**但 secret/原文不对
  - `缺少客户端签名请求头` = 没带头

## 打法
1. 未授权探 setup/health/admin 登录 oracle。
2. 用错误 secret 扫 app_key：区分「不存在」vs「签名失败」→ 得到存活 app（常有 `demo-app`）。
3. 无 client_secret 时 client 面打不动；转 admin/agent 喷或同源 Redis（若 6379 开着且弱口令）。
4. 同机 openresty:80 常 404 默认站，别当独立面板。
