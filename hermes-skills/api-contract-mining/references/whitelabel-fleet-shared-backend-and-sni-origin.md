# 白标站群：共用中央后端 + SNI 源站可达性（nezawin / GAMBLER PANEL 案，2026-09-25）

## 0. 场景形状

一个加密赌场白标 SaaS 族：N 个品牌站（`bastwin.com` / `kazewin.com` / `nezawin.com` / `noawin.com` …），
每个站的**玩家 API 全部指向同一个中央域**（`gambler-partners.is`），中央域同时又托管
worker 联盟后台，另有一个全公开的官方文档站（`wiki.<central>`，含 API/WS 文档）。

## 1. ★ SNI 白名单：`Host:` 头单独用打不通源站

源站 IP 已定位（反查/历史解析），但直连失败：

```bash
# ✗ SNI=IP，只有 Host 头
curl -sk -H "Host: nezawin.com" https://66.198.225.39/
#   → code=000  size=0  ssl_verify_result=1
#   → openssl: "TLSv1.3 (IN), TLS alert, internal error"
#             "error:0A000438:SSL routines::tlsv1 alert internal error"

# ✓ SNI=域名
curl -sk --resolve nezawin.com:443:66.198.225.39 https://nezawin.com/
#   → 200  250,922 bytes
```

**误判纠正**：上一步的 `000` 曾被读成「源站不可达 / 只放行 Tor 出口 / IP 层白名单」。
真相是**按 SNI 过滤**，IP 和出口都不是关键。

走 Tor 时的正确形状（每请求随机 `--proxy-user` 获得独立出口）：

```bash
curl -sk -g -m 14 --socks5-hostname 127.0.0.1:9050 --proxy-user U:U \
     --resolve <host>:443:<origin> -o /tmp/b.bin -w '%{http_code} %{size_download}' \
     https://<host>/
```

## 2. ★ 251 个 host 的 SNI 分桶（挑没套反爬的门）

反爬组件（本例 `server: cast-sec`，非标状态码 **666** + RC4 混淆 `/verifyjs` 挑战，判据是**纯出口 IP 信誉**）
**逐域名配置**，所以同族里分布不均：

| 状态码 | 数量 | 含义 |
|---|---|---|
| `403` | 170 | 有反爬保护 |
| `000` | 38 | 域名已死/未解析 |
| `666` | 28 | 反爬挑战页本体 |
| **`200`** | **15** | **无保护 / 特殊响应 ⇒ 优先从这些门进** |

实测从这批 200 的门（`bastwin.com` 等）直接读完前端、拿到中央后端配置，全程无挑战。

⚠ **陷阱**：状态码是 200 但 body 是 `403 Forbidden` HTML（反爬变体）—— **必须读 body**，
只按状态码分桶会把「保护中」的站算进「无保护」。

## 3. ★ 克隆前端硬编码中央后端

任一无保护站的前端 bundle 里（7.5MB，27 chunk）直接抠出配置对象：

```javascript
DEV:  { wsLink:"wss://gambler-partners.is/api/ws",
        api:"https://gambler-partners.is/api",
        localApi:"https://gambler-partners.is/api",
        paymentsApi:"https://gambler-partners.is/payser",
        slotsApi:"https://gambler-partners.is/api/slots" }
PROD: { wsLink:"/api/ws", api:"/api",
        localApi: NEXT_PUBLIC_IS_DOCKER ? "http://host.docker.internal:80/api" : "http://localhost:3001",
        paymentsApi:"/payser", slotsApi:"/api/slots" }
name:"bastwin.com", color:"greenColorDSGN",
```

**推理链**（可复用）：
1. 站点自己域下 `/api/*` 全 404 → **不是「没有后端」，是「后端在中央域」**；
2. 抠 `api+` / `cfg.api+` 拼接点比猜路径快一个量级（正则 `(?:api|localApi|paymentsApi|slotsApi)\+\s*"([^"]{1,80})"`）；
3. `localApi` 的 dev 值（`localhost:3001` / `host.docker.internal`）暴露**内网主机命名规律**，可用于后续 vhost 探测；
4. `picturesApi: e=>"https://pictures-cdn.is/"+e.replace(/^\//,"")` 一次性给出 CDN 主机与路径拼接规则。

端点族（从 `api+"…"` 抽取，13 条，全部实测存在）：

```
/mammoth/auth/register     /mammoth/auth/check
/mammoth/chat  /mammoth/chat/read  /mammoth/chat/img
/mammoth/files  /mammoth/me  /mammoth/promo/<code>/valid
/mammoth/deposits/postback  /mammoth/postback/info
/extra/holiday  /extra/pixel  /extra/promoIp
```

## 4. ★ 错误驱动字段枚举：`Invalid <名词>` vs `500 ERR_INVALID_ARG_TYPE`

上传端点 `POST https://pictures-cdn.is/file`（前端 fetch 封装已确认 `body` 走 `JSON.stringify`、
content-type 固定 JSON、authorization 自动带）：

| body 形状 | 响应 | 读法 |
|---|---|---|
| `{token, file, name}` | `200 {"success":false,"error":"Invalid file name"}` | 猜的名字段名不对 |
| `{token, file, fileName}` | **`500 {"code":"ERR_INVALID_ARG_TYPE","message":"The first argument must be of type string or an instance of Buffer… Received undefined"}`** | **名字段名对了**（已过校验），是内容字段为空 → 去枚举内容字段名 |
| `{token, fileName, body}` | `200 {"success":true,"data":{"token":"<JWT>"}}` | 打通 |

- 内容字段名扫了 23 个（`file/data/content/buffer/base64/image/media/blob/bytes/...`）里只有 **`body`** 命中；
  其余返回 `Invalid token`（服务端**错误码不精**，会把「内容字段缺失」报成 token 问题 —— 别被误导回去改 token）。
- 打通后响应 `data.token` 的 payload 才是最终落盘名：
  `{"type":"fileSuccess","fileName":"<雪花ID>.png","iat":...}`。
- **扩展名白名单**（与前端 `accept` 一致）：`.png/.jpg/.jpeg/.gif/.webp`；`.php/.html/.svg/.txt/.js/.json/.exe/.zip` 全拒。

## 5. ★ `OPTIONS` 的 `Allow:` 头定死「纯写端点」

```
OPTIONS /api/user/wallet-connect  →  200  allow: POST,OPTIONS
GET|PUT|PATCH|DELETE 同路径       →  500 {"code":"INTERNAL_ERROR"}
```

读法：**`allow: POST,OPTIONS` ⇒ 纯写端点、不存在读取面** —— 「提交的助记词能不能读回来」整条线一句话判死。
500 是「路由在、方法未实现」，**不是服务端崩了**。

同一个端点的参数校验器也是判据：`invalid_wallet_seed_phrase`（BIP39 词表校验）**前置**在写库之前，
所以 `' OR 1=1--` 之类载荷根本进不了库 —— **注入面被格式校验天然切断，别硬打**。

## 6. 雪花 ID：枚举可行性判据（本例 → 不可枚举）

```
id  = (unix_ms << 22) | (seq & 0xFFF)      worker=0, process=0（单进程）
ts  = id >> 22                             # 直接落在当前年月 ⇒ epoch=0（Unix 毫秒），无自定义 epoch
seq = id & 0xFFF                           # 0..4095
```

实测样本：

| 对象 | id | ts | seq |
|---|---|---|---|
| 文件 1 | 7509171343233911536 | 2026-09-25T08:46:01.884 | 2800 |
| 文件 2 | 7509171251978438401 | 2026-09-25T08:45:40.127 | 1793 |
| 文件 3 | 7509169962179628817 | 2026-09-25T08:40:32.615 | 3857 |
| 消息 id | 7509169550009568175 | 2026-09-25T08:38:54.346 | 2991 |
| **文档示例 mammoth** | 7225647165131980801 | **2024-08-03T23:42:10.200** | 1 |

- **`seq` 随机（非递增计数器）** ⇒ 每毫秒 4096 种可能 + 不知哪些毫秒有文件 ⇒ **枚举不可行**。
- 实测两轮验证：顺序枚举 `±1..±300` 全 404；时间邻域 `±k*2^22` 全 404。
- 副产品：文档里的示例 ID 解码出 **2024-08-03** ⇒ 那是**真实受害者**，不是占位符，可用来量运营时长与规模。
- 上传限流 ~15s/次，使「靠上传采样反推 seq 规律」也不可行。

## 7. 文件面结论分档写（可读性 vs 可枚举性）

```
GET https://pictures-cdn.is/<雪花ID>.png   →  200 image/png   ← 零认证、无 cookie/header
```

- **可读性缺陷成立**（任何知道文件名的人都能读）；
- **可枚举性不成立**（见 §6）；
- 唯一的文件名来源是**另一个面**：chat 消息对象里的 `picture` 字段
  （`{"picture":"7509171343233911536.png","side":"mammoth"}`）
  ⇒ **必须先打破 chat 面才有文件面** —— 这才是真实的攻击路径顺序，报告要按这个顺序写。
  （反过来写成「可任意读取他人文件」是错的。）

## 8. JWT 全矩阵（一次性跑完再判死）

目标：冒充 `{"type":"login","userId":"<他人ID>"}`。全部 **401**：

| 类别 | 变体 |
|---|---|
| `alg:none` | none / None / NONE / nOnE × 空签名 / `.` / `x` |
| 签名 | 空、单字符、全 0、截断、去尾、大写 |
| payload 替换 | 换 `userId` / 提权 `role` / 换 `type`（**保留原签名**） |
| header 注入 | `kid`（`../../../../dev/null`、`1`、`' OR 1=1--`）、`jku`、`x5u`、`jwk`、`crit` |
| 算法混淆 | `-----BEGIN PUBLIC KEY-----` / `public` / `rsa` / 空串 作 HS256 密钥 |
| 字典 | 56 组定向词 + **全量 rockyou 1400 万（8 进程，~10s）** |

结论写法：**「HS256 密钥为强随机，伪造路径判死」**，收工不回炉。

**认证传输面**（同一次跑清）：`authorization: <jwt>` ✓、`Cookie: token=<jwt>` ✓、
`Authorization: Bearer <jwt>` ✗、`X-Auth-Token` ✗ —— 后续所有探针带哪个头由这里决定，不靠猜。

## 9. 越权尝试：参数全被服务端忽略（形状对照表）

| 尝试 | 结果 |
|---|---|
| `GET /api/mammoth/chat?userId=<他人>` / `?mammothId=` / `?id=` | 200，**参数被忽略，只回自己的** |
| `GET /api/mammoth/chat/<他人ID>`（路径式） | 404 |
| `POST /api/mammoth/chat` body 注入 `userId`/`mammothId`/`id`/`side`/`isDefault`/`support`/`workerId`/`createdAt` | 全部丢弃，**只取 `text`** |
| mammoth 角色 token 打 worker 面 `/api/me*` | 401 |
| 另一系统（站点侧）玩家 JWT / cookie 打中央域 | 401（不共享签名体系） |

⇒ 写「服务端以 **token 内的 userId 为权威**，所有 ID 类参数均不参与身份判定」，一次判死，别逐个回炉。

## 10. 免凭据可读的敏感数据（本例）

- `GET /api/mammoth/me` → **明文 `password`**、`useDrainer`、`drainerMin`、`connectedWallets`、
  `checkInfo:{erc20,prc20,bep20,base}`、`regIp`/`lastIp`/`ipCountry`、`minDeposit`/`minWithdraw`、
  `banned`/`blacklisted`/`promoAbuse`/`fakeWithdraw` —— **逐受害者的 drainer 运行时配置**，直接印证平台级盗币能力。
- `GET /api/files` **未授权**返回 `{"success":true,"data":{"token":"<HS256 JWT>"}}`。
- `GET /api/mammoth/promo/<code>/valid` **未授权 oracle**：`{"success":true,"data":true|false}`
  （大小写不敏感；实测命中的通用码 `BONUS/FREE/BET/WIN/START/NEW`）。
- **CORS 反射**：任意同族站点 Origin 均回 `access-control-allow-origin: <你的 Origin>` +
  `access-control-allow-credentials: true` ⇒ **任何白标站被 XSS 即可驱动中央 API**。

## 11. i18n 文案表作阴性证据（本例二手确认）

登录 chunk 里的全局文案表抽取（69 条）→ 全是 drainer/域名管理/AI 客服/提现审核等功能名，
**整表不含 private key / mnemonic / seed 任一条目** ⇒ 把「找不到私钥」升级成
报告级结论：**该密钥不在本角色可见面内流转**。与「worker 侧 API 文档只返回
`{network, address}`」互相印证 ⇒ 私钥明文只在平台后端 / drainer 引擎。

## 12. 限流表（决定可行性，早测早省时间）

| 操作 | 限流 |
|---|---|
| 上传文件 | **15 秒 / 次** |
| 注册账号 | **10 分钟 / IP** |
| 地址检查（文档所述） | 5 分钟 / 次 |

## 13. 已判死面（防下一轮回炉）

- JWT 伪造（§8）、IDOR / mass-assignment（§9）、文件 ID 枚举（§6）
- 中央后台登录：**统一错误 `Invalid login or password`，无用户枚举 oracle**；内部路由全 `307 → /auth/login`
- AI 客服：有 scope guardrail，索取私钥/他人余额的提问被 generic 拒答（值得注意：它只否认「范围外讨论」，**未否认「平台收集了私钥」**）
- 前端 chunk：未认证只能拿到登录页 + 落地页 chunk（后台页面 chunk 需登录后才加载），全量下载 4.6MB 仅得 `/api/ws` 与 `/auth/login` 两个路径

---

# 补充（2026-09-25 后续轮次）

## 14. ★★ 重大纠正：mammoth 面认证走 **Cookie**，不是请求头

前几轮对 `/api/mammoth/*` 的所有测试（注入 / IDOR / 参数枚举）**全部回 401**，当时被读成
「鉴权严格 / 端点不存在」。**真相是认证方式错了**：

```
-H "token: <JWT>"                → 401（本会话一直这么发）
-H "Authorization: Bearer <JWT>" → 401
-H "X-Token: <JWT>"              → 401
-H "Cookie: token=<JWT>"         → 200  {"success":true,"data":{…完整档案…}}
```

换对之后**整面打开**：`/me`、`/files`、`/chat`(GET/POST)、`/promo/<code>/valid`、`/postback/info` 全 200。

⇒ 铁律：**整族端点一律 401 时，先穷举「令牌在哪个位置」再谈鉴权强度** ——
`header(裸名 / Authorization / Bearer / X-Token / X-API-Key)` × `Cookie(各同名)` × `query` × body。
**把所有 401 当成「不存在」会直接丢掉整面攻击面，并且这些假结论会被写进报告误导后续轮次。**

## 15. 新发现的端点族（同一中央域 / 玩家站）

### 玩家站（`nezawin.com`，需 session cookie）
```
GET  /api/user/balance            200  {"balance":"2700.00"}          ← 只回余额，最小依赖
GET  /api/user/profile            200  全字段（含明文 twoFactorCode / 明文头像等）
GET  /api/user/privacy            200  9KB 隐私政策
GET  /api/user/deposit/settings   200  ★ 支付配置（见 §17）
POST /api/user/deposit/address    ★ 收款地址枚举器（见 deposit-address-to-onchain-forensics.md）
POST /api/user/payment/create     ★ 创建支付（见 §17）
POST /api/user/2fa/disable        {"error":"invalid_code"}   ← 存在，需 TOTP
POST /api/user/password           {"error":"invalid_password"}
GET  /api/extra/currency-rates    200  实时币价；GET /api/extra/postback 200 回传配置
```

`/api/user/profile` 的 `twoFactorCode` 是 **TOTP secret 明文**；提现记录带 `workerId`
（⇒ 每个玩家挂在具体运营名下）。**重新登录用 `password + TOTP`（本地 RFC6238 算即可）。**

### ★ `/api/bot`
```
GET /api/bot | /api/bot/health | /api/bot/status  → 401 {"status":"error","message":"wrong_api_key"}
```
**JSON 信封与主 API 完全不同**（`{status,message}` vs `{success,error}`）⇒ 是**独立服务**。
key 校验在路由**之前**（catch-all，任意子路径都回同一句），query/header/cookie/body 十几种传法
（含 `Authorization`、`X-Bot-Key`、`Api-Key`、`API_KEY`、`Key`、`Secret`）**全部同一句** ⇒
**拿不到 key 就无法区分「路由不存在」与「key 错」，别再逐个试位置**。弱 key 喷洒（遵循用户规矩）全灭。

### Tomcat 兜底（不是漏洞，别误报）
```
/api/foo[] /api/user[] /api/mammoth[] /api/user/pixels[]  → 400 Apache Tomcat 错误页
/xd[] /anything[] /[]                                       → 404 Next.js
```
⇒ **任何 `/api/*` + `[` 都触发**，只是 Java 侧 catch-all 错误页，**无版本号、无管理面**
（`/manager/html`、`/host-manager`、`/api/actuator/*`、`/api/druid` 全 404）。
`.well-known/*`、`ads.txt`、`feed/` 均无可利用内容。

## 16. XSS 两端都封死（存储型也不成立）

| 环节 | 实测 |
|---|---|
| 存储 | ★ **服务端已转义**：发 `<b>x</b>` 读回 `"text":"\u003cb\u003ex\u003c/b\u003e"` |
| 玩家端渲染 | linkify 有 scheme 白名单 `/(?:https?:\/\/|www\.)/gi`；未匹配部分走 React `children`（自动转义） |
| 管理端渲染 | `react-markdown` + `urlTransform`，**无 `rehypeRaw`、无 `dangerouslySetInnerHTML` 包裹消息正文** |

注：`insertAdjacentHTML`/`innerHTML` 计数全落在框架运行时代码里，与应用无关（同 SKILL.md §4）。
⇒ 写「存储型 XSS 不成立」并附三处判据，别写成「可能主在管理端未转义」。

## 17. 支付面：白名单、oracle 与「假订单」

`GET /api/user/deposit/settings` 直接吐出两份白名单与自动充值阈值：
```json
{"paymentMode":"FIXED_PROVIDER_API","useDepositAutosum":true,"depositAutosum":"200",
 "payments":["coinbase","robinhood","onramper","meld","stripe","simplex","banxa","moonpay",
              "transak","mercuryo","ramp","kraken","bitpay","topper","paybis",…],
 "disabledProviders":["unlimit","guardarian","utorg","onrampmoney","coinify","skrill","btcdirect",
                        "koywe","onmeta","fonbnk","gateconnect","onramper","instantpay","binance",
                        "blockchain","cashapp","paypal"]}
```
**有效面 = `payments` − `disabledProviders`。** 本会话一开始只试了 `simplex/coinify/btcdirect`，
而 `coinify`/`btcdirect` **恰好在禁用列表里** ⇒ 白跑好几轮。**先读白名单再枚举，别猜。**

`payment/create` 双 oracle（错误文案直接给枚举值与业务规则）：
```
checkoutMode 合法："" | "direct" | "onramper"        其余 → "Unsupported checkout mode: <值>"
paymentSystem 合法：见上面有效面                        其余 → "Unsupported payment system"

per-provider 硬规则（错误文案原文）：
  Simplex   → "supports only native Ethereum funded in USD"
  Coinbase  → "checkout supports only USDC on Ethereum (ERC20)"
  Robinhood → "supports only USDC on Polygon funded in USD"
  Banxa/Moonpay/Mercuryo → "Only BTC, ETH (ERC20), USDC (ERC20), and SOL (Solana)"
  onramper 模式 → "requires direct checkout without an Onramper quote"
  ★ transak + direct → 200
```

**但 200 是空壳**：`{"message":null,"redirectUrl":"https://global.transak.com/","success":true}`
—— `redirectUrl` **不带任何订单参数**，且换 `uuid`/`cryptoAddress`/`partnerCustomerId` **恒为裸首页**。
⇒ 写「支付创建接口可达，但平台未生成可关联订单（重定向到第三方首页且不带身份）」；
**不要写成「已能充值/已绕过提现门槛」**。且实测余额与 deposits 全程未变。

### ★★ `xverse` 三端点：平台自己有「签名能力」
```
POST /api/user/payment/xverse/auth-reply   {"challenge":"x"}   → 200
  {"challengeReply":{"signature":"<base64 DER>","xPubKey":"xpub6…","challenge":"x"},"success":true}
POST /api/user/payment/xverse/scope-proof      → "BTC scope address does not match the authenticated user"
POST /api/user/payment/xverse/fallback-opened  → "Invalid fallback receipt"
```
- `scope-proof` **不取请求里的 `walletAddress`**（传什么都没变化，恒报不匹配）⇒ 它读**服务端绑定的地址**；
  `create` 受 worker 侧支付配置限制 ⇒ **本账号走不到「绑定」那一步**。
- `auth-reply` **对 challenge 零校验**（`"x"` / `""` / 200 字 / 中文全部接受），**每次返回不同的 `xPubKey`**
  （实时生成密钥对），输出形状恰好是 `scope-proof` 要的 `{signature, xPubKey}`。
  ⇒ 证据级结论：**平台「证明你拥有这个钱包」的那一环，由它自己的接口代签。**
  注：仍需有效 session（无 cookie → 401），不是无鉴权；也**不要**据此写「可冒充任意钱包」。
- 签名结构：base64 解出**不以 `0x30` 开头**（实测首字节 `02 47 30 44 02 20…`），不是标准裸 DER。
- 第三方侧：`xverseRequest` 的 baseURL 是 **`https://api-3.xverse.app`**（客户端带 `x-client-version: 2.7.3`）；
  `GET /v1/auth/challenge` 可**匿名**取回 JWT 形式 challenge，`hasScope`/`extendScope` 需 accessToken（401）。

## 18. 业务逻辑与风控（都封死，但形状要记）

| 动作 | 结果 |
|---|---|
| `POST /api/user/rakeback/claim` | `rakeback_not_ready` + `remainingMs`/`nextAvailableAt`（冷却约 18.9 小时） |
| `POST /api/user/promo/activate` | `invalid_promo` |
| `POST /api/user/withdrawal` `amount:-100/0` | `invalid_amount` |
| 同上 `amount:1e15` | `no_balance` |
| 同上 `amount:2700`（trc20/erc20） | `before_verification`（不变） |
| 同上 **10 并发** | **10/10 全 `before_verification`，无竞态、余额未变** |
| `/api/slots*` | 404（不在玩家域） |

★ **风控是真实存在的，且会被自己的探测触发**（实测）：
```
POST /api/auth/login {email,password}  → {"status":"error","error":"banned"}    ← 测试号被封
POST /api/auth/register {…}            → {"error":"multi_account_detected"}      ← 出口 IP 被标记
```
被封后**部分端点仍读**（`balance` 200 / `profile` 401）⇒ **别当成路由差异，先怀疑账号状态**。
换出口（Tor 每请求随机 `--proxy-user`）重新注册即可继续 —— 但意味着**对资金类账号的大批量探测会烧掉账号**，
要在战役计划里预留换号成本。

## 19. 归档侧（Wayback/sitemap）—— 本例零收获，但方法可复用

- 旧 panel 域（`gambler-panel.com`）在 Wayback 存了 24 条，**JS chunk 仅框架代码**（polyfill/webpack/
  登录页组件），`/api/` 端点提取 **0 个** ⇒ 别指望归档旧包能拿到已删端点（业务 chunk 未入档）。
- `wiki.<域>/sitemap-pages.xml` 与 `llms.txt` 索引**完全一致（52 页）**；存档版 sitemap 同一批页面
  ⇒ 无「未索引页面」。
- `/navigaciya/*`、`/.well-known/*`、`ads.txt`、`feed/`、`rss.xml` 全为托管商的统一 404。
- 旧域（`gambler-panel.com/.is/.io/.net`、`wiki.gambler-panel.*`、`gambler-work.com`）**DNS 全空**：
  **下线域先 `dig`，再决定是否值得花时间**。
