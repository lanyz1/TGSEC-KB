# KK 平台 11 家游戏厂商研究档案

Extracted from `core/GameTo*.php` + `config/config.php` (KK/Qzino source package, 2026-07). All credentials are plaintext in config — usable to call vendor APIs directly. Research dimensions per vendor: ①注册/密码派生可预测性 ②转账可给任意账号/金额/幂等/竞态 ③查询任意玩家余额 ④注单/取消/重置 ⑤签名伪造(无时效/密钥复用).

| # | 厂商 | 接入类 | API 地址 | 凭证(config 明文) | 签名机制 | 评估 |
|---|---|---|---|---|---|---|
| 1 | PG | GameToPG.php | api.pg-bo.net(备用 api.pg-bo.me) | operator_token `A-d2336c4a-5c5b-4d22-bb9d-130e3ae3ef3b` + secret_key `<REDACTED>`;备用 `I-fe2e2ca2f67f40a6986e530299dcf789`/`02793f8a4ddb43b9b1a353e5b33b1621`(tools/linshi.php 泄露) | 明文 POST | 🔴 无签名,密钥直调 TransferIn/Out/AllOut/BetList;玩家密码派生 `sha1(base64(ServerName+TGID+secret)+md5(...))` 可预测 |
| 2 | PP | GameToPP.php(+_old) | imone.imaegisapi.com | MerchantCode `OMHtZUqQbWuP6BBXefgi1R44OTnd29t7` + SecretKey(新) | PP_Sign(hash) | 🟡 hash 签名,密钥在手可复刻 |
| 3 | EVO | GameToEVO.php | api.luckylivegames.com / site-api.nimstad99.com / admin.luckylivegames.com | key `whe9yko0hnxoynkw` + token `<REDACTED>`;备用 `vnj91qefsampekuc`/`38880f4559d6913928431dd7300ef5fa` | Basic Auth base64(key:token) | 🟡 明文凭证 |
| 4 | IM | GameToIM.php | imone.imaegisapi.com(与 PP 同系) / imone-report.imaegisapi.com | key `OMHtZUqQbWuP6BBXefgi1R44OTnd29t7` | 明文 POST + Password 派生 `md5(sha1(base64(ServerName+TGID)))` | 🟡 玩家密码可预测;注单有 BetStatus/IsResettled(拒单/重置)字段,对账统计条件 `im_BetStatus=1 AND im_IsResettled=0` |
| 5 | JILI | GameToJILI.php | wb-api-2.huuykk865s.com/api1/ | AgentId `KKOK_Anony_USD` + AgentKey `5a815acbb8f2428582f2a7bfb90e5d53818d4857` | keyG=md5(UTC4Time+AgentId+AgentKey);key=6位rand+md5(参数+keyG)+6位rand | 🟠 keyG 可算,随机前缀可暴力 |
| 6 | FC | GameToFC.php | ap1.fcg1688.net | AgentCode `QIDN` + AgentKey `Pp2se4PMYineD99H` | **AES-ECB 加密参数 + `Sign=md5(明文)`** | 🟠 加密+签名全可复刻 |
| 7 | EEAI | GameToEEAI.php | api.aig1234.com | agent_id `anony` + agent_key `sCmzUWxEfcudh85z` | `md5(agent_key&key=val&...)` 参数拼接 | 🟠 MD5 无时效,可重放/伪造 |
| 8 | JDB | GameToJDB.php | api.datgeni2e47.net/apiRequest.do | parent `kkzonghe` + key `ad3e7de6f801e1b9` + iv `672caa06773748b8` + dc `QQTB` | **AES-128-CBC(key+iv)+base64** | 🟠 密钥+IV 明文,完整复刻 |
| 9 | CQ9 | GameToCQ9.php | apie.cqgame.cc | agent `kkzonghe` + token `eyJhbG...`(JWT 格式) | `Authorization: <token>` | 🔴 JWT 可研究伪造/过期/alg 混淆 |
| 10 | XINGLI | GameToXINGLI.php | bsgh5entry.bestgameasia.com:16667 | appid 104 + appkey `oyu6urogc4absqg50zwp` + appsecret `tysaywpomsatfmulk8yd`;备用 appid 106/appkey `tzxjmitg4ncaxcr6ezne`/appsecret `mm7mgc3deg566hjg6pua` | `md5(key=val&...&appsecret)` | 🟠 MD5 参数签名可复刻;注册返回 token 存 Redis 7 天 |
| 11 | TCG | GameToTCG.php | (config 变量待补) | merchant_code + SHA256Key | `sha256(params+SHA256Key)` + **DES-ECB** 加密 params | 🟡 待评估 |

## 通用要点

- 平台余额在 member.balance;游戏内余额在厂商钱包;转账路径:转入(平台扣款→厂商入账)/转出(厂商扣款→平台入账),均有 Redis 双锁+条件更新+失败补偿(makeuppoints) — 平台侧转账逻辑严谨,直接打厂商 API 才是路径。
- 厂商 API 可直接调用的凭证即"给任意账号充游戏余额"的钥匙:拿到 config(源码泄露/服务器权限)→ TransferIn 任意玩家 → TransferAllOut 转回平台 → 提现。
- 玩家名规范:`ServerName + TGID`(如 `kkzonghe8284251336`),知道 TG ID 即可定位/枚举玩家。
- 注单对账(bet_*.php):DB 唯一键 orders 去重 + Redis 拉取锁;跨月去重只查当月/上月(>2 月延迟注单可重复插入 → 双倍流水,现实难触发)。
- 流水/返水:count.php/rebate.php 均 Redis 锁 + iftj/iffs 标记;代理佣金 fyamount=下级投注额 → 自开小号互刷流水吃佣金(运营套利,非代码洞)。
