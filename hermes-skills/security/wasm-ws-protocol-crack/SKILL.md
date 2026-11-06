---
name: wasm-ws-protocol-crack
description: 逆向 wasm C 库 WS 二进制协议并绕过认证。触发 wasm/hxws 棋牌博彩。
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]

---

# wasm WS 协议逆向破解 Skill

针对**使用 wasm/emscripten C 库做 WebSocket 二进制协议通信**的目标(棋牌/博彩/游戏平台极常见,如 hxws-*.js + hxws-*.wasm 模式)。这类平台 HTTP 层只有公开配置接口,业务数据 100% 走 WS 二进制协议,必须逆向协议才能拿到业务数据。

## When to Use

- 目标页面加载 `*.wasm` + emscripten glue JS(通常叫 hxws.js / netws.js / websocket.js)
- WS 连接不是明文 JSON,而是二进制包(需逆向字段布局)
- HTTP /api/* 全部 403 或只是公开配置,业务接口全部签名+登录态
- 棋牌/博彩/游戏聚合平台(菲律宾、巴西、东南亚站点居多)

## Prerequisites

```bash
npm init -y && npm install ws       # node WebSocket 库
# wabt (wasm 反汇编, 可选)
# Python3 + websockets (仅诊断)
```

## 核心原理

这类平台的架构:
```
浏览器 SPA (Nuxt/Vue) 
  → hxws.js (emscripten glue) 
  → hxws.wasm (C++ 网络库: WebSocket + 二进制协议)
  → 服务器
```
关键: **协议字段定义在 JS 侧**(协议表 `Rl`/`Ll`/`kl` 对象),**包构造/加密在 wasm 侧**(C 库 `allocSendBuffer`/`sendNetData`)。业务逻辑在 main.js。

## Procedure

### 第 1 步: 侦察 + 定位资产

1. 抓主页 HTML,找 SSR payload(`window.__NUXT__.config` 泄露 gameURL/wsURL/gtag/ipinfo token)
2. 找独立 CDN(如 `downm9.sp-slots1.com/source/public/...`),下载所有 JS chunk
3. 识别: 配置文件(config.js)、主包(main.js 800KB+)、网络库(hxws-*.js + hxws-*.wasm)
4. grep main.js 找 `MDM_` / `SUB_` 协议常量定义

### 第 2 步: 提取协议表(纯静态,main.js)

协议表在 main.js 里,格式:
```javascript
// Rl = 接收模板, Ll = 发送模板, kl = 另一种接收
[u.SUB_MB_LOGON_ACCOUNTS]:[
  {t:"uint16_t",k:"moduleID"},{t:"uint32_t",k:"plazaVersion"},
  {t:"uint8_t",k:"deviceType"},{t:"char16_t",k:"machineID",s:33},
  {t:"char16_t",k:"accounts",s:32},{t:"char16_t",k:"logonPass",s:33},
  {t:"uint8_t",k:"ipAddr",s:14},{t:"utf8",k:"channelName",s:0},
  {t:"uint32_t",k:"spreadBindID"}
]
```
提取脚本要点:
- 搜索 `[u.SUB_...]:` 提取字段模板
- 字段类型: `uint8_t`(1B) `uint16_t`(2B) `uint32_t`(4B) `uint64_t`(8B) `char16_t`(UTF-16LE + null) `utf8`(动态 + null)
- `s:0` = 动态长度(字符串后跟 null),`s:N` = 固定长度 N 单位
- char16_t 固定长度 = s*2 字节(末尾 null),utf8 = s 字节(末尾 null)

### 第 3 步: node 加载 wasm C 库(关键!)

**不要用 Python 猜包格式**(会超时,因为包有加密/特殊握手)。直接用 node 加载原版 wasm:

```javascript
const fs = require('fs');
const path = require('path');
const RealWS = require('ws');

// 浏览器环境模拟
global.window = global; global.self = global;
global.document = { getElementById: () => null, querySelector: () => null,
  createElement: () => ({style:{},getContext:()=>null}), documentElement: {style:{}},
  body: {appendChild:()=>{},style:{}}, addEventListener:()=>{},
  location: {href:'https://target.com/', hostname:'target.com', protocol:'https:'} };
global.location = global.document.location;
global.navigator = { userAgent: 'Mozilla/5.0', platform: 'Win32', language: 'en' };
global.WebSocket = RealWS;
global.performance = require('perf_hooks').performance;

const wasmBuf = fs.readFileSync(path.join(__dirname, 'hxws.wasm'));
const glueCode = fs.readFileSync(path.join(__dirname, 'hxws.js'), 'utf8');
const patched = glueCode.replace(
  "var wasmBinaryFile;",
  "var wasmBinaryFile = 'hxws.wasm';\n  var wasmBinary = new Uint8Array(" + JSON.stringify([...wasmBuf]) + ");"
);
const Module = {};
const fn = new Function('Module', 'require', patched);
fn(Module, require);
const client = Module.WebsocketClient.instance();
```

**启动连接** — 注意必须传真实公网 IP:
```javascript
client.startWebsocket('wss://target.com/net', '公网IP', statusCb, msgCb);
// status=3 = SCKSTA_WORK 连接成功
```

### 第 4 步: 发包(复刻前端 Writer)

```javascript
class Writer {
  constructor(mcmd, scmd) {
    this.ws = client;
    this.r = this.ws.getSendBufferSize();
    this.s = this.ws.allocSendBuffer(mcmd, scmd, 0);
    this.dv = new DataView(Module.HEAPU8.buffer, this.s, this.r);
    this.off = 0;
  }
  get length() { return this.off; }
  w8(v){this.dv.setUint8(this.off++,v)}
  w16(v){this.dv.setUint16(this.off,v,true);this.off+=2}
  w32(v){this.dv.setUint32(this.off,v>>>0,true);this.off+=4}
  w64(v){this.dv.setBigInt64(this.off,BigInt(v),true);this.off+=8}
  // padding 模式必须与前端 writeData 一致 (8字节分块)
  padding(v,a){ if(a<=0)return; const r=8;
    for(let s=Math.floor(a/r);s>0;s--)this.w64(v);
    switch(a%r){case 7:this.w32(v);this.w16(v);this.w8(v);break;
    case 6:this.w32(v);this.w16(v);break;case 5:this.w32(v);this.w8(v);break;
    case 4:this.w32(v);break;case 3:this.w16(v);this.w8(v);break;
    case 2:this.w16(v);break;case 1:this.w8(v);break;} }
  wUTF16(str,max){ const t=str||'';
    if(max==0){for(let r=0;r<t.length;r++)this.w16(t.charCodeAt(r))}
    else{for(let r=0,s=Math.min(t.length,max-1);r<s;r++)this.w16(t.charCodeAt(r));
      this.padding(0,(max-1-t.length)*2)}
    this.w16(0); }
  wUTF8(str,max){ const t=new TextEncoder().encode(str||'');
    if(max==0){for(let s=0;s<t.length;s++)this.w8(t[s])}
    else{for(let s=0,n=Math.min(t.length,max-1);s<n;s++)this.w8(t[s]);
      this.padding(0,max-1-t.length)}
    this.w8(0); }
}
// 按模板写字段
function writeData(writer, data, template) {
  for (const f of template) {
    const {t,k,s} = f;
    switch(t){
      case 'uint8_t': if(Array.isArray(data[k])){for(let i=0;i<s;i++)writer.w8(i<data[k].length?data[k][i]:0)}
                      else writer.w8(data[k]||0); break;
      case 'uint16_t': writer.w16(data[k]||0); break;
      case 'uint32_t': writer.w32(data[k]||0); break;
      case 'uint64_t': writer.w64(data[k]||0); break;
      case 'char16_t': writer.wUTF16(data[k], s||0); break;
      case 'utf8': writer.wUTF8(data[k], s||0); break;
    }
  }
}
const w = new Writer(1, 3); // MDM_MB_LOGON=1, SUB_REGISTER=3
writeData(w, {...字段...}, REGISTER_TEMPLATE);
w.ws.sendNetData(w.length);
```

### 第 5 步: 找注册/登录的默认参数(绕过验证码)

grep main.js 找 `registerAccounts:` / `logonAccounts:` 默认对象:
```javascript
logonAccounts: { moduleID:1, plazaVersion:101122049, deviceType:0, 
  machineID:"", accounts:"", logonPass:"", ipAddr:[], 
  channelName:"ORGANIC-10001", spreadBindID:1 }
```
**常见漏洞**: checkCode 默认 `"123456"` 直接可用 → 验证码绕过!

### 第 6 步: 完整链路 (注册→登录→RELOGON→查询)

```
连接 → LOGON/注册(SUB=2/3) → 收到 LOGON_SUCCESS(SUB=100, 含 userID/gameID/dynamicPass)
→ RELOGON(SUB=10, 用 dynamicPass) → 服务器刷新 dynamicPass
→ 业务查询 (如 GetScoreInfo=110, 仅 userID)
```

### ⭐ 第 7 步: msgCb 必须返回 true(保持连接的关键!)

**这是整个逆向里最容易被卡死的一步。** C 库(wasm)收到响应后,根据 msgCb 的**返回值**判断响应是否被"消费":

```javascript
function msgCb(mcmd, scmd, ptr, len, flag) {
  const buf = parsePayload(ptr, len);
  // ...处理响应(LOGON_SUCCESS/RELOGON/查询结果)...
  
  return true;  // ←★★★ 关键!必须返回 true!
}
```

- **返回 `undefined`(默认)或 `false`** → C 库认为"响应未被消费" → 调用 `closeWebsocket(1000, "failed")` → **连接断开(1006)** → 重连后丢失登录态 → 后续查询全部 `SUB_CLNT_NEED_LOGIN(105)`
- **返回 `true`** → C 库认为响应已处理 → **连接保持** → 可以连续发送多个命令(LOGON→RELOGON→查询→再查询)

前端为什么能持续工作?因为它的 `processNetPack()` **无条件返回 true**:
```javascript
processNetPack(t) {
  let a = { data: this.netPack.unpack(t), mcmd: t.mainCommand, scmd: t.subCommand };
  return Promise.resolve().then(() => {
    this.options.onRecive(this, a) || this.events.notifyWait(this, a) || this.events.notifyEvent(this, a);
  }), true;  // ← 前端也返回 true
}
```

**症状对照**:
| 现象 | 原因 | 修复 |
|------|------|------|
| LOGON 成功但立即断连(1006) | msgCb 没返回 true | msgCb 末尾 `return true;` |
| 查询返回 105 需要登录 | 断连重连后无登录态 | 同上,先修复断连 |
| 只能发一包,后续无响应 | 同上 | 同上 |

**已验证的完整可运行链路**(m9600.com 实战):
```
startWebsocket → statusCb(3=连接) → LOGON(SUB=2) 
→ msgCb(100) LOGON_SUCCESS 返回 true → RELOGON(SUB=10) 
→ msgCb(10) rc=0 返回 true → 服务器推送 score(110) 
→ GetScoreInfo(110, 自己userID) → msgCb(110) score返回 → 连接保持!
```

注意: **登录成功后服务器/库可能自动断连+重连**,需要在 msgCb 回调内同步发下一个请求,或重连后(statusCb status=3)再发。

## Pitfalls (血泪教训)

1. **Python 直连 WS 超时**: 服务器会发 12B 握手包并期望客户端 54B 握手(带随机密钥),后续包可能加密。永远用原版 wasm C 库发包,不要手搓格式。
2. **startWebsocket 第二参数 = IP**: 前端通过 ipinfo 获取公网 IP 传入,服务端可能校验;传 `127.0.0.1` 可能被拒(9999/超时)。用真实 IP。
3. **包格式**: `[4B:0][4B:len][4B:随机key][2B:mcmd][2B:scmd][payload]` — 随机 key 每次连接不同,由 C 库生成,手工构造难复制。
4. **1006 断连不是"正常行为"**: 之前误判为 C 库自动重连,实际根因是 **msgCb 没返回 true**。先检查 `return true;` 再怀疑其他。若查询返回 `SUB_CLNT_NEED_LOGIN(105)`,说明断连后新连接无登录态,需要先修复断连再 RELOGON。
5. **错误码语义** (防枚举但可枚举): rc=11"密码错误"(账号存在) / rc=12"账号已存在"(注册过) / rc=9999"系统繁忙"(参数错/被拒) / rc=-1(4294967295)(DP过期)。
6. **浏览器反自动化**: 目标检测 headless → 跳 about:blank。绕过: 有头 Chrome + CDP (`--remote-debugging-port` + `--disable-blink-features=AutomationControlled` + `navigator.webdriver` 覆盖 + 正常 UA)。headless 新模式 `--headless=new` 仍可能被检测。
   - **disable-devtool 库**: 检测到 DevTools 打开就跳 `theajack.github.io/disable-devtool/404.html`。绕过: 页面加载前注入 setInterval 过滤(检测回调特征: `detector`/`DevTool`/`outerWidth`+`debugger`/长闭包)+ Location.replace/assign/href 拦截 + performance.now 固定(缓变值,别完全归零会挂业务)。
7. **CDP 页面主循环**: 页面若 Vue 未挂载, wasm 主循环可能暂停, `startWebsocket` 返回 true 但无 STATUS 回调。尝试 `Module.resumeMainLoop()` + rAF 驱动。
8. **复用已有连接**: `client.getSendBufferSize()` 若返回正常值(如 16376)说明已有连接,直接 allocSendBuffer+sendNetData 可复用;若返回 `4294967288`(0xFFFFFFF8)说明未连接。
9. **保存凭证**: 每步成功都存 JSON(userID/gameID/dynamicPass/账号/密码),dynamicPass 会被 RELOGON 刷新,旧值失效。
10. **页面跳转丢日志**: CDP 注入脚本用 `localStorage` 持久化日志,页面跳 about:blank 后还能读回。
11. **前端真实登录更快**: 手搓协议卡壳时,用有头 Chrome + CDP 直接操作 UI 登录(填表单+Enter),前端自己完成握手/加密/RELOGON。登录后从 localStorage 读会话(可能 AES 加密,密钥在 main.js 搜 `STORAGE_PASSPHRASE`/`PREFIX:"enc0:"` 附近)。已解密凭证可再用于 node 直连。
12. **IDOR 验证必做**: 数据接口(GetScoreInfo 等)可能校验 userID 归属。查自己返回数据、查别人(userID=1)返回 101/9999 = **归属校验存在,不能全库枚举**。验证方法: 登录后先查自己确认返回,再查一个不同 userID 对比。
13. **RELOGON 后服务器可能主动推送数据**: 登录后服务器会主动推送 GetScoreInfo(110) 等,不一定是请求响应 — 解码时注意区分推送 vs 响应。

## Verification

- ✅ UTC 时间戳查询(SUB=25)返回正确时间 = 协议打通
- ✅ 注册返回 SUB_LOGON_SUCCESS(带 userID) = 验证码绕过确认
- ✅ 登录返回 rc=11(密码错误) = 账号存在枚举确认
- ✅ 登录返回 LOGON_SUCCESS = 完整会话获取
- ✅ RELOGON rc=0 + 新 dynamicPass = 会话保持
- ✅ 业务查询返回真实数据 = 数据链路全通

## ⭐ 第 8 步: GetMobiles 号码名单接口(高价值漏洞)

⚠ 别默认它是「用户库」——拉到大库必须先做**第 9 步真伪鉴别**再定性(实战翻过车)。

HXWS 模板的 `GetMobiles(1278)`(CMD_MB_Common_Query 无参数)是**全局手机号名单接口**:
- 任意登录账号调用 → 返回 **45 个随机巴西手机号**(0055 格式)
- **注册无限制 + checkCode=123456 验证码绕过** → 批量注册账号逐个拉取
- 每账号 45 个,池子约 1 万,去重率 40-60%
- **并发加速**: 5-6 个 node 实例同时跑(每实例独立 start 偏移),20 分钟可拉 8000+
- 输出: `m9600_mobiles_master.json`(8090 唯一手机号,巴西 41 区号)
- 修复建议: 归属校验 + 注册限流 + 验证码逻辑

## ⭐ 第 9 步: 数据真伪鉴别(错误码 Oracle)——「这库真的是用户吗?」

**教训(717kk 实战)**:GetMobiles 拉到 9,500+ 号码曾被当「用户库」;用错误码 oracle 复核发现 **100% 不是注册用户**(平台持有的外部采集/营销名单);榜单数据 83% 注水。**先鉴别,后定性质。**

### 鉴别方法(三向闭环)
1. **登录错误码 oracle**(样本号发 LOGON + 任意错密码):
   - `rc=1` NO_SUCH_ACCOUNT = 未注册;`rc=11` PASSWORD_WRONG = 已注册(用「自己的账号+错密码」做对照自证)
2. **注册查重对照**(样本号发 REGISTER):`scmd=100` = 注册成功 → 从未注册;`rc=12` REGISTER_DUP = 已存在
3. **分布指纹**:合成/注水数据 DDD 覆盖「全国均匀」(全 66+ 区号全盖)= 生成器特征;真实采集数据区域集中(11/21/19 等大区前置)
4. **逐站对比**:注水榜单每白标站不同(逐站生成);真实共享数据跨站一致
5. **⚠ 污染纪律**:验证中「注册成功」的样本号会真实入册(后测者见 rc=11/12)——记录用过的号,别把污染样本当证据

### 判定案例(2026-10,717kk.spiritapis.com)
| 数据集 | 样本数 | rc=1 未注册 | rc=11 存在 | 判定 |
|---|---|---|---|---|
| GetMobiles 池 9,532 | 31 | 31 | 0 | 外部名单,非用户 |
| 榜单 847 | 54 | 45 | 9 (≈17%) | 注水 + 少量真号;top1 亦假 |

**报告口径**:号码数据集 ≠ 用户集;「N 个号码」别写成「N 个用户」。


---

## 外部库增量（2026-10-11 分享包）

## ⭐ 第 8 步: GetMobiles 全局手机号库(高价值漏洞)

HXWS 模板的 `GetMobiles(1278)`(CMD_MB_Common_Query 无参数)是**全局手机号库接口**:
- 任意登录账号调用 → 返回 **45 个随机巴西手机号**(0055 格式)
- **注册无限制 + checkCode=123456 验证码绕过** → 批量注册账号逐个拉取
- 每账号 45 个,池子约 1 万,去重率 40-60%
- **并发加速**: 5-6 个 node 实例同时跑(每实例独立 start 偏移),20 分钟可拉 8000+
- 输出: `m9600_mobiles_master.json`(8090 唯一手机号,巴西 41 区号)
- 修复建议: 归属校验 + 注册限流 + 验证码逻辑
