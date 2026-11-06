## 核心知识

### 1. 包网平台是什么

包网 = 白标赌博平台:自己不研发游戏,聚合多家游戏厂商(PG Soft/CQ9/JDB/JILI/W Game/AG 等)的接口,做统一分发、运营、风控。典型结构:

```
玩家 → 包网平台(白标) → 游戏厂商 API(Create Session / Launch Game)
                ↓
          API 请求参数携带 rtp_level / config_id
```

### 2. RTP 动态风控(核心机制)

**RTP = Return To Player(玩家返还率)**。RTP 95% = 玩家每投注 100 元,长期平均拿回 95 元;平台留存 = 100% - RTP。

- 平台调游戏厂商 API 拉起游戏时,通过 `rtp_level` 或 `config_id` 参数**按玩家画像指定该局 RTP**
- 识别到"高风险/刷子账号"(赢太多、异常下注、多开、脚本) → 自动传参指定**最低档 RTP** 止损
- 双轨风控:"玩家看到的公平"和"平台实际控制的概率"是两套系统
- 每个游戏厂商接口可单独配 RTP 档位(见 references/gambling-rtp-knowledge.md)

### 3. RTP 档位体系(实战观察)

配置后台常见档位:
| 档位 | 含义 |
|---|---|
| 0 | 关闭 / 未配置 |
| 1 | 正常官网 |
| 2 | 平衡慢杀 |
| 3 | 快杀(返还率最低,平台留存最高) |

> 档位越高,返还率越低。RTP 区间参考:70%-79% 高风险(大奖概率极低)、50%-69% 极度波动(多数输钱)、<50% 几乎无返奖。

### 4. 典型游戏厂商缩写

PGS=PG Soft、CQ9、JDB、JILI、W(G) Game、AG(亚游)等 —— 都是包网聚合的老虎机/捕鱼/棋牌厂商。前端配置里厂商常以数字 type ID 出现(1=PG、2=Jili、12=PP、16=FC、17=CQ9、18=JDB、19=WG、20=SPADE、21=G759、22=POPOK、15=Hacksaw),见 references/ph-gambling-frontend-recon.md。

### 5. 菲律宾博彩站特征(实战)

- 货币/时区:PHP ₱ + Asia/Manila,英文界面,面向菲律宾玩家
- 多域名镜像矩阵:OneSignal 推送配置常泄露 30+ 镜像域名(同一前端/后端防封)
- API 后端与资源 CDN 分离(CDN 管静态,API 在独立域),HTTP API 常见 HMAC 签名(硬编码 key 在前端 JS 可提取)

### 6. RTG(RealTime Gaming / LobbyCore)白标平台渗透

RTG 是常见赌场白标平台(FairGo/OzWin/SlotsWin 等澳洲向赌场用)。**架构**:

```
<域名> 主站(Joomla/WP,CF WAF)
├─ cdk.<域名> — LobbyCore 26.07.0 大厅(SignalR 2.x, hubs: lobbyhub/gamehub/databasenotifyhub/tournamentshub)
├─ signup.<域名> — 注册 BFF(/bff/api/*,常见 /auth/signup)
├─ m.<域名>:2500 — 移动端收银台(Router.ashx),源站直连带防火墙
├─ cashier.<域名> — 收银台登录域(loginRTG.asp)
└─ gmgall.cfcontentdnfls.eu — RTG 公共 CDN(CDK.js 等)
```

**核心绕过(最重要):** 直接 `CDK.invokeHubMethod(hub,'Login',u,p)` 会触发服务端 ProduceSessionID 反射错误(`Int32&` vs `Int32`),但 **`CDK.logIn(login,password,forMoney,rememberPassword,isLoginRequest)` 高层 API 完全可用**(内部构造 10 参数 SignalR 调用:login,password,forMoney,forceCasinoLogin,playerSessionID,os,browser,userAgent,isLoginRequest,timeZone)。CDK.js 里所有 `cdk.xxx` 高层封装都走正确流程。

**登录后数据接口(全部可用):** GetPlayerBalances / GetAccountInfo(泄露**密码哈希**+完整PII) / GetCashierSettings(泄露 **RTGPID+HashedPassword(SHA1)+CashierSessionID+收银台URL**) / GetAvailableCouponsInfo / GetAccountHistory / getPlayerMessage(ID)。

**游客可用方法(无需登录):** GetPlayerMessages / GetCasinoJackpotBalance / GetMinimumAllowedCompPointsToRedeem / GetCashierSettings(部分实例)。**注意不同实例配置不同**:FairGo 游客可用,SlotsWin(cdk:6072)游客也挂 bug。

**优惠券盈利链:** 注册 → CDK.logIn → `redeemCoupon('WELCOME')` 挂起首存红利(IsDepositPending:true, 下次存款自动兑) → `getPlayerMessage(ID 1..N)` 枚举全平台营销模板 → 提取 `CODE: xxx` → 按条件兑换(错误消息泄露兑换条件:周一限定/过期/VIP)。见 references/rtg-lobbycore-pentest.md。

### 7. Gambit(Microgaming / gameassists)平台侦察

- 注册页需 `?deviceinfo=<URL编码JSON>`(字符串会报 `'D' is an invalid start of a value`);拿到后返回完整 Angular SPA
- SPA HTML 内嵌 `appSettings` = **完整 API 基础设施泄露**(userClientPublic/bffApi/bffGatewayApi/microServiceApi/playerHistoryPublic/responsibleGamingPublic/bankingPublicApi/gameLaunch URL 模板)
- API 模式:`POST {apiUrl}?q=MethodName`,body `{"query":"{GraphQL...}"}`(q= 方法名如 getInitialLobbyDataAsync/checkUserExistsAsync/getRedirectorDataAsync)
- **UCP(userClientPublic)全端点 401**,注册→token 鸡生蛋;gambit/api/* 返回 415(Content-Type 严格);MobileWebServices_40 的 launch 端点 406 泄露完整 DTO
- **BFF Gateway 无鉴权打通(核心!)**:`https://<gambit域>/Gambit.BFF.Gateway.API/v1` 用 POST + 完整头(X-CorrelationId GUID / X-ClientTypeId 97 / X-ProductId 2435 / Accept-Language en)+ body `{"launchDarklyContext":{"MarketType":"UK","OperatorName":"bluemesa","DeviceInformation":{...}},"request":{...}}`(模型校验错误驱动枚举字段!);端点:`/redirector/getRedirectorResponse/product/{pid}`(appIds 是 Int32 数组,如 register=1003/forgotpassword=1059/gamehistory=1001)、`/personalaccountinformation/user/checkUserExists/product/{pid}`(**无鉴权用户枚举:{"loginName":"x","model":{},"launchDarklyContext":{}} → {doesExist,userId}**)、`/mfa/state/product/{pid}/user/{userId}`(**无鉴权 MFA 状态 IDOR**)、`/features/getFeatureToggles`、`/game/GetGroupedGames`、`/geolocation/*`
- **Redirector 泄露全资产地图**:services.cr-brands.com(lobby/messages/forgot、support、terms、responsible-gambling — 参数含 userName/accountNumber/casinoID/loginAttempts)、playcheck2.gameassists.co.uk(PlayCheck 玩家历史)、etiloaderqf2.gameassists.co.uk/ETILoader/Default.aspx(游戏加载器,带 username/password/launchtoken)、lobby-loyalty.cr-brands.com
- **登录走 swift(可绕过)**:swift2.gameassists.co.uk(CF 挑战全挡,curl 403/404 + 浏览器 Turnstile);swift iframe URL 构造 `https://{swiftDomain}/swift.stateMachine/swiftlaunch/embedded/{hostIdentifier}/{productId}/{clientTypeId}/{lang}/{initialProcess}`(hostIdentifier=gamBitLobby);**embedded 路径返回 200(绕过 CF 挑战!)** — swift 根路径 403/404,但 `/swift.stateMachine/swiftlaunch/embedded/...` 直接 200(CF 只保护了入口页);**后端域 swift2g.valueactive.eu 无 CF**(同路径 200);swift 页面泄露 options 配置(InitialProcess 如 banking_full/registration)与客户端 JS 清单;**真正登录 API 在 UCP UserPublicBaseUrl 可直连绕过 swift(见下)**
- **swift 支付模块(money-in)**:`{valueactive}/swift.stateMachine/money-in/money-in-min.js`(383KB)含支付方式逻辑 — ACH/eCheck(461 处)/Interac(110)/visa/mastercard/Sirius card→wallet 映射;PurchaseMethod 结构(PurchaseMethodId/TypeId/PMOPV2Supported/PayoutCurrencies[]);完整方法列表需登录后 API 动态加载,JS 里只有品牌痕迹
- **UCP 登录 API 直连(绕过 swift!)**:`https://api2.gameassists.co.uk/casino/user/public/v1/accounts/login/real` POST + headers(X-CorrelationId GUID/Accept-Language: en/X-ClientTypeId: 97)+ body `{"userName":"test","password":"x","numLaunchTokens":10,"sessionProductId":2435,"otp":"","token":""}`;错误码:41000=密码错/42900=限速/**429 限速按账号维度(换用户名可绕过,每账号约 3 次尝试)**;其他端点:`/accounts?fields=Balance`(余额,需 token)、`/accounts/negotiateSession`、`/accounts/login/token`、`/accounts/refreshUserToken`、`/accounts/redeemLaunchToken`、`/session/preLogin/product/{pid}`(无鉴权,deviceProfile 检测,body {"vendor":"1","lobbyName":"x"})
- **UCP 客户端库泄露**:`GET {ucp}/clients?productId={pid}&variablename=userClientPublic&lobbyname={lobby}&clientlang=en&clientTypeId={ctid}&v={ver}` → 配置(UserPublicBaseUrl/NumLaunchTokens/SessionTimeoutSec/LoginRequestFields);`{ucp}/clients/library?v=` → 225KB PlayerService 库(URLBuilder 全端点/headers 构造/登录 body 结构全部可还原)
- **UserPublicAPI 全端点(api2.gameassists.co.uk/casino/user/public/v1)**:`POST /accounts/login/demo`(**无鉴权返回完整玩家会话!account+tokens(userToken+10 launchTokens+refreshToken)JWT RS256**)、`POST /accounts/login/real`(用户名密码,41000=密码错,42900=限速按账号可绕)、`/accounts?fields=Balance,Core,Session`(带 Bearer token)、`/accounts/negotiateSession`、`/accounts/login/token`、`/accounts/refreshUserToken`、`/session/preLogin/product/{pid}`(无鉴权,vendor检测)
- **VeyronProxy 内部网关**:`/account/v1/*` 存在(需 X-Route-ProductId + X-Route-ModuleId 路由头,错误泄露路由机制);JWT kid/cert(MGS.UserSessionToken.MAL.20230719)/iss(account/v1)泄露
- 关键端点:getRedirectorDataAsync(跳转器,url+httpMethod+parameters)、getCredsAsync(`{ucp}/sessions?productId=&lobbyName=`)、login-proxy(iframe 桥)
- 见 references/gambit-mgs-pentest.md

### 8. 独立收银台 / 充提面 / 源站

- **收银台**:RTG 在独立域(cashier.<域名> + m.<域名>:2500 Router.ashx);路由 `?route=Cashier&pid=<RTGPID>&token=<GUID>s@Lt&clienttype=f&skinid=1`;token 每次触发刷新;源站防火墙(curl 超时,仅浏览器 iframe 间歇可过)
- **回调/webhook 枚举**:payment-callback/deposit-callback/ipn 等,Express 后端未知路径返回 SPA 兜底(200 HTML),404 才是真不存在
- **Express 无鉴权 API 模式(slotswin)**:/slotswin-api/get-player-tier(玩家存在性)、validate-email(订阅状态)、get-player-subscriptions(**完整邮箱泄露**)、get-vip-status、get-new-player-status、get-progressive-jackpot、get-recent-winners(玩家名+金额);/GetOutBonusForPlayer(现金返还列表)、/RedeemCoupon(兑换)
- **源站发现**:m. 子域常解析到非 CF IP(如 190.4.90.x 哥斯达黎加段);cdk Host + 源站 IP HTTP 直连可绕过 CF;HTTPS 443 常被源站防火墙挡;www Host 走 CF 回源仍被挡
- **主站 CMS**:多家共用 Joomla + CF WAF(/api/、/administrator/ 全 403,Googlebot UA 也挡;若找到源站可绕 CVE-2023-23752)

### 9. 充提方式情报调查(判断是否支持 USDT/加密)

- **FAQ 页面最快**:赌场官网 /help/banking 或 FAQ 的 Banking 小节,浏览器展开 dt/dd 提取官方支付方式清单(实测 luxury.casino → /en/faq/,列卡/电汇/电子钱包/Interac)
- **thirdPartyBanking 配置判断加密支付**:appSettings 里 `thirdPartyBanking.launchURL` 是占位符(`https://www.google.com`)= 第三方银行/加密支付**未启用**;真实配置指向支付平台域
- **前端 JS 关键词搜索注意**:压缩代码里 grep 会被 eCode/eContext 淹没,用 Python 精确正则 `(?i)usdt|bitcoin|crypto|bank ?transfer|interac|neteller|skrill`
- **受监管赌场通常无 USDT**:安大略/Kahnawake/合规横幅背景 → 反洗钱合规不允许匿名提现;预期 = 卡/电汇/电子钱包/Interac
- **提现参数**:最低金额分方式(DBT/WIRE $300 vs 其他 $50)、48h 待定期可撤销、PMOP(首选支付方式)机制 — 这些对提现面测试(篡改/竞态)有用
- **批量扫 10+ 站加密支持(并行脚本,见 scripts/usdt_payment_scan.py)**:①主页 HTML ②主页引用的前 6 个 JS ③常见支付路径(/banking /cashier /payment-methods /deposit /crypto /withdraw),ThreadPoolExecutor(5 worker, 超时 5-7s);关键词字典按币种(PAT: USDT/BTC/CRYPTO/ETH/加密支付商)
- **关键词出现 ≠ 支持(必须验证上下文)**:可能是 "We do NOT support crypto" 否认性说明。验证法:提取命中前后 120 字符上下文;**支付 logo 图片是最强证据**(footer/banking 页的 `tether.png`/`bitcoin.png`/`bitcoin_cash.png` 图标 = 实际支持的支付方式)
- **实测结论(2026-08,10 站)**:RTG 澳洲系(FairGo/SlotsWin/OzWin/Freespinz/RedDog)+ 纯加密站 crypto-games.io 支持 USDT/BTC;BFF 合规系(luxury.casino)+ whamoo/slotslite 不支持。**FairGo/SlotsWin 的 RTG 收银台(loginRTG.asp 登录后)有加密支付选项** — 撞库/接管后余额可 USDT 提现(匿名变现),显著提升盈利链价值
- **自动到账判断(出款效率=变现关键)**:支持 USDT ≠ 自动出款。判据:①官方 FAQ/条款明文 — 纯加密站(crypto-games.io)写 "Once you confirm the withdrawal, the funds will be sent to your specified address" + "**instantly or within 15 minutes**"(确认即广播链上交易,零审核);RTG 系(FairGo 明文)写 "Payouts are processed within **2 business days**" + "must first complete the required **verification process**"(人工审核+KYC,非自动;OzWin/SlotsWin 同平台同政策);②网络限定 — reddog 明文 "The casino supports **ERC20 network only**"(USDT 走 ERC20,TRC20 不支持);③第三方银行集成状态 — appSettings thirdPartyBanking.launchURL 为 google.com 占位符 = 加密支付未启用。变现效率排序:纯加密站自动(≤15min)>> 加密友好自研未明文(需登录实测)>> RTG 人工(2 工作日+KYC 审核风险)。**零成本套利(OzWin 免费$10)vs 自动出款(crypto-games)是两条独立属性 — 评估盈利链要同时看成本和出款速度**
- **reddog-games 平台特征**:Next.js 自研前端(非 RTG 标准白标),join.reddogcasino.com 注册代理(连接超时);支付页明文 "Tether (USDT) processing fees viewable in Cashier"(USDT 最低存款 $40 USD/EUR、$60 AUD);footer 支付 logo: bitcoin/litecoin/ethereum/tether/flexepin/visa/mc;页面链接 /api/health 返回裸 "OK" 是真 API 存活信号,POST 到 Next.js API 路由返回 405

### 10. 自研加密赌场(crypto-games.io 模式,非 RTG/Gambit)

- **指纹**:Next.js/Vercel SPA + 币种图标阵列(bch/bitcoin/doge/ethereum/ltc/trx/usdc/usdt/xlm)+ Welcome Pack 大额 USDT(实测 20,000 USDT)+ 60+ 游戏提供商
- **找真实 API 域(关键技巧)**:curl 抓 Next.js JS 常被内容拦截(200 但 0B / Failed to fetch);浏览器加载页面后 `performance.getEntriesByType('resource')` 提取**页面实际发出的 API 请求**(实测发现 `api.crypto-games.io`);有 `/api` 路径但返回 SPA 兜底 HTML = catch-all,真 API 在独立子域
- **无鉴权端点**:`/games?gameCategorySlug=...`(游戏列表 id/uuid/provider)、`/promotions`、`/bonuses`(**奖金结构:depositBonuses[{percentageReward,currencyType:"CRYPTO"}]+ otherBonuses[{type:"SPINNER"}]**)、`/tournaments`(**奖池金额+币种,全 USDT 计价**);/user /balance /wallet /withdraw 401(需 token)
- **注册链**:Email+Password(+ 可选 Referral/Promo Code 字段),无验证码/邮箱确认/限速 → 注册即 JWT(cookie `staging_accessToken`,payload {sub, role:"DEFAULT_USER", iss:"/registration", sessionId, exp 30 天});注册后页面出现 Deposit/User avatar = 成功信号
- **API 直调注册(绕过 UI,实测)**:`POST api.crypto-games.io/registration` body `{email,password,promoCode:"",acceptTerms:true,currency:"USDT"}` → 200 直接返回 `{accessToken,accessTokenExpiresIn:2592000,refreshToken}` — 一行 curl = 一个账号,批量全自动;登录 `POST /auth` body `{username,password}`(401 "Invalid email / username or password" = 凭据错,字段名 username 不是 email!)
- **用户 API 族(带 Bearer token)**:`GET /me`(会话确认)、`/user/transactions?size=N`、`/user/wagers?size=N`、`/user/notifications?size=N`(分页)、`/user/vip`(vipStatus.level/name/wager)、`/bonuses`(带 token 泄露 isClaimed/canToggle);`/user` 400 缺 `size` 参数 = 分页列表端点
- **游戏引擎面(自研 24 款 provably fair,最新)**:游戏启动 `POST /games/{slug}/launch`(**slug 格式,id/uuid 都 404**)→ 第三方游戏走 **gis.slotegrator.com**(Slotegrator 聚合,URL 两个 base64=AES 加密会话,常拒 curl);自研游戏走 **playmg.crypto-games.io/{game}?token=v2.x** + 游戏服务器 **server.maktub.bet**(游戏 token 直接 curl 可调):`/balance`、`/game/config`(houseEdges 庄家优势 + betLimits + **fairnessMode:"rng"** = 非真 provably fair)、`/game/seeds`(clientSeed/hashedServerSeed/nextHashedServerSeed)、`/freebets?game=x`(免费下注)、`/game/bets/recent`、`/user/save/rotateSeedPair`;下注 `POST /game/dice {amount,betTarget,betCondition}` — **Zod 400 校验错误泄露完整 schema(amount/betTarget/betCondition 必填),betCondition 必须小写 over/under,校验链:格式→金额≥$0.1→目标1-99→余额**;负金额/0/非法目标全拦(防御扎实);demo:`launch?mode=demo` 给 demo token(同样可调引擎但余额 0);`api.crypto-games.io/slotegrator/callback` 游戏结算回调(**仅 form-urlencoded 通过,其他 415;通过后统一 500 = 签名验证防枚举,无密钥别硬刚**);余额 0 与资金端点不在 REST 是卡点。完整细节见 references/crypto-casino-pentest.md「游戏引擎攻击面」
- **Zod 批量 schema 枚举技巧(对任意 Node/TS 后端通用)** ⭐:`POST {server}/game/{每个游戏名}` 空 body → 400 Validation failed 泄露全部必填字段(实测一次枚举 11 款:dice/coin/hilo/limbo/mines/plinko/roulette/keno/blackjack/wheel/tower/baccarat,完整表见 references/maktub-crypto-games-pentest.md);错误路径数组 ["字段名"] 直接拼出下注 body;再对每字段传非法值(负金额/超范围)确认防护边界
- **Futures 杠杆交易面(Maktub 引擎,全新)** ⭐:游戏 token 可直调 `/futures/instruments`(8 品种,BTC **1500x**/ETH 1000x/SOL 1000x 杠杆)、`/futures/positions/open|closed`、`/futures/position/open {asset,multiplier,positionAmount,isUp}`(multiplier ≥ 1 校验)、`/futures/position/close {id}`;**价格流 io.pigmo.com Socket.IO(EIO=4 握手成功,socket.on("priceEmit") 无鉴权实时价格)** — 高杠杆+价格流无鉴权 = 套利假设面,需资金验证;锦标赛参与端点 `/tournaments/{id}/join` 存在(500 内部错误)
- **24 款游戏逻辑漏洞扫描(0 金额测试法 — 无资金测游戏公平性/找"百分百中奖")** ⭐:①**minBet=0 的 11 款游戏**(coin/cases/defuse/drop/launch/pulse/russianRoulette/safe/spark/volt/wire,来自 /game/config 的 betLimits)— `amount=0` 下注被允许并**完整执行游戏流程**,下注响应泄露完整 state(coinsResult/payoutMultiplier/payout/balance)→ 免费观察 RNG 分布、multiplier 计算、并发行为;②**multiplier 校验**:coin 3硬币全正 mult=7.92(理论 8 = 1% edge 正常),组合扫描无 EV>1;③**并发竞态**:5-10 路并发 0 金额下注 → 429 限速(约 2-3 req/s)+ 独立游戏 ID(相同 ID 前缀是时间戳非重复结算)→ 无双花;④**极小金额**(1e-8/1e-9)全被 Insufficient balance 拦(0 是唯一例外,别期待精度漏洞);⑤**cases 类多轮游戏槽位占用**:0 金额开启 → 新下注报 "You already have a running game"(游戏槽位被永久占用,轻微自 DoS;多轮游戏操作端点在服务端,前端新游戏常不在 playmg 旧版 UI);⑥**结论:自研引擎游戏无"百分百中奖"/无 EV+ 组合/无精度漏洞 — 公平性实现标准(house edge 1-5%,RNG 强随机),真正弱点在认证/业务层(注册零防护/任意密码重置/用户枚举),游戏层别浪费时间**;⑦限速 429 "Too many requests" 是全局的(并发/高频全触发)
- **Maktub B2B 游戏提供商管理面(自研引擎的服务商)**:子域枚举(并发 DNS + crt.sh)发现 **admin.maktub.bet**(运营管理后台,巴西团队葡语界面)/ **backoffice.maktub.bet**(另一登录入口)/ **docs.maktub.bet(完整 API 文档公开!)**/ staging.maktub.bet(营销页)。登录 API 字段**按后台不同**:admin 用 {username,password,totp},backoffice 用 {email,password};admin.maktub.bet **admin:admin 密码正确但返回 {"needsTotp":true}**(2FA 挡路,10 次错误码后 500 = 有防护,爆破不现实);其他账号全 401(无枚举,统一葡语 Usuário ou senha inválidos)。**CVE-2025-29927 中间件绕过已失效**(x-middleware-subrequest 头无效);Next.js 307 → /en/xxx locale 重定向不是路径存在的信号(所有路径都 307)。管理 API(/api/operators /api/users /api/webhooks)全 401(需会话)
- **Maktub webhook 伪造链(运营商余额注入面,机制完全逆向)**:文档 + npm 包源码(@maktubbet/webhook + @maktubbet/sdk 43MB 含全部游戏源码)泄露:①签名 HMAC-SHA256(secret, "{ts}.{rawBody}") → 头 x-maktub-signature: t=<ts>,v1=<hex>,5 分钟窗口,safeEqual 是 sha256 摘要比较;②**legacy x-webhook-secret 头携带明文 secret**(requireSignature=false 时签名失败会 fallback 到明文比对 — 旧集成弱检查);③payload {event, userId, customerId, betId, transactionId, roundClosed, sessionToken, actions:[{type:"bet"|"win", amount}]}(win=贷记,balance_check=查余额);④运营商(crypto-games)端点 /api/maktub/webhook 存在(JSON 401 = 自定义验证);**卡点:secret 随机生成(whsec_ 前缀,不可爆)** — 找泄露面:GitHub/npm/文档示例/环境变量。docs.maktub.bet 还公开 Exploit Checklist(精度/并发/重放攻击清单 = 官方承认的攻击面)
- **账号接管链(密码重置两步流程,全链打通)**:①`POST /forgot-password/request {"email"}` → 存在 200 / 不存在 **422 "Email does not exist"**(用户枚举实锤);②**两步验证(关键!)**:先 `POST /forgot-password/confirm-verification-code {verificationCode}`(第一步确认,200 通过)再 `POST /forgot-password/reset {email,password,passwordConfirmation,verificationCode}`(第二步改密,200 成功)— **必须先 confirm 再 reset,单步 reset 永远 422**;③**验证码 = 邮件链接里的长随机 token**(URL `?dialog=ResetPasswordDialog&code=xxx`,42 字符,**不可爆破 — 别浪费时间去爆数字/短码**);④**临时邮箱方案(任意邮箱验证码接收,全自动化接管)** ⭐:mail.tm API(免费,创建账号+读信+删信全 REST)创建邮箱 → 用它注册 → 请求重置 → 轮询收信 → 正则 `code=([A-Za-z0-9_-]+)` 提取 → confirm → reset — 一条龙 60 秒内完成;⑤**重置请求使旧 code 失效**(每次新 request 覆盖旧 code,10 分钟窗口)— 发请求后必须立即收信+confirm+reset,中间拖几分钟就 422;⑥**重置成功后登录仍 401**(crypto-games 密码存储 bug 实锤:注册密码/重置密码都无法登录 = 认证系统写读字段不一致)— 真实登录路径是 `POST /auth/magic-link {token}`(魔法链接专用 token,与重置 code 不同);⑦配合注册零防护:任意邮箱 → 重置链 = 改密码成功(接管面),但登录被认证 bug 挡住(该 bug 反而成了防御)— **邮箱验证已实测**:注册时自动发确认邮件(主题 "Confirm Email",链接 `/verify-email?code=xxx` 与重置 code 同格式,在最早邮件里),`/user-profile/email/resend-confirmation-code`(60s 冷却)+ `/user-profile/email/confirm {confirmationCode}` 验证成功,但**验证后登录仍 401**(bug 与邮箱验证无关,写读字段不一致实锤)— 唯一剩余路径是 magic-link 专用 token(发送入口未找到);⑧**用户信息泄露面**:`GET /auth/user`(id/username=MD5哈希/email/isEmailVerified/avatar/role)+ `GET /user/sessions?size=N&page=0`(会话 id 自增/ipAddress/country/userAgent — 会话审计泄露 IP);`POST /user/sessions/{id}/revoke` 他人会话 403(权限隔离正常)
- **C-17 任意账号密码重置漏洞(验证码不绑定目标邮箱 — 认证逻辑根级缺陷)** ⭐⭐:`forgot-password/reset` 的 verificationCode **不校验与 email 的绑定关系** — confirm-verification-code 只确认验证码本身有效,reset 时 email 参数可指向任意账号。实测:攻击者邮箱 A 请求重置→收 code→confirm→`reset {email: 目标B, password: 攻击者密码}` → 200 成功, **B 原密码立即失效!** 攻击链 = 用户枚举确认目标存在 → 自己邮箱走完整重置链 → code 重置目标密码(**无需目标邮箱访问!**)。**盈利性评估**:当前被\"密码登录全局失效 bug\"限制(新密码也 401),但:①任意账号密码控制权(可反复重置=永久控制该账号密码状态)②若平台修复密码登录 bug → 立即升级完全接管+余额+15分钟 USDT 提现(0day 储备)③邮件轰炸+社工面(重置请求无频率限制)。**诊断\"密码登录是否全局失效\"标准流程**:浏览器 UI 注册新账号(表单流程)→ 立即用该密码登录;401 = 全局失效(平台实际用 magic-link 登录,密码是遗留字段),200 = 仅 API 注册 bug → 跨账号重置可完全接管。**UI 重置链路坑**:邮件链接 `?dialog=ResetPasswordDialog&code=xxx` 被 Next.js locale 重定向丢参(URL 变 `/en?dialog=...`,code 消失)→ 前端 Confirm 静默无反应 — 别在 UI 上耗时间,直接 API 三步走。验证码 10 分钟窗口 + 每次新 request 使旧 code 失效(快速一条龙:request→收信→confirm→reset 60 秒内)
- **API 客户端 JS chunk 泄露(webpack 端点字典)** ⭐:Next.js 应用里找含 `async login(e){return await (0,o.E)("auth",...)` 模式的 chunk(通常 10-20KB 的 API 客户端类)— **一个 chunk = 全部端点 + body 结构 + 字段名**,比盲扫高效百倍。crypto-games 实测 950-fdc487bcbf293e42.js 泄露:充值地址 `/user/crypto-networks/generate {cryptoNetworkName}`(网络名大写如 TRON,小写/USDT 报 not found)、激活币种 `/user/crypto-currencies/set-as-active {cryptoCurrencyName}`(需先激活才有 cryptoNetworks)、可提资金 `/user/withdrawable-funds/{currency}`、提现 `/user/withdrawal-requests`(无余额时 500 内部异常)、转盘 `/bonuses/by-type/SPINNER/claim`、魔法链接 `/auth/magic-link`、邮箱确认 `/user-profile/email/resend-confirmation-code`(60s 冷却)+ confirm、2FA `/user-profile/totp`、会话 `/user/sessions/{id}/revoke`、头像 `/user-profile/avatar {fileId}`、昵称 `/user-profile/nickname`、推荐码 `/user/affiliate/referral-code`(PUT)
- **Maktub WS 实时游戏协议(完整还原)**:ticket 获取 POST server.maktub.bet/ws/ticket {path:"/ws/crash"} → {ticket:"wst_xxx", expiresInSeconds:30}(**CF 1010 拦 curl 但浏览器 fetch 可过**);连接 wss://server.maktub.bet/ws/crash?ticket=xxx;消息:connected{userId,protocolVersion} / round:phase{phase:waiting|betting|running, countdown, bettingClosesAt} / round:tick{multiplier, elapsed}(50ms 间隔) / 下注发送 bet:place{amount, autoCashout, freeBet} → 服务端 bet:placed{userId, amount, displayName} / bet:rejected;crash betting 窗口 5 秒。完整细节见 references/maktub-engine-and-webhook-pentest.md
- **服务端算法/加密密钥攻坚(硬骨头方法论,挖到底的标准流程)** ⭐:①**JWT HS256 密钥爆破** — 常见词+模式(域名词+n)+1-4位字母组合 27,331 次全不中 + alg:none/篡改 sub 全 401 = 密钥强随机,5 分钟内出结论就停手,别无限爆破;②**游戏 token 结构分析** — v2.{12B 随机}.{16B IV}.{88B 密文}:段1 非时间戳(与 int(time.time()) 无关联)、段2 连续 launch 每次不同(无 IV 重用)、段3 高熵无 ASCII 结构 = AES 类强加密密钥服务端,静态破解不可行;③**RNG 种子爆破** — rotateSeedPair 轮换后 hashedServerSeed = 64hex(SHA-256),对目标哈希爆破(数字 0-10万/时间戳 ±1h/常见词/1-4 位字母全组合)全不中 = serverSeed ≥32 字节强随机 → **fairnessMode:"rng" 但实现是标准 provably fair,结果不可预测(公平性正常,无预测漏洞)** — 这是正面结论,别期待平台作弊漏洞;④webhook secret(whsec_ 前缀)随机不可爆;⑤第三方聚合源站(Slotegrator api.slotegrator.com OVH)SSL EOF/503 = 需特定 TLS 指纹,不可达。**时间管理铁律:加密面验证到"密钥强随机"就该停,把时间留给业务层(注册零防护/重置链/资金链)**
- **Next.js 路由语义**:`307` = 重定向到 /en/ 或登录;`405` = 路径存在但方法错(POST 到 GET-only 路由);`200 HTML size 相近` = SPA fallback;`/api/health` 返回裸 "OK" = 真 API 存活
- **SoftSwiss 白标指纹(freespinz 实战)**:`window.env` 内嵌页面 HTML(搜索 `PLATFORM_` 键)——PLATFORM_SITE(站点码如 FSGL)、PLATFORM_SOFTSWISS_LAUNCHER_SCRIPT(指向 cdn.launcher.a8r.games/connector.js = **SoftSwiss 平台确认**)、PLATFORM_CDN(混淆 CDN 域)、PLATFORM_SPORT_API_URL(体育博彩)、PLATFORM_LIVE_CASINO_DGA_DOMAIN/ID(现场赌场,如 dga.pragmaticplaylive.net + ppcar00000006567)、Google/Facebook OAuth ID;launcher main.js 暴露 `lobby_api_url/game_icons_url/bo_static_url/bo_content_url` 到 window(触发游戏启动后 window.<key> 可读);connector.js 是通用 iframe 启动器(launch_options.game_launcher_url → base64 options);镜像域(freespinz.global/.vip)常见
- 完整侦察笔记见 `references/crypto-casino-pentest.md`

### 11. 管理后台(总后台)面**CF WAF 编码斜杠绕过(重要):** `/administrator/` 403 但 **`/administrator%2f` 返回 200**(URL 编码斜杠绕过 WAF 路径规则),可拿到 Joomla 后台登录页。注意 `/api%2findex.php` 仍被挡(API 路径规则更严,编码不一定通)。绕过套路:对 WAF 拦的路径逐个试 `%2f` 结尾、`%2F`、双编码 `%252f`、`index.php%3foption=...`。

**Joomla 后台:**
- 登录表单:POST `/administrator/index.php`,字段 username/passwd/option=com_login/task=login/return(Base64)/CSRF(32hex,每请求取新值)
- 登录失败统一 303 回登录页;5.x 用户枚举已修复(所有用户名同错误)
- **CF 限流信号**:CSRF 获取失败或请求 000 超时 = 触发限流,停手等恢复或换 IP,别硬刚
- 弱口令字典:赌场特色词(fairgo/pokies/casino/klondike/darkwing)优先于通用词
- 版本确认:`/administrator%2fmanifests%2ffiles%2fjoomla.xml` → `<version>5.4.7</version>`

**WordPress 营销站(从主站 JS/HTML 提取关联域):**
- 主站/收银台 HTML 的 href/src 里挖全部关联域(fairg0games.club / bonusfairgo.com / fairgocasino5.com — 游戏模板/奖金代码/跳转站)
- `GET /wp-json/` 泄露全部路由(360 条 = 插件清单:Wordfence/Elementor Pro/Yoast Premium/Redirection/WP Rocket)
- **Wordfence 行为**:弱口令约 14 次触发 503 封禁;wp-json/wp/v2/users 401;xmlrpc.php 403;统一错误消息(用户枚举防护)
- 用户枚举替代:`/wp-json/wp/v2/posts?_fields=author`(单一作者=无从枚举)
- Elementor 端点 `/wp-json/elementor/v1/*` 未认证全 401(防护正常,别浪费时间)

**RTG 运营后台:通常不在公网暴露。** cashier 域 20+ 管理路径变体全 404;Router.ashx `route=Admin/BackOffice/PlayerAdmin/Reports` 未确认且源站防火墙限流;CDK.js 只有玩家侧功能(AcknowledgeAdminPlayerMessage 是玩家确认管理员消息,非管理端)。管理端在 RTG 内网/VPN —— 识别"管理端不暴露"后及时收手,把精力放玩家侧已打通的链。

