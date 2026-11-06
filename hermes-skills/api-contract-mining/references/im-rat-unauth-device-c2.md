# iM / 陈瑞泽管理系统：未授权设备 C2 面（2026-09-20）

指纹：标题「iM后台管理系统」/ 文案「陈瑞泽管理系统」；Vite SPA + Express API；`baseURL` 默认 `/api`。

## 合约（主包 grep）
- 登录：`POST /api/auth/login`（需 username+password；库缺表时回「数据库查询失败: Table 'backsystem.user'…」= **路由存在**）
- 设备：`GET /api/devices`、`GET /api/devices/stats`、`GET /api/devices/{id}`
- 注册：`POST /api/devices/register` → **201**（常无鉴权）
- 删除：`DELETE /api/devices/{id}` → **200**（常无鉴权）
- 控制（均 POST，body JSON）：
  - `/api/devices/{id}/list-files` `{path}`
  - `/api/devices/{id}/read-file` `{path}`
  - `/api/devices/{id}/write-file` `{path,content}`
  - `/api/devices/{id}/create-file` / `create-directory` / `delete-file`
  - `/api/devices/{id}/keyboard-log` / `keyboard-log-filter`
  - `/api/devices/{id}/get-contacts`
  - `/api/devices/{id}/start-screen-capture` / `stop-screen-capture`
  - `/api/devices/{id}/screen-control` action ∈ `wake_up|screen_off`
  - `/api/devices/{id}/black-screen` action ∈ `show|hide|toggle|update_message|status`
  - `/api/devices/{id}/start-app|stop-app|uninstall-app` `{packageName}`
- 配置：`GET /api/config/frontend` 常未授权；`GET /api/config/backend` 可能 500 缺表

## 闸门语义（别误判）
- 控制接口回 `设备未连接WebSocket，请确保设备在线` = **鉴权已过、只缺设备 WS**，不是 404 路由不存在。
- `screen-control`/`black-screen` 先校验 action 枚举（400 列合法值）再查 WS —— 用 400 文案抠枚举。
- 前端 WS：`of()` 默认 `ws(s)://location.host` + **`?type=web`**；`type=device` 给端侧。nginx 若未 upgrade，握手变 **HTTP 200 HTML** → 客户端连不上（本战役症状）。

## 打法顺序
1. `GET /api/devices` 落盘清单（型号/GPS/安装应用）。
2. `POST /api/devices/register` 证未授权写；`DELETE` 证删；**测完删掉自己的脏设备**。
3. 对清单 id 打控制 API：记录「仅 WS 门」证据。
4. 找真 WS：扫后端端口 / 反代配置；或伪造 `type=device` 上线后再打控制。
5. 登录链可并行，但 **未授权设备面优先交付**。

## 证据落点
`loot/host_<ip>_80/DEVICES.json`、`REGISTER_HIT.json`、`DEVICES_FINAL.json`。
