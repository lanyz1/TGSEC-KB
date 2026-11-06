<!-- archived from /root/.hermes/skills/security/websocket-encrypted-protocol-reverse/SKILL.md on 2026-10-21 -->

---
name: websocket-encrypted-protocol-reverse
description: "逆向WebSocket加密通道(URL参数+消息解密+权限边界)。触发: websocket, wss://, 竞价室。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/websocket-encrypted-protocol-reverse`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/websocket-encrypted-protocol-reverse/…')`，不要相对 `references/legacy/` 解析。

# WebSocket 加密通道逆向(URL 加密参数 + 消息解密 + 权限边界)

对"HTTP 接口只做页面初始化、实时数据走 WSS + 参数/消息全加密"的 Web 应用(竞价室、实时行情、推送类),从 JS 逆向出可复现的连接协议。与 `webapp-api-crypto-reverse`(HTTP 加密 API)互补——同一个站常两者都有。

## 适用场景
- JS 里出现 `websocketAddress` / `websocketInit` / `new WebSocket(...)`
- WS URL 路径带加密参数:`/ws/<enc1>/<type>/<enc2>`(enc 是 base64 或 hex 密文)
- 目标:不依赖浏览器,Python 直连 WSS 收实时数据

## 方法论(95306 竞价室实证)

### 1. 找 WS 入口
- 搜 chunk:`websocketAddress:"wss://..."` + `websocketInit:function(){...}`(同一站多个页面 chunk 各有一个,type 数字不同 = 不同角色房间)
- 轮询触发模式:`watch:{radio:...}` → radio 变化 → `websocketInit()`(radio 常是选中项的 ID)

### 2. 拆 URL 模板
```javascript
var a = key生成(同站 HTTP 加密同款 key);
i = sm4encryptEcb(a, X).replace(/\//g, "jingjia");   // 参数1
s = sm4encryptEcb(a, this.radio).replace(/\//g, "jingjia");  // 参数2 = 选中项 ID
url = websocketAddress + "/" + s + "/" + type + "/" + i;
```
- `enc(x) = base64(SM4-ECB(key, x)).replace("/", "jingjia")` —— **只替换 `/`,`+` 和 `=` 保留**
- type 区分房间角色:如 00=竞价室(offer)/01=监视(monitorOffer)/02=监控(surveilOffer)

### 3. 消息解密
- `onmessage`: `JSON.parse(sm4decryptEcb(key, e.data))` → **消息 = 裸 base64(SM4 密文)**,key 与 URL 参数同款
- `msgType` 字段分流:heartbeat(心跳,需回 pong 或忽略)/offer(出价推送)/monitorOffer/surveilOffer

### 4. 最小 Python WS 客户端(无 websocket 库,主服无 pip 时)
- 原始 socket + `ssl.create_default_context()` → `HTTP/1.1 101` Upgrade 握手(Sec-WebSocket-Key 随机 base64)
- 帧解析:服务端帧**无 mask**;`opcode 1`=文本 / `8`=关闭(后 2 字节 = 关闭码) / `9`=ping(回 opcode 10 pong 带原 payload)
- 客户端发送帧需 mask(4 字节随机 + XOR)

## 权限边界(最容易卡死的一步)
- **握手 101 成功但立即收到关闭帧 `0x03e8`(1000)= 服务端应用层拒绝**——最常见原因:**该账号对该包件/房间无业务权限**(如未报名企业进竞价室)。此时试遍参数组合(projId/packId 互换)、Authorization 头、Cookie、URL 带 token 全部无效。
- 需要**业务账号 ST**(报过该包件/有房间权限的账号)——从审计/已拦截数据里找,或等业务账号自然操作。
- 部分站点(如 95306)竞价室操作**不写审计日志**(独立网关)→ 竞价期"审计抓 ST"链路失效,WS 也进不去 = 平台设计的数据黑盒;只能靠报名期拦截或结束后兜底接口。

## 陷阱
- base64 密文长度必须 16 倍数(SM4 块)——响应长度 %16≠0 说明格式判断错了(不是 SM4 或不是纯密文)
- enc 只替换 `/` 不替换 `+`/`=`,URL 编码别多转
- 同一站 HTTP 加密 key 与 WS key 通常同款(同拦截器),先复用再怀疑
- 服务器日期/时区决定动态 key:用业务时区(如北京 UTC+8)不是服务器时区

## 用户偏好(强制)
- **国内目标(95306 等)所有探测/连接必须走跳板机/主服 SSH 执行,严禁本机直连**(用户多次强调)
- 低频小批量,防 WAF;WS 心跳连接别挂死(超时即断)

## 支持文件
- `references/95306-bidding-room.md` — 95306 竞价室实录:WS URL 模板、SM4 key 材料、通道边界(审计不覆盖竞价室)、报名期/竞价期数据获取策略、兜底通道


---

## 外部库增量（2026-10-11 分享包）

## 心跳与密钥(自研棋牌 / AES-CBC 家族实证)

- **先找心跳**:自研游戏服常要求客户端定时发心跳(如裸字符 `@`,每 4s 一次,服务端回同字符);不发则握手 101 后**立刻被断**(表现为 `Connection to remote host was lost`),**别误判成权限不足**。
- **消息体形状**:`base64( AES-CBC + ZeroPadding( JSON ) )`,业务字段平铺(`{operation, account_id, session, data}`);ZeroPadding 要去尾 `\x00` 再 `json.loads`。
- **动作表整块抠**:客户端会定义 `wsOperation = { JoinRoom:"JoinRoom", … }`(或等价枚举),一次性抠出全部动作名再构造请求,比逐字段猜快一个量级。
- **别肉眼反串字符串猜密钥**:混淆对象(如 `ps.g()`/`ps.g(1)`)直接在 node 里求值——把 `var ps = {…};` 整段抠出,`new Function(src + '; return ps;')()` 后调 `ps.g()`;同一站 HTTP/WS 常共用一套 key。
- **session 粒度要先测**:有的站是站点常量,有的是**每账号一枚**(登录后从 `/home1/index|room` 之类接口取)。两个账号各取一次比较即知。

## 私有数据是否外泄:多账号差分法(判「透视/越权」唯一可靠手段)

1. 用**自己掌控的两个账号**各开一条 WS 连到同一房间/会话;
2. 让它们做同一动作(入座/准备/开局),逐条对比两边收包;
3. 看 A 的收包里是否出现只属于 B 的私有字段(手牌、余额、证件号…):只有 B 收到=服务端做了隔离;A 也收到=直接可得;
4. 副产物:同一事件对不同角色的字段差异表(=该协议的权限模型)。

**数据库层常比协议层更快出结果**:先查牌局/回合结果表是否存了全桌明文(如 `game_result` 这类 JSON 列里藏着所有玩家的手牌),有则是「数据层透视」——先查库再谈协议。
