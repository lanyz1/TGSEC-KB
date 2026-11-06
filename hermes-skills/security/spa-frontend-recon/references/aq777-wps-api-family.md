# AQ777 菲律宾博彩白标平台逆向实战(gz778.aq777c1.vip, 2026-08)

## 平台指纹

- 品牌 AQ777,菲律宾在线赌场(Slots/Sabong/Baccarat,Jili/PG/FC 提供商),Vue SPA + webpack
- CDN:腾讯 EdgeOne(`Server: TencentEdgeOne`),JS 挑战反自动化
- 真实 IP:43.174.196.140(CNAME 到 `*.eo.dnse5.com`,EdgeOne 节点)
- 前端产物:`/res/js/app.XXXX.js`(入口)、`/res/js/vendor.XXXX.js`(1.8MB 全部业务库)、`/res/encrypt.js`(混淆加密库)、路由 chunk `/res/js/<Name>.<id>.<hash>.js`
- 源站域名(前端 JS 明文泄露,CDN 绕过候选):`images.b298100.com:42666`(图片)、`www2.854819.com:42666`(游戏启动)

## API 体系:`/wps/*` + modID 模块化

所有接口以 `modID` 字段关联功能模块(278 个模块,whitelabel 可读)。核心端点:

```
POST /wps/session/login               # 登录(encrypt:true)
PUT  /wps/member/register             # 注册(encrypt:true, token:false)
POST /wps/member/register/mobile      # 手机注册
POST /wps/member/register/autoUsername # 自动用户名注册
GET  /wps/member/info                 # 会员信息(token:true)
GET  /wps/v2/wallets/balance          # 钱包余额(token:true)
POST /wps/relay/GCS_walletTransfer    # 钱包转账(token:true)
GET  /wps/system/whitelabel           # 白标配置 [公开,金矿]
GET  /wps/session/key/rsa?t=<ts>      # RSA 公钥 [公开]
GET  /wps/system/status               # 功能状态(带 url 参数)
GET  /wps/agent/affiliate             # 代理系统
GET  /wps/system/test/ping?speed=<ts> # 连通性测试(源站探测用)
POST /wps/verification/sms/noLogin    # 短信验证码(无token)
```

更多端点直接在 vendor.js 的 `PKPb` 模块(`t.a={login:{...}}`)和 `2xaC` 模块里枚举 `link:` 字段。

## 请求封装(vendor.js X0rp → sc 类,4gpj = new sc())

- **必带 headers**:`Merchant`(merchantCode,来自 `Object(A.a)()`)、`Device: web`、`Language`(hisLang)、登录后 `Authorization`(token)。**裸调 400 "http_method_not_support"/"function.not.available" 通常是缺 Merchant header**,不是方法错。
- GET 用 query string 传参(`<link>?<urlencode(json)>`),POST/PUT 用 JSON body。
- URL 中的 token/authorization query 会被 `z()` 函数剥离。
- 注册会自动注入:`registerMethod=WEB`、`domain`、`registerUrl`、`referralCode`、`affiliateCode`、`linkId`(来自 localStorage tid)、utm 参数、`loginDeviceId`(登录/注册接口额外)。
- 登录/注册返回后 token 存 sessionStorage `token`,`account`、`merchant` 也存 sessionStorage。

## 加密协议(encrypt.js,混淆但可复刻)

- RSA 公钥:`GET /wps/session/key/rsa?t=<ts>` → 返回纯 hex modulus(256 hex 字符 = **1024-bit**;Python 复刻 `chunkSize=2*biHighIndex=126`,exponent 0x10001,little-endian Tom Wu 变体,逐字节匹配 Node `rsaEncryptV2` 基准 — 完整代码见 `white-label-casino-pentest/references/aq777-wps-rsa-des-case.md`)
- 加密链:`window.reRsaV2(data)`:
  1. 随机 DES 密钥 → 用 RSA 公钥加密 → `t.RSA`
  2. 业务数据 JSON → `CryptoJS.DES.encrypt(data, key, {mode: ECB, padding: Pkcs7})` → `t.DES`
- 请求:`headers.Encryption = t.RSA`,`body = {"value": t.DES}`
- **模式是 ECB 不是 CBC**(本会话动态解码字符串表证实 `0x198="ECB"`;旧版本误判 CBC 导致一直 `decryption.err`)。RSA 加密用**反转后** rand,`json.dumps` 必须 `separators=(',',':')` 紧凑对齐 JS `JSON.stringify`。精确复刻 + 利用链见 `aq777-wps-rsa-des-api.md`。
- 字符串表(a0_0x2207 数组,188 项)含全部明文常量:端点路径、算法名、报错文案、`63CceVnV` 等密钥候选、RSA exponent 字符串
- 注意 exponent 也走混淆表(`_0x253469(0x175)`),需从字符串表解析

## 白标配置 = 攻击面情报源(公开接口)

`GET /wps/system/whitelabel` 返回完整功能树(278 modId),直接判断:
- 登录/注册验证码开关:`LOGINCAPTCHA3` / `LOGINREQCAPTCHA3` / `CAPTCHA3` / `GEETEST3` / `GEETESTRISK3` 的 enabled
- 登录方式:手机验证码 `MOBILEVERCODELOGIN3`、Google/Facebook/Telegram/Apple `*LOGIN3`、OSS `OSSLOGIN`
- 注册方式:`DIRECTREG3`(直接注册)、`MOBILENUMREG3`(手机注册)、`USERNAMEREG3`、`REGMOBVERF3`
- 提现/支付:`WITHDRAW`/`WTHDRW3`、`DEPOSIT`/`DEPFUNC` 家族、`PAYMENTPASS3`、`BINDCARD3`
- 代理/资金:`AGECEN`/`AGENTPROMOTE3`、`PROFITSHARE`/`DIVIDEND`/`DAILYSAL3`
- 枚举值:`"enabled":"1"` = 开,`"0"` = 关 → 直接判断撞库/注册爆破可行性

## 会话经验

- EdgeOne 挑战绕过:urllib + CookieJar,先 GET 首页再同会话 GET JS(见 SKILL.md Pitfalls)
- curl 对 JS 路径全返回验证页时,先用 `file` 确认;真实 JS 拿到后 `--compressed` 或 urllib 自动处理 gzip
- webpack chunk 映射在 app.js 的 `s.e` 函数里:`res/js/<Name>.<id>.<hash>.js` 映射表(路由名:1=Agent, 2=AgentAc, 3=Member, 11=index...),按映射批量下载
- HTTP 封装 X0rp 模块在 vendor.js(不是 app.js),app.js 里只有 `4gpj:new X0rp.l()` 引用;找请求封装先 grep `interceptors.request.use` 定位 axios 实例
- 客服 URL 用 `window.desDecrypt(加密路径, 8位key)` 解密 → 客服子系统是独立攻击面

## 移动端/代理后台独立 bundle(后半段关键发现)

同一域名 `/m/agent`(代理后台)、`/m/index.html` 等路径加载**独立 React bundle**,与网页版接口字典完全不同且更全:

```
/m/vendor.encrypt.v2.dll.js (882KB)
/m/chunk-common.820e0c70.js (622KB)
/m/app.3d46cd5f.js          (950KB)
```

从这些 bundle 提取的完整接口面(网页版没有的):

**代理**:`/wps/agent/downline`(下线,需加密POST)、`/wps/agent/downlines`、`/wps/agent/transferDownline`、`/wps/agent/transferMultipleDownline`、`/wps/agent/updateDownlineRebates`、`ODSFE2_Subordinate`、`ODSFE2_TeamKPIA/B/C`、`ODSFE2_MemPNL`、`ODSFE2_CurrentDailySalary`、`MCS2_getAgentQuotaGroupByProduct`

**资金**:`/wps/member/bankCard`(绑卡)、`MCS2_bankCards`、`MCS2_withdrawBanks`、`/wps/transaction/withdraw`(提现)、`MCS2_depositManualTransfer/DepositAlipay/DepositQQ/DepositWeChat/depositPaymentGateway`、`MCS2_depositTransactioNReport`、`MCS2_WithdrawTransactionReport`、`ODS2_MemberTransaction`

**安全/资料**:`/wps/member/securityConfig`、`hasWithdrawalPassword`、`/wps/member/paymentPassword`、`/wps/member/bankCard`、`/wps/member/info`(POST 可改资料)、`/wps/member/info/email`(改绑定邮箱)、`/wps/member/info/payeename`、`/wps/member/info/nickname`、`/wps/member/customerSecurityQuestions`、`/wps/check/username`(轻量用户枚举)

**其他**:`/wps/system/country`、`/wps/member/trialuser`、`/wps/session/login/3rd|line|maya|telegram`、`WPS3RD_verifyLineCode`、`WPS3RD_refreshMayaTokens`、`CSP_fcmBind/fcmSubscribe/fcmUnsubscribe`

## 代理身份与提权尝试(实测结论)

- 身份判定:`MC_SESSION_INFO.type = customerType`;type ∈ [1,2,41,42] = 代理,type ∈ [0,4,40] = 普通。代理功能(下线/团队/转账)需要代理身份。
- 提权尝试:`POST /wps/member/info {"type":1}` 返回 `success:true` 但 **type 不变**(服务端忽略该字段);注册传 `type/customerType` 参数同样无效。客户端无法自提权。
- 代理接口活跃性:明文 GET/POST → `function.not.available`;**加密 POST** `/wps/agent/downline` → `request_param_err`(通道活跃,缺参数);`/wps/agent/downlines` → `rest_not_found`。错误码变化 = 通道死活指示器。
- whitelabel 陷阱:用错误 merchant('AQ777')拉的 whitelabel 显示 278 模块(代理全关);用正确 merchant(`as888tlbf7`)是 145 模块,**代理模块(AGECEN/DOWNMAN/AFFMAN3/REGCEN)实际启用**。必须确认 merchant 再下结论。

## 风控阈值(实测)

- 注册:连续 ~9 个成功 → `register_ip_restricted`(IP 限频,`autoUsername` 也拦);冷却数分钟~1小时
- 登录失败:5 次 → `us_forbidden_login_error`(账号锁定)
- 连续登录测试后:IP 整体 `login.ip.restricted`(地区级错误文案)
- 第三方登录:Telegram hash 真校验(`telegram_validate_failed`),伪造无效;错误泄露内部类 `com.tcg.gateway.to.telegram.TelegramTcgLoginRequest`

## 多商户

同一网关换 merchantCode 可探测其他白标实例:`dingtsaiyl`(25 模块)、`default`(25 模块)vs `as888tlbf7`(145 模块)。功能少的实例防护可能更弱,值得横向。

## 产物位置

`C:\Users\Administrator\Desktop\gz778_recon\`:app.js / vendor.js / encrypt.js / whitelabel.json / chunks\
