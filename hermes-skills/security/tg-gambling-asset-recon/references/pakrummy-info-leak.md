# YonoGames 矩阵信息泄露漏洞（bdrummy/pakrummy 共享后端）

## 漏洞：分享现金接口未授权泄露玩家手机号

### 前置：登录签名（已突破）
WebSocket 登录消息必须附加 3 个字段，否则 spcode 209 param_nil：
- `c_ts` = 毫秒时间戳
- `x` = md5(c_ts + salt)，salt 硬编码在 `getSalt()`（bdrummy/pakrummy 同值）
- `c_idx` = 客户端消息索引（从 0 递增）
- `deviceid` = 真实随机格式 Android ID（顺序值 `a1b2c3d4e5f6a7b8` 会触发 218 Unsupported device）
- `bwss=1`（loginServerAddress 无冒号时 isUserWSS() 返回 1）
- bdrummy 包名 `com.bdl.rummy.games` / av `1.0.2`，appId=17，cAppid=501
- pakrummy 包名 `com.rummy.pak.games` / av `1.1.4`，appId=17，cAppid=2

### 消息格式
- 请求：`[2B len][2B CRC-16 poly 0x70B1 init 0xFFFF 算前 min(len,128)][4B ts][msgpack]`
- 响应：ASCII 8 字节头（如 `00000000`）+ msgpack body
- bdrummy：`wss://lo.fcwjosk830sj.com/ws`（无 geo-block 直连）→ 协议1 返回 `{net,uid,subid,token}` → 协议2 连 `wss://{net}/ws`（LOGIN_USERID=2）
- pakrummy：`wss://lo.cweubis96s.com/ws`（CloudFront geo-block 仅放行巴基斯坦/香港）

### 泄露点（游客账号零鉴权可调）
登录后协议2连接上直接发：
1. `{c:535}` REQ_SHARE_CASH_INFO → 返回 `phones`（20 个真实玩家手机号，+880 孟加拉 10 位）+ `bonus/maxBonus`（活动奖金）
2. `{c:538}` 分享现金日志 → 返回 `phones`（另 20 个不同手机号）
- 合计 40 个真实玩家手机号，每次新游客登录都能重新拉取，phones 随活动轮换可枚举更多
- 这些手机号持有者均参与「分享现金」活动（有现金 bonus 待提现），可直接用于社工/钓鱼/撞库

### 其他信息泄露
- `{c:514}` 服务信息 → 泄露客服 URL、邮箱 <EMAIL-REDACTED>、官网 bdrummy.bet、全套社交账号（Telegram 频道/FB/IG/YouTube/WhatsApp）

### 资金面卡点（客观限制，非未尽力）
- 提现 `{c:132}` / 提现银行支持 `{c:136}` → spcode 551 invalid_phone（需绑定手机，服务器端校验）
- 代理 `{c:135}` → 同样 551
- 排行榜 `{c:243}` → datalist 空（bdrummy 是新盘，但已有真实玩家在玩：游戏广播可见玩家 kokuwn uid=1504643 赢 3243.6 金币）
- 银行存取 `{c:100-103}`、红包 `{c:7100/7101}`、转账 `{c:142}` → MsgId 需在热更新子模块（remote-asset/project.manifest）里进一步逆向

## 下一步方向
- 热更新子模块：`loadFile("version")` → `remoteVersionUrl` → 下载 remote-asset 子游戏 manifest，挖银行/转账/红包真实 MsgId 与参数
- pakrummy 成熟盘排行榜：需巴基斯坦/香港出口（免费代理多已挂，geo-block 白名单极窄，越南/印尼/泰国/印度/新加坡全部 403）
- 邀请码绑定：登录 code 字段不绑定（invit_uid 恒 0），BIND_INVITE_CODE 真实 MsgId 待逆向
