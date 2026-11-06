# gambling-family-router 全文 第 3/4 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## Pitfalls

- **用户给了具体 bot/目标时只做针对性扫描, 禁止全网泛扫(用户铁律, 2026-08 明确纠正)**:用户给 @某bot 或具体品牌后, 不要拿通用语法(bot/panel/telegram)在空间测绘引擎全网扫——用户明确否决("我不需要你去全网扫杂乱的面板, 只要针对性的扫专属 bot 面板")。先提取目标专属指纹(bot 用户名/品牌中英文/客服号/已知域名)再搜。**Censys 搜中文/拼音关键词误命中极高**(搜 "zhoushi" 返回 7 个全是公司名/路名/工厂官网), 中文特征优先 Fofa(`title="Bot" && body="telegram"`), 其次 Shodan(`http.title:"bot" http.html:"telegram"`)。用户没引擎 key 时**教注册**(Fofa: fofa.info→免费注册→个人中心→API 信息→email+key;Shodan: account.shodan.io/register→Account→API Key), 不要只问"你有没有 key"——用户明确纠正过("你教我怎么注册不就可以了吗")。
- **Censys 新平台语法已迁移(legacy 全失效, 2026-08 实测)**:`services.http.response.body:"..."` / `services.http.response.html_title:"..."` 在新平台返回 Invalid Query。新语法:
  ```
  host.services.endpoints.http.body:"bot_token"
  host.services.endpoints.http.html_title:"bot" and host.services.endpoints.http.html_title:"panel"
  web.endpoints.http.body:"..."   # Web Properties 资产
  ```
  免费版未登录 5 次搜索/天;已登录 Chrome profile(chrome_censys)的 cookies(auth_v1/session.id/cf_clearance)长期有效, CDP `--remote-debugging-port` + `--user-data-dir` 复用登录态;浏览器锁 DB 时别 sqlite 直读(WinError 32), 走 CDP Network.getAllCookies。搜索页是 SPA, 结果需 CDP 滚动 + innerText 正则提 IP, 再批量探测(80/443/8080 + title + login 特征)筛真面板。
- **二进制 WS 平台 9999 = 字段错,不是握手缺失**:手工拼包字段类型/长度错(如 char16 少 padding、`uint8_t s:N` 当字符串写)时,服务器统一回 `9999 "系统繁忙"` 伪装拒绝 — 别被误导去补"握手序列"。**先复刻前端 writeData 模板驱动 + 用前端默认值填字段**,一次即通。参考 m9600:模板驱动后登录回 rc=11(密码错误)、注册成功。
- **协议加密 + C库主动断连 = Python/原生 WS 复现必失败**:这类平台的 wasm 网络库在 C++ 层做握手(客户端 54B+服务器 12B 随机种子)+ 加密,RAW 帧无明文命令号。用 Python/raw WebSocket 手工构造包要么超时要么被 9999 — 别在这条路上浪费时间,**直接 wasm-in-Node 驱动或 CDP 真实浏览器**。断连(code 1006)是 C 库自己 `close(1000,"failed")`,不是服务器踢;hook 底层 `RealWS.prototype.close` 可确认,拦截后连接保持但 C 库状态已乱不再回调。
- **CDP 驱动真实 Chrome 处理反自动化 + 后台节流**:目标有反自动化时直接 navigate 会被 about:blank 拦截 — 用 `Page.addScriptToEvaluateOnNewDocument` 在导航前预注入脚本(隐藏 navigator.webdriver 等);后台/headless tab 的 rAF 被节流导致 C 库主循环停(statusCb 永不触发)— 必须 `Page.bringToFront` + `Emulation.setFocusEmulationEnabled` + `Emulation.setIdleOverride(isUserActive:true)` 强制激活;建 tab 用 PUT(Chrome 150+ 拒绝 GET /json/new)。**有头 Chrome + `--disable-blink-features=AutomationControlled` 反检测显著弱于 headless**,一次不行就换有头重试;页面加载后先查 `getSendBufferSize()==16376`(已自动连接)→ **复用已有连接直接发命令**,不要重复 startWebsocket(返回 true 但回调永不触发)。
- **错误码字典即用户枚举器**:协议类平台注册/登录错误码直接区分账号状态 — `rc=11 密码错误`(账号存在)、`rc=12 账号已经存在`、`rc=9999 系统繁忙`(伪装拒绝/风控)。逐个手机号打登录,rc 不同 = 用户枚举。
- **前端硬编码 checkCode 就是验证码绕过**:注册请求的 checkCode 字段取前端 `registerAccounts` 初始对象里的默认值(如 `"123456"`),服务端往往不校验 = 任意手机号注册。协议平台先试默认值,别去破解短信。
- **服务器每次响应后断连(1006)的根因是 msgCb 没返回 true,不是"正常行为"**:C 库(wasm)根据 msgCb 返回值判断响应是否被消费 — 返回 undefined/false → 调 `closeWebsocket(1000,"failed")` 主动断连(1006),重连后无登录态 → 查询回 105。**msgCb 末尾必须 `return true;`**(前端 processNetPack 无条件 return true 所以正常)。先查这个再怀疑重连/心跳/其他。修复后连接保持,可连续发包做撞库/批量查询。
- **登录逻辑绕过(参数篡改)对这平台无效**:空密码/账号=密码/手机号变体/SQLi(' OR '1'='1)/NoSQL/数组/布尔/超长 — 全部回 rc=1 或 rc=11,无绕过。这类平台认证是服务端严格比较 MD5,别在参数混淆上浪费时间。
- **REST 签名复刻后仍 403 = 无管理接口面**:从前端 JS 提取签名(密钥如 `7f6e5d4c3b2a1f0e9d8c7b6a`,signedPost = sorted params → timestamp+body → HMAC-SHA256 hex),验证签名正确(`signerror`→业务错误=签名对),但 /api/admin/* /api/agent/* 仍统一 403 — 说明无此接口面,别扩大枚举。
- **客服/辅助系统是独立攻击面**:customer_info 接口泄露客服系统 URL(带会话 token);客服 SPA 主 JS 里有独立 API base(如 `apic.dwlmjmcw.xyz`)+ **AES-256-CBC 密钥/IV 硬编码**(密钥 `DfoieDOsdkfmfkwofxoDMytduexwJkmN`, IV `IfklajiocsowmJsk`,ZeroPadding),axios interceptor 加密 timestamp+uuid。用 Python 复刻加密后可直接探测其 /v1/ 端点(匿名文件上传 /v1/file/base64 可用,其余 401/404)。
  - **真实 API 路径要用 CDP 抓包发现**(静态 JS 只见 2 个 /v1/file 路径):客服聊天 API 实际是 `/customer-service/v1/customer/history|config|m|send2|typing`,在动态加载的 HomePage chunk 里。
  - **实际鉴权格式不是 AES 加密 body**(2026-08 深入):请求头 `X-Timestamp: <加密base64>(密钥非前端主密钥,解密失败)` + `merchant-id: 12`(唯一有效值)+ `Content-Type: application/json`;body 明文 `{"cid":"<会话token>"}`;响应明文 JSON。
  - **cid 从主站 customer_info 的 liveVivai_customer 链接 hash 段获取**;客服 SPA 首页 "Invalid Link",必须带有效 token 才进聊天界面;带有效 cid 的 history 返回聊天记录(content AES 加密,密钥未知)。
  - **cid 校验严格**:随机/变体 cid → 422 "cid error";merchant-id 只认 12 → 客户视角单会话,不可枚举。
  - **客服工作台 API 存在但 401**:`GET /customer-service/v1/service` 和 `/service/history` → 401 "invalid credentials";login/auth 全 404 = 无公网登录入口。能看所有用户会话的客服端锁死,诚实报告"客户视角只拿到自己会话"。
- **端口扫描全 OPEN 是 TUN 假象**:所有端口 bash /dev/tcp 和 Python connect 都"成功"= singbox_tun 接管,端口结果一律不写入报告。
- **SignalR send 500 的常见原因**:①Content-Type 必须是 `application/x-www-form-urlencoded`,data 参数 URL 编码 JSON(`data={"H":"lobbyhub","M":"Method","A":[],"I":0}`);②connectionToken 参数要用 negotiate 返回的 ConnectionToken(DPAPI 长串),不是 ConnectionId;③hub 名小写。
- **"The ConnectionId is in the incorrect format"**:token 与会话 cookie 不匹配(cookie 没保持)或参数用错;用同一 cookie jar 走完整流程。
- **未登录 hub 不连接**:`hub.server` 为空 = 连接未建立,别在浏览器 console 死磕 `createHubProxy`;方法清单已拿到就够写攻击面。
- **BFF 注册字段是扁平大写驼峰**:前端 signUpModel 是嵌套(stepOne/stepTwo/stepThree),后端接收扁平字段(FirstName/CountryCode...);直接 curl 用扁平结构,别照前端嵌套发。
- **后端 libphonenumber 手机号校验严格**:前端过(纯数字 6-13 位不以 0 开头 + PhoneNumberCountryCode 传 ISO3)≠ 后端过;带 `+` 会触发另一校验报 "Provider: ... digits only"。**先逆向前端提交转换函数**(FairGo: `normalizePhoneNumber = "00"+去非数字` → 提交 `00`+国家码+本地号,一次通过),别盲试组合;仍失败再换思路走 hub `CreatePlayer`。
- **RTG ProduceSessionID bug 不是硬墙 — CDK.logIn() 高层 API 绕过(2026-08 FairGo 实战突破)**:直接 `CDK.invokeHubMethod(hub, 'Login', user, pass)` 会触发 `Expression of type 'System.Int32&' cannot be used for parameter of type 'System.Int32' of method '...ProduceSessionID(...)'`(服务端 C# ref 参数反射 bug,API Level 3-6 全触发)—— 但这只是**调用方式错误**,不是平台锁死。**正确登录 = 浏览器里调 CDK 高层 API**:
  ```js
  // CDK.logIn(login, password, forMoney, rememberPassword, isLoginRequest)
  CDK.logIn('user', 'pass', true, false, true)
  // 内部构造 10 参数 SignalR 调用:
  // lobbyHub.invoke(Login, login, password, forMoney, forceCasinoLogin,
  //   playerSessionID, os, browser, userAgent, isLoginRequest, timeZoneUser)
  ```
  从 CDK.js 逆向:登录函数定义 `function (login, password, forMoney, rememberPassword, isLoginRequest)`,调 `lobbyHub.invoke(LobbyHubMethods.Login, ...)` 10 个参数(环境指纹 os/browser/userAgent/timeZoneUser 由 BrowserDetection 生成)。**登录成功后**自动触发 `GetPlayerBalances` + `GetCashierSettings("deposit"/"payout"/"coupon")` 初始化 — console 出现 `Invocation of lobbyhub.Login returned` + `databasenotifyhub.Register [pid, ...]` = 登录态建立。**别用 invokeHubMethod 直接调 Login(2 参数必挂),先找 CDK.js 里 `cdk.logIn`/`LobbyHubMethods.Login` 的高层封装**。认证凭据:测试账号密码或注册响应 providerSignInUrl 的 login/token。游客连接无会话方法仍可用(GetPlayerMessages/GetCasinoJackpot*/GetCashierSettings)。
- **data-js-vars Base64(UTF-16LE)**:ASP.NET MVC 赌场站 `<html data-js-vars="...">` 是 HTML entity 编码的 Base64,解码用 **UTF-16LE**(不是 UTF-8):`base64.b64decode(h.unescape(v)).decode('utf-16-le')`。内容含 casinoLoginUrl/mgsId/apiDomain/eipa(加密参数)/affId — 全平台配置一把梭。
- **Gambit/MGS deviceinfo 必须 JSON**:`?deviceinfo=` 参数传字符串报 `'D' is an invalid start of a value`(JSON 解析错误);传 URL 编码 JSON(如 `{"platformName":"Desktop","browserName":"Chrome",...}`)才返回完整 SPA。Gambit `/gambit/api/*` POST 415 = 端点存在但需特定 Content-Type/格式(非标准 JSON,值得深挖 SPA main.js 还原)。
- **错误驱动字段枚举**:对注册类接口发 `{}`,每轮按错误补字段,错误信息本身就是完整字段清单 + 格式要求(3字母 ISO 国家码、E.164 手机号等)— 比逆向前端 JS 快得多。
- **邮箱域名黑名单**:注册接口会拒部分邮箱域名("Email account invalid"),yahoo/gmail 通常过;proton.me 类匿名邮箱常被拒,别浪费轮次。
- **Azure Blob 路径双斜杠**:`content/client//lobbyCorePackages/...` 的双斜杠是路径的一部分,去掉会 BlobNotFound。
- **HTTPS 直连源站常超时**:源站 443 防火墙只放行 Cloudflare;用 HTTP 80 + Host 头打。
- **CF 绕过全技术栈评估 (2026-08 m9600 白标 = 无缝隙)**:41 域名全 CF、历史 DNS(ViewDNS/RapidDNS/crt.sh/certspotter)无数据(证书只有通配符)、子域爆破 230+ 词全 CF、AXFR 拒绝、无 SPF/DMARC(无 MX)、whois 隐私保护、Wayback 无源站 IP、FOFA 候选 IP 验证无效、nginx 指纹(1.20.1/1.26.3)无内部泄露、CNAME 链无差异、第三方资产(linkedbro/macan-native)是广告/分析 SaaS 非源站。**结论:白标平台"教科书级" CF 配置 = 无缝隙,纯外部渗透绕过不可行** — 无邮件(无 SPF 泄露)、无历史托管、无未保护子域、无 IP SAN 证书。剩余真实选项:Shodan 付费 API / 长期监控 / 客服工作台凭证(无入口)。别在源站绕过上无限消耗,该结论直接写进报告。
- **WAF 站点**:主站 403 别硬打,子域(cdk/m/play)通常无 WAF。
- **Joomla 赌场主站 = 内容壳**:充提页面(/banking /cashier /withdraw /cashtocode)常是 Joomla 内容页,无充值表单 — 资金操作全在 RTG 收银台(登录墙后)。Joomla 的 `/api/`、`/administrator/`、敏感文件(.bak/xml)被 CF WAF 统一 403/挑战,Googlebot UA 也拦;源站 www 虚拟主机也常走 CF 回源(仅 cdk 虚拟主机直连 200)。结论:Joomla 面(CVE-2023-23752 等)大多被 WAF 封死,别花太多轮次,直接聚焦 RTG 平台与注册体系。
- **RTG 登录 token 消费端未还原时别死磕**:`CDK.validateExtToken(user, token)`(参数顺序 user, token,从 CDK.js `cdk.validateExtToken = function (user, token)` 还原)新 token 也回 ErrorCode 2000 空引用;`providerSignInUrl` 浏览器打开 username 仍空。注册响应带 token 是设计缺陷(记录为漏洞),但消费端点未知 = 诚实报告"注册链通、登录态未建立",转 PII/枚举面。
- **GET 返回 SPA 兜底(200 HTML)≠ 端点不存在**:Express/Next.js catch-all 会把任何 GET 路径渲染 index.html(200 + 页面 HTML)。判断 API 是否存在的正确方法:**试 POST + JSON body** — 返回 `{"Result":"FAIL","Reason":"INVALID"}` 或 405/415 = 端点真实存在,只是需要正确参数/方法;全 404 才是真不存在。
- **混淆字符串表是 rotor 旋转的,静态索引不可信**:混淆 JS 里 `a0_0x2207()` 返回的字符串数组被 `(function(){...}(arr, 0x8437b))` 循环 shift 旋转,直接数数组下标映射字符串是错的(exponent 索引静态值可能恰好命中也可能错)。**必须动态解码**:Node vm sandbox 加载原 JS 后调用解码函数(`a0_0x55e8(0x175)`)拿真实字符串,再用它做算法判断。AQ777 encrypt.js 的 RSA exponent 0x10001 就是先静态猜、后动态验证确认的。
- **加密接口 `decryption.err` = 加密链复刻错,不是业务错误**:服务端回 `decryption.err`(#132)说明 RSA/DES 复刻与前端不一致(JSON 无空格、rand 反转、DES key 前 8 字节、**mode 用错(CBC vs ECB)** 等任一错都会触发)。**别用无 encrypt 标志的接口(如 freeplay)验证加密链** — 那些走明文,返回 `function.not.available` 不代表链对;真正验证 = 加密接口的 `decryption.err` 是否消失。**正向信号:登录接口从 `decryption.err` 变成 `geetest_captcha_err`(#1334)= 加密链已 100% 正确**(服务端已解密并进入业务校验);带任意 `geetestChallenge/geetestValidate/geetestSeccode` 字段即可绕过 Geetest v4 登录。**一直 decryption.err 时先动态解码字符串表确认 mode**(AQ777 系是 DES-ECB 不是 CBC)。
- **EdgeOne(TencentEdgeOne)CDN 用 Python urllib 打,Node/curl 被 TLS 指纹拦**:567 状态 + 7351B JS 挑战页 = EdgeOne JS 挑战;浏览器 navigate 被 SPA 反自动化跳 about:blank。`urllib.request.build_opener(HTTPCookieProcessor, HTTPSHandler)` + 浏览器 UA 直接过,静态 JS 全量下载用 Python。
- **API 前缀藏在 fetch() 里,常不是 /api/**:前端 JS 搜 `fetch(` 全部调用点再提取路径 — 站点常自定义前缀(`/slotswin-api/`、`/bff/api/`、`/slotswin-api/get-*`)。无鉴权枚举模式:POST + JSON(`{"Login":"<用户名>"}`)→ `SUCCESS`/`INVALID` 差异 = 用户名枚举器;`{"Email":"<邮箱>"}` → `SUBSCRIBED`/`INVALID` = 邮箱枚举器;GET 类如 `get-recent-winners`/`get-progressive-jackpot` 直接泄露玩家姓名+金额/实时奖池。详情见 references/slotswin-api-enum-case.md。
- **枚举器拿到用户名后必试 profile/subscription 端点升级 PII**:营销类端点(订阅查询/资料查询)常直接返回**完整邮箱**而不只是存在性 — `get-player-subscriptions {"login":...}` 一步从"用户存在"升级为"用户名+完整邮箱+订阅状态"泄露。参数名可能小写(`login`)与 tier 接口大写(`Login`)不同,从各自 `var params` 还原。盈利链:邮箱+真实用户名 → 钓鱼/撞库 → 账号接管 → 收银台余额。
- **充提/余额篡改面定位(先测这四件事再下结论)**:①RTG 收银台 `GetCashierSettings` 报 `"was not logged in while inside ..."` = 收银台在登录墙后,叠加 ProduceSessionID bug = 双重保护,直接篡改向量不存在;②回调/webhook 伪造面:探测 `payment-callback`/`deposit/notify`/`ipn`/`webhook/*` 等路径,**Express 未注册路由返回真 404**(区别于 catch-all 200 HTML)= 无回调面;③充值/提现 API 爆破(`api/deposit|withdraw|balance|cashier|payment|transaction`);④现金返还系统 `*Bonus*`/`*Coupon*` 端点(如 `/GetOutBonusForPlayer` 查询 + `/RedeemCoupon` 兑换入余额)= 最接近余额操作的无鉴权面,测归属校验与 ID 可枚举性。四件事测完仍无公开余额 API = 诚实报告"无直接向量 + PII 间接链"。
- **字符验证码 403 语义判别(浏览器弹窗法)**:curl 拿到的 `{"code":403}` 无法区分"验证码错误"vs"账号密码错误"。**判别法:浏览器真实提交**(browser_type 填识别码 → 点登录 → 读 layer 弹窗文本):提示"用户名或密码错误,你还可以尝试X次" = **验证码已过,403 是密码错**;提示"验证码错误" = ddddocr 识别率问题。**跨 session 验证码一致性**:先 browser_console 拿 `document.cookie` 的 PHPSESSID,再用 curl/urllib 带同 SID 下载 code.php 识别,值即当前 session 验证码 — 无需在页面内读图。ddddocr 对 4 位混合字符验证码有效(投票/预处理可提升),但注意验证码长度可能 3-4 位不稳定。
- **PHPWind 7.3.2 登录态细节**:认证 cookie 是 `c7a50_winduser`(httponly);curl -c/-b 保存的 `#HttpOnly_` 前缀行用 `-b` 读取可能不被识别 → **手写 `-H "Cookie: ..."` 最稳**。响应"您已经为会员身份,请不要重复登录!" = 会话已登录。登录态可能绑定出口 IP(代理出口漂移后 winduid 变空回 guest)。新注册用户 groupid=7 默认**不能发帖**(需管理员验证,"您还没通过管理员验证,需要通过管理员验证才能发言！")→ 附件上传 getshell 前先确认发帖权限。

## Verification

- [ ] 完成批量指纹一轮,按信号分级
- [ ] 识别是否白标平台(RTG/Softech)并拿到平台核心 JS
- [ ] SignalR negotiate/connect 验证(无鉴权?)
- [ ] 已枚举 hub 方法清单(记录为攻击面)
- [ ] 已找源站(非 CF IP + Host 头直连验证)
- [ ] 报告含:站点总览表 / 高危发现(复现)/ 盈利性分析 / 诚实声明(未做破坏)

