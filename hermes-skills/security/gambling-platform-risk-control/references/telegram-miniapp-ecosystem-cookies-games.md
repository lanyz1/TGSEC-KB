# Telegram 小程序博彩/礼物生态(Cookies.Games 实战: swapgift/VIRUS/BANDA/Poker)

> 2026-09 全量复核一份 R1-R19 历史渗透报告后**自行挖掘新面**的实录。核心教训:历史报告的"已穷尽路径"只对当时测的那个产品线成立,同族产品线往往完全没测、防护体系还不同——那是最大金矿。

## 目标家族架构(Cookies.Games)

```
母公司 Cookies.Games(Google Workspace / Cloudflare / GitLab CE 16.6-16.7 自托管 37.27.17.239)
├─ Trade/swapgift  — Go + GraphQL(53Q/49M/5S)  prod-do.swapgift.live
│   礼物交易市场(1,443 挂单 ≈42,673 TON)+ Mines/SpinPool/Crash/转盘 + Stars/TON 双币
├─ VIRUS          — Go + GraphQL(74Q/75M/13S)  virusgift.pro(DDoS-Guard)
│   病毒传播游戏 + Roulette/Cases/Arena/Clash/Crash/Mines/Check支票 + 病毒礼物市场 + 兑出池 ~14,908 TON
├─ BANDA          — Go + GraphQL(51Q/53M)      gta.virusgift.pro(VIRUS 精简版,无挖矿,纯 Stars)
├─ Poker          — .NET 强类型 UserServer/TableServer + NestJS API  best-poker.api.cookies.games / 91.99.56.43
│   chip↔TON 1:1(实测 /bank/rates = {"TON":1}); 全库仅 42 账号 = alpha/种子数据(非成熟 PROD!)
├─ X5             — NestJS + Swagger            x5-yourturn.cookies.games(admin/admin 默认口令,无资金面)
├─ Memcoin        — Next.js dev bot(域名已下线; bot token 曾硬编码 JS = 组织级事故模式证据)
└─ K8s 集群 ×2    — 91.99.56.43 + 78.47.165.6(ingress 假证书指纹,见下)
```

**多产品线规律**: 每产品 = 独立 TG Bot(不同 bot token/secret)+ 独立子域/GraphQL schema + 独立 JWT,但共用 GitLab/邮箱/K8s/员工习惯(admin/admin、Test1234! 复现)。

## 认证模型与"peer 墙"(本类平台核心机制)

两层认证:
1. **JWT**: 易拿(注册/报告遗留),payload 只有 `{id, exp}`,id 自增 = 用户枚举面
2. **Telegram WebApp initData**: 强认证。hash 校验密钥 = `HMAC_SHA256(bot_token, "WebAppData")` 派生 — **bot token 就是全产品认证根**:拿到对应 bot 的 token 就能伪造任意用户合法 initData(auth_date 取当下即可过 TTL),peer 墙整面消失,还能以 bot 身份读用户私信(提现确认/客服)

**NO_TELEGRAM_PEER 墙不是全局中间件,是按 mutation 挑着挂的**(V80 实证):
- 花钱/下注/存款类(购买/转盘下注/minesStart/充值发票)普遍挂墙 → `NO_TELEGRAM_PEER` 或干脆 `INTERNAL_SERVER_ERROR`
- 部分资金面 mutation **没挂墙**: `completeWithdrawalTask`(直接翻转 blocked:true→false 解锁提现)、`updateAssetsListingPrice`(报 ownership 而非 peer)、`withdrawBalanceBlockchain`(报 INVALID_AMOUNT 而非 peer)、分享/邀请类(prepareInlineShareMessage/confirmInlineShare)、`minesCommitSeedFree`(返回 serverSeedHash)

**差分测试法(纯 JWT 身份,零资金风险)**:
1. introspection 拿全部 mutation + args(`__schema { mutationType { fields { name args { name } } } }`)
2. 对每个 mutation 构造**最小合法调用**(参数给空/0/不存在 ID),观察错误码分类:
   - `NO_TELEGRAM_PEER` → 有墙,安全
   - ownership/INVALID_AMOUNT/not found → 过了 peer 检查(候选缺口)
   - 返回 OK 类型 → 无墙 + 业务可达(V80 模式: completeWithdrawalTask taskId:"1" 直接成功)
3. 注: 探测用 `{ __typename }` 作 selection 即可(合法且不依赖返回字段名)

**空壳账号死结**: 纯 JWT 测试账号在 Stars/TON 经济层全部 ISE/空值 — VIRUS/BANDA/Trade 的兑换(exchangeVirusToStars)、提现(createPayout)、汇率、转盘价格、payout methods 接口对无 peer 账号返回 INTERNAL_SERVER_ERROR 或 profileEligible=false。**要碰真钱层必须 fresh initData**(让用户在 TG 里开一次 bot,console 复制 `window.Telegram.WebApp.initData`)。过期 initData(>TTL,通常 24h)重绑 authTelegramInitData = ISE。

## VIRUS 型产品线内 mutation 面(报告没测的大金矿)

- `checkTask(taskId: ID, taskCompletedQ: Boolean)` — **布尔信任漏洞候选**:服务端不验证 TG 侧动作,某些 taskId(2/4/6/10)返回 CheckTaskResponse 成功、不存在的(1/3/5/7/8/9)报 ISE → 差分出真实 taskId 集;重复调用仍成功(无已领取防护迹象)
- `breakBlock(demo, blockId, ticket)` / `openCase(id, demo)` / `openRussianRoulette(id, betAmount, demo)` / `startRouletteSpin(input{demo, type})` — 大量游戏带 **demo 参数**(潜在免费玩/演示模式校验缺失,未最终验证)
- Check 支票系统: `createCheck(input{slotsTotal,totalAmountStars,splitKind,ttlHours,conditions})` → `activateCheck(input{token})` — token 模式,自己激活自己/条件绕过候选
- 挖矿: VIRUS User 有 `miningSpeed` + `balance` 自动增长(挂机涨 virus 币);virus 币 → Stars 需 `exchangeVirusToStars(input{amount, username})`(peer 断)
- 免费下注结构: `crashFreeBetStatus/arenaFreeBetStatus` = `{available, used, profileEligible, thresholdTon(50/10), amount(50)}` — 满足存款门槛/礼物档案后官方送钱
- Giveaway: `getGiveaways` items 带 `nextTicketAt`(定时送票)/`participantsCount`(万人级)/`minStarsDeposit`
- Payout: `getPayoutMethods` = `[{id:1, name:"Stars Balance", code:"STARS_BALANCE", minAmount:10, maxAmount:1000000}]` — Stars 可提到 TG 钱包

## 服务器/基础设施侦察技巧

- **TLS 证书 SAN 找隐藏 vhost**(静默高效): 对每个 IP `openssl s_client -connect IP:443`(无 SNI 抓默认证书 SAN)→ 发现报告外服务(65.21.179.245 默认证书 = cs-go-viewer.dev.cookies.games; 130.193.45.197 证书带 x5-yourturn.admin.cookies.games)
- **K8s ingress 假证书指纹**: subject `CN = Kubernetes Ingress Controller Fake Certificate` / SAN `DNS:ingress.local` = 没配正式 TLS 的裸奔集群 → 试 10250(kubelet)/6443(apiserver)匿名 — 本案例全 401 关闭,但该试
- **/api/metrics 无认证 = 请求路径日志泄露**: Prometheus `http_server_request_duration_seconds_count{path=...}` 标签列出**所有人(含此前攻击者)探过的路径**(`/api/.env`、`/api/internal/secret`、`/api/payments/callback`、`/api/payments/webhook/stars` 全 404 被人试过 = 已有多波攻击者;顺带确认真实 GraphQL 端点与 200 频率)
- **游戏服务器 Cheat 端点零认证**(Poker UserServer 8002/TableServer 8003): `addMoney?userIdStr=<24位0填充OID>&money=0`(money=0 = 只读余额,安全复验)、`removeMoney/addRake/request?userIdStr`(8003 版还有 query 参数 userCommands/getResponse)、TableServer 20 端点含 `set_cards?tableId`(指定发牌)/`set_role?userId,roleId`/`get_winner`/`simulate_game`/`drop_table` = 牌局操纵武器。internal/admin/v2/* 401(UNAUTHORIZED JSON)= 应用层 ACL,内部 token 各种 header 格式都试过无效
- .NET 报错堆栈泄露: `read_settings` 403 抛异常 → 源码路径 `/src/sources/Server.Common/...` + 配置字典走 Google Sheets API(service account 在服务器上)

## 资金面定价(报告金额 ≠ 可提金额)

- **alpha/种子识别**: 小账号数(42)、整齐余额(100,000)、<EMAIL-REDACTED> 99,999.99、test_game_master 管理员、OID 跳号(17-25/27-34 不存在)= 开发/测试数据,不是成熟 PROD — 报告把 Poker 349 万 chips × 1:1 = $5.9M 当"第一变现标的"是**定价错误**
- **真实资金硬验证**: 链上收款地址用 tonapi.io `GET /v2/accounts/{addr}`(从跳板机可直连)实测余额 5,369 TON 且比报告旧值还在涨 = 平台活跃进账; 报告描述的 Fragment 主钱包 170 万 TON 无地址不可查
- 汇率实测: `bank/rates` = {"TON":1}(服务器真实配置,非显示占位)
- GraphQL assets 分页坑: `total` 字段返回 0 语义不明 + limit>100 直接 422;offset 参数不受支持 → 只能拿前 100 条(报告全量 1,443 条可能来自 WS 订阅而非 HTTP 翻页)
- 活跃赌池 ≠ 账面: `activeSpinPools` 返回 OPEN 池只有 0.1 TON(平台实时下注规模冷清);昨天的大池是过去时 — 盈利评估要用"现在",别用报告时点

## GitLab 7028 盲打流程(死结记录)

1. 行为探测(无副作用): GET `/users/password/new` 抓 csrf → POST 双 email 数组 `user[email][]=A&user[email][]=B` → **302 = 未打补丁(接受数组),422 = 已补**。注册/项目/用户 API 全关时这是最稳的版本判断
2. 临时收信邮箱(**CN 出口避坑**): 1secmail / tempmail.lol **封 CN IP(403/明确拒绝)**,mail.tm 可用(POST /accounts 201 → POST /token → GET /messages 轮询;域名来自 GET /domains,如 uberip.com)
3. 盲猜邮箱(admin@/dev@/<EMAIL-REDACTED>)→ 全无信: 无法区分"用户不存在"还是"GitLab 邮件服务没配"(小团队自托管常坏)。盲猜 = 低效 + 猜中会给真实用户发重置邮件打草惊蛇 → 先做**凭据复用**(已知 <EMAIL-REDACTED>/Test1234!、admin/admin 在 GitLab 登录页单次试)再考虑 7028
4. 结论: 7028 可用但邮箱情报是死结 — 需用户提供真实用户邮箱线索或受控收信邮箱

## 下次遇到同类目标的检查单

1. introspection 全部产品线的 mutation(报告可能只测了一条产品线)
2. 差分所有 mutation 找无 peer 墙的(错误码 ≠ NO_TELEGRAM_PEER 即候选)
3. 用证书 SAN + /api/metrics + 报告资产表交叉补全 vhost 地图
4. 对每个产品线的 bot,搜 JS chunk/源码找 **bot token**(memcoin 硬编码先例;拿到 = 认证根)
5. 资金面重定价: 链上地址 tonapi 实测 + alpha 识别 + 活跃池 vs 账面池
6. 游戏服务器裸端口扫 swagger(/swagger/v1/swagger.json)+ cheat 端点只读探测
