# Socket.IO RPC 后端:当「所有 REST 路径都 404」时(2026-09 实战)

配套脚本:`scripts/socketio_poll_client.py`(纯 HTTP 长轮询的原生 Socket.IO v4 客户端,无第三方库)。

## 症状

目标 App/SPA 的 bundle 里明明写着 API 主机,但对该主机的**每一个** REST 路径
(`/api/...`、`/v3/...`、`/`、`/health`)全部返回 404 / `Cannot GET` / `{"error":"Rota não encontrada"}`。

→ 高度怀疑:**这套后端不是 REST,而是把全部业务动作跑在 Socket.IO 的 RPC 上。**
盲猜 REST 路径会一条都打不中(本轮实测:8 个前缀 × 多个端点 = 全 404,零信息)。

## 1. 先拿客户端源码,再读它的 api 层

1. **找开发服务器**(这一条最容易被忽略,回报最大)。移动端/前端项目常把 dev server 裸奔在公网:
   端口 `8081`(Expo/Metro)、`3000`(Next/Vite/Open WebUI)。对 `/` 取 manifest 会直接给出 bundle URL。
   命中 `dev=true` → bundle 是**未压缩开发版 = 全量源码**(实测 7.79 MB)。
   见 `references/expo-metro-devserver-sourcemap.md`。
2. **重建源码树**。Expo dev bundle 的模块边界形如 `__d(function ...,"<src 路径>")`,
   拿源码路径字符串反查即可定位任意模块(`src/api/apiClient.ts`、`src/services/socketService.ts`…)。
   **反斜杠正则极易被转义搞坏 —— 优先用纯字符串定位**:`t.find("src/api/apiClient.ts")`,
   取该位置前面 N 千字符当模块源码。本轮在这上面白烧了好几轮。
3. **读 api 层而不是猜路径**。看它是把路径映射成 socket action(典型写法
   `request(action, payload, {token})`)还是真发 HTTP。**这一步决定后面所有请求的形态。**

## 2. RPC 协议(字段名必须逐字对齐源码)

```json
["rpc:request", {
  "requestId": "<ms>-<event>", "eventName": "<root>.<verb>",
  "payload": {...}, "idempotencyKey": "<ms>-<event>", "attempt": 0 }]
```

ack 回 `{ok, data, error:{message,statusCode,code}}`。

- **动作名是 `<root>.<verb>` 字符串**(`auth.me` / `conversations.list` / `videos.feed`),
  不是路径。从 api 层源码把清单抽全(实测抽出 30 个 verb)。
- token 走**命名空间 auth**:`40{"token":"<JWT>"}`,**不是 HTTP 头**。
- 客户端源码里若出现 `token === null ? connectPublic() : connect(token)`,
  说明存在"公共无 token 连接"通道 —— 值得单独探一遍。

## 3. Engine.IO 4 帧格式(轮询模式)

| 步骤 | 报文 |
|---|---|
| 握手 | `GET /socket.io/?EIO=4&transport=polling` → `0{"sid":"..."}`,**剥掉开头 `0`** 才是 JSON |
| 鉴权/连接命名空间 | `POST` body `40{"token":"..."}` |
| 发事件带 ack | `POST` body `42<ackId>["<event>",{...}]` |
| 读 ack | 轮询回包里的 `43<ackId>[...]`;一个包多帧时用 `\x1e` 切分 |

## 4. 三种响应语义必须分清

| 响应 | 含义 |
|---|---|
| `404 Unknown realtime action` | **动作名不存在**(枚举错了),不是权限问题 |
| `401 Unauthorized` | 未带 token / token 无效 |
| **`403 Forbidden`** | **token 有效但无权访问该资源** ⇒ 逐资源鉴权;**换别人的资源 id 得 403 = 无 IDOR** |

## 5. 打之前先定"入口",再只读枚举

- `auth.register` 若**公开可用**(只要 name/email/password)→ 注册一次性测试号拿 token,
  这是进数据面最便宜的门(与 `reset-token-disclosure-ato` 同思路)。
- `auth.me` 是**验证 token 真被接受**的最快回落点(返回自己档案 = 会话已建立)。
  常见坑:token 字段名猜错 → **打印响应全文**再取值。
- 然后**只跑读类动词**做矩阵:`get / list / listByUser / feed / messages / history /
  comments / discover / lobby / matches / search / me / find / next`。
  写类(create/save/send/delete/approve)一律不碰。
- 越权验证的正确姿势:**用自己的账号,把资源 id 换成别人的**(或换另一个账号的会话 id)。
  得到 403 就**如实写"鉴权健全"**;不要为了报告好看把空 `data:[]` 写成"发现"。

## 6. 别把空数据当"数据池"

`ok` + `[]` / `null` 只说明"动作存在、该账号无数据"。
判断后端**到底有没有真实数据**要看对象本身:`data:[]` 全空、UUID 形如 `aaaa…a1`,
媒体指向公共示例源(Google 示例桶 `gtv-videos-bucket` / Unsplash / `example.com`),
文案是"setup 演示"类占位串 → **这是种子/演示数据**。
正确结论是"**入口打通但当前不承载真实客户数据**",不是"拿到金库"。
(本轮就是这个教训:把可认证的样板后端当成了"客户聊天数据金库",必须自我更正。)

## 7. `presence:online` 不是全局枚举 oracle

在线/存在性广播通常**只推给有关系(好友/同群/同房)的用户**。实测监听 80 秒零事件
⇒ **不能**当全局在线用户枚举。要用户 id:回源码找 `users.search` / `listByUser` /
内容流里的作者字段,而不是靠监听广播。

## Pitfalls(全部本轮实测踩过)

1. **空 POST 当 keepalive 会打断 Engine.IO 会话** —— 服务端判定 payload 非法直接断连,
   之后所有请求返回 `null`。**不要发空包**;要让连接活着就正常轮询。
2. **ack id 切片写死 `p[3:]` 会在两位数时错位**(ack id ≥ 10 即解析失败)。
   正确:`rest = part[2:]`,数出前导数字长度,再 `json.loads(rest[i:])`。
3. **不要在复用的 socket 上并发/穿插多个 action** —— ack 会串台。
   实测同一连接上连续发多个动作导致解析错位;要一次一个,拿到 ack 再发下一个。
4. **远程结果不要用 `tail -N` 截取** —— 会切掉前缀(本轮把前半段结果丢了两次)。
   把结果**写文件再拉回**,并且**边跑边 append**,这样超时也有部分结果。
5. **矩阵别设计得太慢**:轮询等待设得过保守(8 s/次)× 两三百组合 = 必然超时且白跑。
   先小批量(20 个高价值组合)拿到有效动作名,再决定要不要扩大。
6. **`presence`/广播类事件不是枚举面**(见 §7)。
