---
name: tg-cloud-panel
description: >-
 授权目标上 Telegram 云控/营销面板杀伤链：弱口 admin、openapi、session/Fernet、
 Google cookies、Vite@fs、Portainer/Redis/WolfStack/etcd 旁路，目标是可登录 TG session。
 用户提到 TG云控、Sticker Promo、TG Panel、Auto Sender、feijikong、relay-token、
 session_string、gAAAAA、云控面板、:8000/:8002/:8020/:8085、
 your_secret_key、/proxy/list、/admin/users、Session ZIP 时使用。
  先认族：JWT+/proxy/list 走 jwt+rbac，禁止打 Fernet/OSS；
  首页「系统选择」+ /tgcloud_pc + /customer 改读扩展包 tg-cloud-control-pentest；
  main.wasm / goEncrypt / 掩码票 eyJhbG...XXXX 走第四族（浏览器 oracle，禁止先拆 WASM）。
 Fernet 解密切 fernet-session-decrypt；Bot webhook 越权仍走 tg-bot-webhook-hijack。
---

# TG 云控面板杀伤链（Cursor Skill）

## 何时用

- 端口/标题像 Sticker / TG Panel / Auto Sender / Forwarder / 云控
- 用户要「可登录 session」而非手机号列表
- FOFA/扩线打到同类面板且已在 scope
- 出现 JWT `your_secret_key`、`GET /proxy/list`、`GET|PUT /admin/users`、Session ZIP

## 认族（三族，禁止混打）

| 指纹 | 走 | 不要做 |
|------|-----|--------|
| `gAAAAA` / `:8000/:8020` / Fernet | 本卡 → `fernet-session-decrypt` | 当 JWT 弱钥结案 |
| 「系统选择」`/tgcloud_pc` `/customer` / OSS STS | 扩展包 `tg-cloud-control-pentest` | 打 Fernet / `/proxy/list` |
| JWT `HS256` + `your_secret_key` / `/proxy/list` / `/admin/users` / Session ZIP | **本卡认族** → `jwt_gql_probe` → `rbac-bypass-authz` → 对象矩阵 | 打 Fernet / OSS STS |
| `/main.wasm` + `window.goEncrypt` + 掩码票 `eyJ…XXXX` | **第四族** → 有头浏览器 oracle + `jwt_gql_probe --token 掩码票` | 先逆向 WASM / 当坏 JWT 丢掉 |

JWT 第三族顺序：手工先试 `your_secret_key` → 伪造 admin → `GET /proxy/list` `GET /admin/users` 当未授权读 → Session ZIP 收明文 2FA → 撤权后枚举 `ver`/`version`/`v`/`jti`（五次内复活才报）→ 用户表先捞 IOC 再改本轮标记号。成功口径仍是 **可登录 session**，不是手机号/代理条数。

## 真源

1. `docs/playbooks/TG云控面板杀伤链.md` · 第四族 `TG云控Go-WASM掩码票手法.md`
2. `tools/ops/tg_cloud_panel_probe.py`
3. 下游：`fernet-session-decrypt` · `vite-fs-read` · `wolfstack-hardcoded-secret` · `etcd-unauth`；第三族另接 `jwt-bypass-pentest` · `rbac-bypass-authz`
4. 案卷金标准：`exports/bot-recovery/feijikong_20260813/STATUS.md`（Fernet 族）

## 强制步骤

1. 目标在 scope。先按上表认族，JWT 第三族不要跑本卡弱口当主刀。
2. ```bash
 python3 tools/ops/tg_cloud_panel_probe.py -u http://IP:端口 --case <案卷>
 ```
3. 有 login_hits → 枚举 accounts；见 `gAAAAA` → **立刻**切 `fernet-session-decrypt`（并行 `vite-fs-read` 挖 KEY）。
4. API 有号无 session → 不要结案；打读盘/RCE/Portainer/WolfStack。
5. 明文 session 外连验活；证据：`接管/` + STATUS（LIVE 数/阻塞项）。
6. 成功口径是 **可登录 session**，不是 852 手机号。

## 不要做

- 未授权扫公网面板网段
- 只堆手机号当接管
- Fernet 未解密就报「已拿到号」
- 生产改 2FA/踢设备不先对齐目标号

## 衔接

- Fernet → `fernet-session-decrypt`
- `:3000` Vite → `vite-fs-read`
- 容器主机 → `wolfstack-hardcoded-secret` / Portainer / `etcd-unauth`
- Bot 管理面越权 → `tg-bot-webhook-hijack`
- 「系统选择」双应用 / OSS STS / 客服 chat_token → `docs/learning/extended-pack/skills/tg-cloud-control-pentest/SKILL.md`
- JWT `your_secret_key` / `/proxy/list` / `/admin/users` / Session ZIP → `jwt-bypass-pentest` → `rbac-bypass-authz` → 对象矩阵（勿打 Fernet/OSS）
- FastAdmin Shop `/shop_hq` 出海后台（filter+op / tdata zip）→ `fastadmin-shop-tenant-bola`
- 解出的明文 session 入库/清库 → `tg-account-library`

## 注册即管理员 + 会话导出即接管（2026-10 TG 集群）
- 公开注册体直接带 `role:"admin"` → 无限配额管理员，再读全量账号库与代理凭据（服务端不校验 role）
- `POST /api/accounts/batch-export` 返回真实 Telegram `.session`（SQLite）+ tdata ZIP → 免密登录，无需破口令
- 坑：面板口令强随机（5000 次全灭）；RDP 静态 banner 桩 = 假目标
