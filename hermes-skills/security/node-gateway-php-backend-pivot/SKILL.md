---
name: node-gateway-php-backend-pivot
description: Use when Express fronts a PHP/Laravel API.
---

# Node/Express 网关 + PHP 后端 渗透打法

## 一、先分层，别把网关 404 当路由不存在

| 响应 | 含义 |
|---|---|
| `{"ok":false,"error":"Not Found"}` (32B) | **Express 自身 404** ⇒ 该前缀没挂载，不代表后端没有 |
| nginx 默认 404（常带 `<!--` 尾巴） | 网关放行了，**PHP 后端**回 404 |
| `{"status":"error","code":401,"message":"登录已过期"}` | 全局中间件排在路由前 ⇒ 不存在的路径也 401，端点存在性被遮蔽 |
| 分页器 `links` 写出 `/api/user/...` | 请求是 `/api/jmy/user/...` ⇒ 网关做过 rewrite，这就是**后端真实前缀** |

用「Express 32B vs nginx/PHP 404/401」三种形状当尺子批量判定，别只看状态码。

## 二、推断映射

拿已知可用端点试两三种前缀形态。常见结论：网关把
`/api/jmy/user/<X>` → PHP `/api/user/<X>`，而 `<X>` 自身已含控制器名（`user/info`、`trade/list`）。
所以 `.../api/jmy/user/info` 会 404，正确的是 `.../api/jmy/user/user/info`。

## 三、挂载前缀穿越（path.join 未规范化）

```
GET /api/jmy/user/%2e%2e/user/user/info   → 200（等价 /api/user/user/info）
GET /api/jmy/user/user/user/info          → 404 Express
```

- 单级 `..` 退到 `/api/*`，可枚举后端其它命名空间
- 双级 `..`、`%252e%252e`、`..%2f`、`..;/`、`....//` 多被挂载前缀校验拦回 404
- 命中后先确认能否绕过鉴权（多数只复制映射，不提权）
- 命名空间枚举：`/api/jmy/user/../<seg>/` × 百词表，全 404 就说明后端只有一套路由文件

## 四、WebSocket 聊天面（这类平台的真数据出口）

信封：`{type|action, todo, message, token}`

```
{"type":"auth","token":JWT}   → 回完整 user 对象(id/username/phone/real_name/invite_code/余额)
{"type":"get_room"}           → 房间列表，常带 admin_name(运营真名)/bond/在线数
{"type":"room","todo":"join","message":{"room_id":N,"password":S}}
   → 4001 请输入房间密码(空/0/[]/{}) ; 4002 密码不正确 ; 200 返回 messageList
```

- 每条消息的 `sendUser` 是完整用户对象 ⇒ **进房即批量拿手机号**
- 房间密码普遍无速率限制（实测 40+/s 无锁号）：先扫 4 位纯数字，再上字典 + 多连接并行
- `subscribe` 自定义频道一般被拒，别指望绕过密码；`get_room` 只给房间元数据
- CF 对同一出口会拦 WS 握手，需换出口/代理重连

## 五、其它固定套路

- 响应头 `x-ratelimit-limit` 常被配成天文数字（见过 20000000）⇒ 限流形同虚设，先看一眼再谈爆破成本
- 详情类接口（`out/detail/{id}`、`recharge/detail/{id}`）多按 token 过滤，未命中回 `400 数据未找到`；**先用自己名下记录校准 id 区间**，否则全站 400 是假阴性
- 免鉴权单参端点（如 `question {phone}`）常是三态预言机：未注册 / 已启用 / 已停用，且 `phone` 无长度校验
- 对象桶 `AccessDenied` 时先试已知 key（下载页/APK），再试 `www.zip`/`backup.zip`/`.env` 一类备份名
- 昵称类写入字段常限长 20 字，够放 `<svg onload=print()>`（正好 20），放不下带回连的载荷

## Pitfalls

- 把 Express 的 32B 404 当成「路由不存在」⇒ 整片后端面漏掉
- 把 nginx `try_files` 兜底页当成「目录/文件存在」
- `nmap -p- --min-rate 3000` 得满屏开放端口 ⇒ 假 SYN-ACK，必须 `connect()` 精确复核
- 账号级锁号：累计 4 次错误口令即锁 24h，撞库每号最多 3 次
