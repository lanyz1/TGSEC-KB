# 资金盘交叉验证: 用户充值地址 + 充值类型 + 真实用户数(2026 QQLink/KbitPay 实战)

> 用户纠正过的坑: 只看"热钱包空"就下"没真钱"结论是过早的 —— 热钱包是真实的链上钱包, 资金真相在**用户充值地址**和**充值类型拆分**里。

## 1. 用户充值地址(别只看热钱包)

- 表: `web3_addresses`(uid/chain_symbol/address)+ `wallet_users.address`(用户绑定地址, 常见 TRON `T...` / BSC `0x...`)
- 抽查 10-20 个用户地址 → 链上余额(TRON 用 TronGrid, BSC 用 bsc.publicnode.com, 见 umbrella SKILL.md 第 4 步)
- **全 0 = 用户从没在链上充过真钱** → 平台的钱不是用户充进来的
- 反例教训: 热钱包(出金方)是真实链上钱包、有 10000+ 笔交易、近期还有入金 —— 但余额只剩 2 USDT(TRON)/0 USDT(BSC 留 0.97 BNB gas) = 资金被归集/抽离, 不是"没开过"

## 2. 充值类型拆分 = 资金盘铁证

`wallet_recharge_logs` 按 `type` 分组:
- `chain` = 真实链上充值(有 txn_hash, 可链上验证) —— 往往只有几十~几百 USDT、几十笔
- `transfer` / `internalUid` / `redPacket` / `internalEmail` = **内部记账**(无链上 tx, 纯 DB 数字) —— 可达上百万
- 结论: 99%+ 资金是系统凭空创造; 用户"提现地址"存在但地址上从没真钱进去过
- SQL 模板: `SELECT type, COUNT(*), SUM(amount) FROM wallet_recharge_logs WHERE deleted_at IS NULL GROUP BY type`

## 3. 真实用户数审计(揭穿灌水)

- 总用户数 → 按 email 域名分组: `SUBSTRING_INDEX(email,'@',-1)` → 找压测/灌号域名(如 `@stress.test` 占 93%)
- 活跃度交叉验证(全用 DISTINCT uid):
  - `wallet_user_login_log` → 有登录
  - `wallet_account` balance>0 → 有余额
  - `wallet_recharge_logs` → 充过值
  - `wallet_draw` → 提过现
- 真实盘子 = 有登录/有余额的交集, 往往只有 100-300 人(注册号撑场面, 官网宣传人数严重注水)
- 时间线: `created_at` 按月分组 → 某月突增几万 = 灌号铁证; 最后真实出金日之后卡单/无人提现 = 跑路轨迹

## 4. 交付口径

- 结论分三层: ① 控制面打穿(token 伪造/管理台 API) ② 资金面读取(任意用户余额全量) ③ 真实资金可转性(链上 ≈0, 转不走真钱, 只能改 DB 数字)
- 向用户明说"热钱包是真实的, 但资金被归集走了" —— 别因为"转不走"就否定热钱包真实性
