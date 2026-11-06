# m9600 资金接口测试 + 全量 WS 接口批量扫描(实战配方)

> 目标: m9600.com(MM99, CG/HXWS 模板白标博彩)。ws loader/Writer/msgCb 基础见 `wasm-ws-protocol-crack` skill(用户自建,需 `hermes curator adopt` 后才能由 agent 维护);本文件是资金面与批量测绘的配方。

## ⭐ 关键修正: 资金接口通过 CF 全超时,但直连源站后可用!

m9600 早期(CF 未绕过时)测 PlacePayOrder/PlaceWithdrawOrder/GetWithdrawCashLimit 全部超时 → 误判"外部支付网关,无资金逻辑"。**CF 绕过后(hosts 直连源站 IP),提现/限额/配置/抽奖全部有响应!** 测资金逻辑必须先绕 CF 直连源站。

## 资金/充提接口清单(协议号 + 模板 + 直连实测)

| 接口 | mdm,scmd | 模板 | 直连源站实测 |
|------|----------|------|------|
| GetProductInfosNew | 3, 1214 | {userID, dynamicPass, channelID} | ✅ 完整充值产品表(3976B, productID/price/awardValue) |
| GetWithdrawConfig | 3, 1222 | CMD_MB_Common_Query(无参) | ✅ 806B 提现配置(含 "cpf" 渠道+等级限额) |
| GetPayChannel | 3, 2160 | CMD_MB_Common_Query(无参) | ❌ 超时(直连也不响应) |
| GetWithdrawCashLimit | 3, 1782 | CMD_MB_Common_Query(无参) | ✅ 609B 限额(limitMin/limitMax + 等级 dailyCount/dailyFree) |
| GetPayBindParam | 3, 2246 | CMD_MB_Common_Query(无参) | ❌ 超时(CPF 在此,服务器未启用) |
| PlacePayOrder | 3, 2 | CMD_MB_PlaceOrder | ⚠️ 直连仍不稳定(NEED_LOGIN 频繁) |
| **PlaceWithdrawOrder** | 3, 2002 | CMD_MB_PlaceOrder | ✅ **直连有响应(JSON 错误码)!** |
| **ShareLotteryExecuteSbin** | 3, 1708 | {userID, dynamicPass, ip} | ✅ **直连有响应(抽奖!)** |
| LotterySbin | 3, 1520 | {userID, lotteryType(u8), ip} | ✅ 响应(错误码 1204/1207,无实际抽奖) |
| USER_SAVE_SCORE | 3, 161 | {userID, dynamicPass, saveScore(int64), machineID} | ❌ 超时(保险箱未启用) |
| USER_TAKE_SCORE | 3, 162 | {userID, takeScore(int64), password(md5), machineID} | ❌ 超时 |
| CheckInDone | 3, 2144 | {userID, dynamicPass, machineID, ip} | ⚠️ 直连不稳定(NEED_LOGIN) |

**CMD_MB_PlaceOrder 模板**(充值/提现共用):
```
{userID(u32), productID(u32), price(i64!), nickName(utf8 32), machineID(utf8 33), ip(utf8 16), extends(utf8 1024)}
```
extends 通常传 JSON `{"Currency":"BRL","WalletNumber":"...","WalletType":"gcash"}`。响应是**明文 JSON** `{"code":N,"msg":"..."}`。

## 提现三层校验(m9600 实测,测资金漏洞先摸清)

| 错误码 | 含义 | 触发 |
|--------|------|------|
| 1904 | amount is out of global range | 金额超出全局范围(100/1000/5000 太低,10000 才进入下一校验) |
| 127 | error:127 | 余额不足/其他校验(余额10₱提现10000+ 被拒) |
| 2001 | too fast | 频率限制(连续请求需等 3-5 秒) |

**结论: 提现逻辑较安全**(金额/余额/频率三层),未发现超余额提现/竞态可利用点。

## 抽奖(ShareLotteryExecuteSbin 1708) — 每日限次

响应模板: `{errorCode(u32), itemIndex(u8), itemType(u8), reward(i64), scoreExpiredTime}`
- 第 1 次: errorCode=0, reward=100(成功得奖励)
- 第 2-8 次: errorCode=1500(次数用尽)
- **有次数限制,不可重复刷**(1500=次数用尽)

## 订单查询 — 会话绑定校验(越权必被拦,WS 层 IDOR 全堵的最后证据)

| 接口 | mdm,scmd | 模板 | 实测 |
|------|----------|------|------|
| GetPayRecord | 3, 2830 | **{userID(u32), pageSize(u32), pageIndex(u32)}** — 无 dynamicPass! | ⚠️ 直连超时(限流);CF 通道原参数有 dynamicPass 也超时(参数错) |
| QueryOrderStatusBatch | 3, 2240 | {userID(u32), count(u16), onlineID(u32[])} | ✅ 自己 userID → 10B 空结果;传别人 userID → **105 NEED_LOGIN 断连** |

**结论**: QueryOrderStatusBatch 按连接会话绑定 userID,跨用户查询(即使传已攻破账号的真实 userID)直接断连 = **订单越权被拦**。GetPayRecord 传 dynamicPass 会超时(模板没有该字段)。

## 为什么最终没有资金逻辑漏洞(诚实结论)

1. 提现: 三层校验(金额/余额/频率)— 安全
2. 抽奖: 每日限次(1500)— 安全
3. 充值: 直连不稳定 + 需真实 productID(GetProductInfos 才能拿),价格篡改(真实价→1元/0元/负数)未测出
4. 保险箱(SAVE/TAKE_SCORE): 未启用,无负数金额测试面
5. **资金逻辑校验完善是这类平台常态;数据泄露(GetMobiles 全局手机号库/排行榜/撞库身份)才是实际可拿的最大价值**

## 批量扫描工程要点(334 协议号全测)

### 接口清单提取
```python
# main.js 里抓 [u.SUB_XXX]:[{...}] 模板, 筛含 userID 字段 = 数据查询接口
re.findall(r'\[u\.(SUB_[A-Za-z0-9_]+)\]:\[\{', code)
```
m9600: 334 协议号,98 个含 userID 查询接口(24 系统扫 + 67 批量扫 + 8 重测)。

### 致命坑
1. **LOGON_EXIT(11) 绝不放批量序列** — 登出会话,后续全部 105 / alloc failed
2. **LOGON_SUCCESS(100) 完整解码模板** — 简化模板错位(userID=2/nick 乱码):
   ```
   faceID(2B) gender(1B) customID(4B) userID(4B) gameID(4B) experience(4B)
   loveLiness(8B) accounts(32×2B) nickName(32×2B) dynamicPass(33×2B)
   userScore(8B) tCCoin(8B) userInsure(8B) tCCoinInsure(8B) insureEnabled(1B)
   isAgent(1B) moorMachine(1B) roomCard(8B) lockServerID(4B) kindID(4B)
   agentID(4B) userFlag(4B)
   ```
3. **响应 scmd ≠ 请求 scmd**: 常见请求+1(1222→1223, 2544→2545, 1702→1703);也可能是 110(ScoreInfo 推送)或 105(需登录)
4. **每接口 3-4s 超时兜底**自动跳过,否则单接口超时卡死全批
5. **断连(1006)重连**: statusCb(status≠3) → 重置 phase → 重新 startWebsocket → LOGON → RELOGON 再继续
6. **限流**: 连续大量请求触发 1006,冷却 30s 再跑;node 在 Hermes background 模式会 `stdin is not a tty`,用 Python subprocess 包装器
7. **110 是登录后服务器主动推送**(余额),别当请求响应处理

### 有响应但无用户数据的接口(避免重复测)
BaseEnsureTakeReward(2105)/CheckInDone(2145)/TakeBindMobileReward(1287)/GetProductTypeActiveState(1213)/ShareLotteryExecuteSbin(1709)/ShareLotteryTakeReward(1711)/ShareLotteryTakeSpreadRebate(1715)/MAIL_Detail(2205) — 多为操作结果码。

### 服务器端未启用的接口(超时,别硬试)
GetPayBindParam(2246)/GetLotteryPlatformRecordNewest(1514)/GetTask_Config(2642)/Task_Buff_Status(2640)/GetActivityConfig(1300)/GetGiftCode(2630) + 部分 Take/Reward/Done 操作类。

## 最终交付结论(诚实)

m9600 无高价值漏洞: 无 RCE / 无 SQLi / 无资金逻辑(提现三层校验+抽奖限次)/ 无管理端。**最高价值 = 数据泄露: GetMobiles(1278) 全局手机号库 9248 个巴西手机号(批量注册+6并发提取)、排行榜 1454 账号+投注额、撞库 8 账号、4 真实姓名+GCash、客服客户 API。** 资金侧无法套利,数据侧成果重大。
