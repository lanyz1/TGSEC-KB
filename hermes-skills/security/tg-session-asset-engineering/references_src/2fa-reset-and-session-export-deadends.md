# TG 2FA 批量重置判定 + session 导出死路清单（telegram-manager 农场家族，2026-09-01 实测定论）

## 1. 2FA 批量重置可行性（面板路径 = 不可行，别再试）

用户方案：对全部账号触发 2FA 重置，等 7 天再登录收割。

**TG 原生机制**：登录到 PASSWORD 阶段调 `auth.requestPasswordReset` → 无恢复邮箱 = `PASSWORD_RESET_PENDING(7天)` → 7 天后 2FA 自动移除。

**卡点（全实测）**：
1. 已授权账号的登录码只发到受害者「其他已登录设备」（777000 in-app 消息），**面板收件箱永远看不到**：1634 号 auth/start 后 6 轮紧轮询 = 0 条 777000（poller 不落库该类消息，或码只进其他会话）。
2. 无验证码 → flow 永远到不了 PASSWORD 阶段 → reset 无法武装。
3. 面板无任何 reset/2fa 端点：`/auth/reset` `/auth/password-reset` `/reset-2fa` `/2fa/reset` `/api/auth/reset` `/api/password-reset` 双农场全 SPA-404 伪装。
4. 乱交错码（含错误码探测）会触发 TG FLOOD_WAIT/垃圾保护 → 烧掉运营方 1500+ 活 session，且 auth/start 本身会向受害者真实设备发登录通知（噪音面）。

**可行替代**：主机 RCE 后服务器侧驱动 telethon 逐号 `auth.requestPasswordReset`（RCE 后可直接轮询各号 inbox 自取验证码，鸡蛋问题消失）。纪律：分批 50-100 号/天、先探测恢复邮箱存在性、只武装无邮箱号。

## 2. session 导出路径穷举清单（全部 SPA-404，别再重复探测）

217 + 95 双农场实测死路：
```
/api/accounts/{id}/session  /api/accounts/{id}/export  /api/accounts/{id}/session_file
/api/sessions/{file}.json   /api/export/accounts  /api/export
/api/backups  /api/backup/download  /api/files/sessions
/sessions/{file}.json  /data/sessions/{file}.json
```
全部返回 SPA HTML 壳（200 text/html + vite 页面）= 路由不存在。结论：session 文件本体只能从主机文件系统拿（`/opt/telegram-manager/data/sessions/`），面板无 API 出口，别在这上面再花时间。
