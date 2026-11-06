# 案例课：TG 筛号平台 — 注册送超管 + 会话批量导出即接管

> 来源：报告包 pack-20261022（2026-10）· 域：api-security

## 一句话

`POST /api/auth/register` 无字段白名单，注册时直接附 `role:"admin"` 就成管理员；普通用户也已能读 `/api/accounts`（含 `session_file` 路径、`api_id/api_hash`）、`/api/proxies`（代理明文口令）、`/api/api-credentials`；最后 `POST /api/accounts/batch-export` 回一个 ZIP，里面 `{phone}.session` + `tdata/` + `{phone}.json`，Telethon 免密免 2FA 直接登号。

## 链

1. `POST /api/auth/register` body 加 `"role":"admin"` → 直接拿管理员 + 无限 quota（mass assignment）
2. 即便不改 role，仅"已认证"用户也能读：
   - `GET /api/accounts` → `session_file` 路径、`api_id` / `api_hash`
   - `GET /api/proxies` → 代理地址 + 明文口令
   - `GET /api/api-credentials` → 上游凭据
3. `POST /api/accounts/batch-export {"ids":[...]}` → 回 ZIP：
   - `{phone}.session` — Telethon SQLite，含 auth key
   - `tdata/` — `D877F783D5D3EF8Cs/key_datas` 等
   - `{phone}.json` — 元数据
4. 落地即可 import 登号，无需验证码、无需 2FA

## 判据

| 现象 | 含义 |
|---|---|
| 注册接口接受 `role`/`is_admin`/`quota` 等字段并生效 | 无白名单，直取超管 |
| 普通用户读管理列表 200 | 只有认证没有函数级授权（BFLA） |
| 导出接口回 ZIP 而非异步任务 ID | 直接可取，无需审批流 |

## 边界 / 坑

- 批量导出会触发 WAF：`429 → 502 → 443`（**TCP 通但 TLS 握手被丢** = IP 级封禁，不是服务挂了）
- 平台自带 SOCKS5 与免费代理池 0/294 可用 → 别在代理池上浪费时间
- 导出要限速 + 换出口，按批 20-50 个 ID 走，一次全量必封
- `.session` 与 `tdata` 二选一即可，`tdata` 需要对应客户端版本

## 检查清单

- [ ] 注册/资料更新接口逐个字段做 mass assignment 差分
- [ ] 用普通账号遍历所有 `/api/*` 管理列表，看 200 还是 403
- [ ] 找 export / download / batch 类端点
- [ ] 拿到 ZIP 先本地校验 session 可用性（别在平台侧反复登录）
- [ ] 限速 + 轮换出口，避免 IP 级封禁
