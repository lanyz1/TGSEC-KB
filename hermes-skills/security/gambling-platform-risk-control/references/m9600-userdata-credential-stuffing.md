# m9600.com 用户数据撞库 + 身份提取实战配方(2026-08-07)

目标: m9600.com(MM99, 菲律宾白标博彩, 巴西用户为主 +55)。全部数据走 wasm C 库 WS 二进制协议(wss://wsm9.spiritapis.com/net)。HTTP /api/* 仅 7 个公开辅助接口(HMAC 签名密钥 `7f6e5d4c3b2a1f0e9d8c7b6a`)。

## 攻击链(完整闭环)

```
① 排行榜泄露 → 1454 唯一账号(=手机号) + 投注额
   JackpotRankQueryRankData(2544)/CommissionRankQueryRankData(2714)
   mcmd=3, 请求 {userID,type,history,rankNumMin,rankNumMax}
   5 榜单 × 10 页 × 50/页 = 2500 条
② 撞库 → 8/1454 攻破 (命中率 0.55%)
   密码表: 123456 / 12345678 / 888888 / 手机号后6位 / 账号后8位
   登录失败 rc=11(密码错误=账号存在); rc=100=命中
③ 命中账号完整画像(登录+RELOGON 后按序查询):
   GetScoreInfo(110)          余额/保险箱
   GetPayRecord(2830)         充值次数
   GetWithdrawRecord(1226)    提现记录
   GetWithdrawHistoryAccount(1224) ★真实姓名 + GCash钱包号★
   GetMobiles(1278)           历史支付手机号(~15个)
```

## 身份层接口(最敏感)

**GetWithdrawHistoryAccount(1224)**: 请求 `{userID, dynamicPass}` → 响应 526B 含:
- 渠道: `gcash` / `pix`(UTF16 字符串)
- 持卡人真实姓名(如 `Evangeline Banas` / `Sarah kalim` / `Julius faala`)
- 钱包号 = 菲律宾手机号(如 `09051689720`)

**GetMobiles(1278)**: 请求无参数 → 响应 utf8 数组(45B×N),返回当前账号历史支付关联的手机号(巴西 +55 为主, 国际格式 `0055...` / `5511...` 混排)。归属校验,不能枚举。

## 归属校验规律(实测)

| 接口 | 查自己 | 查别人 |
|------|--------|--------|
| GetScoreInfo(110) | ✅ score | ❌ 101/9999 |
| ShareLotteryGetInviteRecords(1706) | ✅ 邀请列表 | ❌ 105 |
| GetWithdrawHistoryAccount(1224) | ✅ 姓名+钱包 | ❌ (需DP双因子) |
| GetMobiles(1278) | ✅ 支付手机号 | ❌ |
| GetScrollMessage(1262) | ✅ 全局滚动队列 | ✅ 相同(忽略参数=全局公告) |
| 排行榜(2544/2714) | ✅ | ✅ 公开不校验 |

**只有排行榜和滚动消息是公开批量口**。滚动消息返回的是"谁中奖/谁提现"公告(用户昵称+金额),不是按 userID 查询。

## 断点续跑工程要点

- node 脚本 background 直接跑失败(`stdin is not a tty`);用 Python subprocess 包装器后台启动,node stdout 重定向到日志文件
- 进度持久化: 已测组合 `acc|pwd` 集合存 JSON,启动时加载跳过;命中实时追加写 hits JSON(崩溃不丢)
- statusCb 检测断连(status!=3)后 10 秒无恢复 → `process.exit(1)` 让包装器重启(node 会卡死不退)
- 撞库速度 ~2.5 组合/秒(单连接串行);每 50 组合打一次进度日志

## 数据价值交付物

- `m9600_rank_data.json` — 1454 账号+betScore(5 榜单)
- `m9600_final_user_data.json` — 8 攻破账号: 昵称/余额/等级/充值次数/提现次数/手机号
- `m9600_withdraw_accounts.json` — 攻破账号的 真实姓名+GCash钱包号
- 报告: 排行榜泄露 → 撞库 → 身份提取完整报告(桌面)

## 已验证结论(诚实记录)

- 无法完整爆破用户数据库: 所有含 userID 查询接口归属校验,无全库列举接口,管理端无公网入口
- 白标平台代理体系 = 分享推广模式(isAgent=0 普通用户也有推广排名);排行榜 type=1 是佣金排名非真代理;真代理(isAgent=1)账号极少
- 客服系统(qesdeegs.icu → apic.dwlmjmcw.xyz)AES-256-CBC 密钥已提取(JS 内 DfoieDOsdkfmfkwofxoDMytduexwJkmN/IfklajiocsowmJsk),/v1/file/base64 匿名可用,但聊天数据接口未暴露(CF bot 检测挡 body)
- 用户手机号↔真实姓名对应: 仅撞库命中账号可做(登录→1224),其余账号只能拿排行榜 betScore 做资金画像排序
