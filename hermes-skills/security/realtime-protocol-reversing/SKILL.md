---
name: realtime-protocol-reversing
description: "Use when cracking a proprietary WS/RPC game backend."
---

# 私有 WebSocket / 实时 RPC 协议逆向

目标：不靠猜字节，**让真客户端自己发包、在旁边抓帧**，然后把业务面从 WS 迁到更好打的通道（通常是 HTTP RPC 桥）。

## 步骤

1. **先确认到底是 WS 还是 HTTP。** 在浏览器里跑真客户端，看 `performance.getEntriesByType('resource')`，过滤 `router|pomelo|rpc|api`。若客户端有 `/xxx/router/pomelo` 这类调用，业务根本不走 WS——别再去逆封包。
2. **装只读钩子抓真帧**（不注入伪造业务请求）：
   ```js
   // 必须在页面脚本之前注入（CDP Page.addScriptToEvaluateOnNewDocument）
   const O = WebSocket.prototype.send;
   window.__frames = [];
   WebSocket.prototype.send = function (d) { window.__frames.push(['out', d]); return O.apply(this, arguments); };
   window.__mk = (ws, u8) => ws.send(u8);   // 需要时复用页面自己的 socket
   ```
   同时 hook `fetch`/`XMLHttpRequest`，把**完整请求头**抄下来——裸拼头直连多半 401。
3. **注入已有凭据触发自动登录**：把真实 `access-token` 写回客户端自己的 storage 键（如 `xxx_base.token`）后 reload，比手工构造登录包省一小时。
4. **解码帧**：常见外层 `[type][3字节大端长度][body]`；1=handshake 2=ack 3=heartbeat 4=data。内层常见 `[reqid varint][type<<1|compressRoute][路由(2字节ID 或 len+str)][JSON]`。
5. **判定是不是「只推不收」**（见下），是就转 HTTP 桥，别继续试。
6. **在 HTTP 桥上做路由级审计**：先 dump 路由表（握手包里的 `sys.dict` / `routeToCode`），再按白名单逐条只读调用，做自作用域 vs 目标 uid 的对照。

## 关键坑（每条都栽过一次）

- **登录 200 之后全部静默 = 连接器「只推不收」，不是编码错。** 判据：重发 login、换源 IP、换新令牌、心跳 pong 已回，全无响应，且客户端自己的 out 帧只剩心跳。此时继续调字节序是纯浪费时间——这套架构 WS 只做广播，业务走 HTTP RPC 桥。
- **心跳方向是单向的**：服务端推 heartbeat(3)，客户端回 ack(2)。回 3 会 ping-pong 风暴。
- **长度字段是 3 字节大端**，少这 3 字节服务端静默丢包（不报错、不断连），这是最容易误判成「协议对不上」的根因。
- **同一张路由表 ≠ 同一张挂载面**：握手包里的 `sys.dict` 是全量路由，但每个传输只挂自己的命名空间。HTTP RPC 桥常只挂业务命名空间（如 `hybird.*`），`game.*` / `connector.*` / `http.*` 即使明明在表里，走 HTTP 也统一回 `{"code":404,"tips":"路由错误"}`。判据：拿表里两个不同命名空间的路由各打一次，命名空间外全 404、内正常 ⇒ 是挂载差异不是路由不存在，改走 WS 传输，别对着路由名 fuzz。同理，旧构建签发的 token 在新网关回 `400`（解析层拒）、在游戏服 WS 回 `410 invalid token`，都不代表「不校验过期」。
- **`__console__` / `__gamemaster__` 这类路由名过不了网关的名字校验**（要求 `模块.动作` 三段式），回「路由消息格式错误」只说明名字格式不对，**不说明路由不存在**。路由表里没有 admin/gm 名字时，按名字 fuzz 后台路由收益为零。
- **IDOR 普查基线必须用同租户/同 partner 的真 uid。** 自造游客号通常属于另一个 partner，对每条路由都返回「none same partner / 无权限」，整轮普查会变成 100% 假阴性（实测 100+ 条只读路由全判「自作用域」，换真 uid 后才出命中）。
- **私有聊天的频道键注意分隔符**：常见 `<小uid>:<大uid>`（冒号）。下划线/短横线/直接拼接都回 200 但 0 命中——「格式写错」和「没有数据」在响应上长得一模一样。
- **`uid` 参数被忽略 ≠ 有 IDOR**：先用两个**已知真实** uid 对照（自己 vs 同租户他人），只有他人数据真实回显才算成立。顶层 `uid`/`session`/`user` 注入、`uid`/`x-uid` 头、无令牌，通常全部被拒；`$ne`/`$gt`/`$exists` 会被类型校验挡掉。

## HTTP RPC 桥的形态

- 端点通常形如 `POST /user/router/pomelo`、`/api/rpc`、`/gateway/invoke`
- body：`{"router":"模块.动作","msg":{...}}`，头带普通用户令牌即可调**整个后端路由表**
- 响应常直接是后端 ES/Mongo 的原始结构（`{context:{total,hits:[...]}}`）——dev 实例的报错会直吐索引名，参数语义探测优先在 dev 上做
- 路由名若被校验卡住，先用客户端字典里**确实存在**的一条做正对照，确认是鉴权问题还是格式问题

## 纪律

只调只读路由；写类（`bind*/change*/transfer*/set*/del*/create*/buy*/payout*/send*/update*`）一律不碰，误发即停机并如实记录。抓到的令牌、密钥、PII 只在本地使用，不外发、不入报告正文。

## 游戏服 HMAC 密钥从公开桶取出 → 协议复刻（2026-09 GOODLUCK777 实战）
- S3 公开桶里躺服务端 Node 源码 + `HMAC_SECRET`，签名算法 `hmac_sha256(secret, `${cmd}|${ts}|${body}`)`
- 复刻：Node 侧用同算法签名，直接调游戏服 opcode；无需逆二进制
- 私有协议字段从源码 `proto/` 里直接读，比抓包快 10 倍
- 判据：本地签名请求返回 `{"code":0}` 并改变游戏状态
