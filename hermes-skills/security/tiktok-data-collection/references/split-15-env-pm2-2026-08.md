## ★生产 .env 变更不生效 = pm2 环境快照坑(2026-08 实测,通用)
- **症状**:改 .env 加新变量(如 `USDT_TRC20_ADDRESS=...`)→ `pm2 restart tikflow` 后功能仍不生效(充值仍 503 payment_not_configured)
- **根因**:pm2 进程 env 快照里**已有同名键但值为空**(早前 .env 空值占位时 `pm2 start` 带入快照)→ Next 的 dotenv **不覆盖已有 env 变量** → .env 新值被忽略
- **判别**:`pm2 env <id> | grep 变量名` 看进程快照——值空 = 中招
- **修复**:`export VAR=真实值 && pm2 restart tikflow --update-env`(把 shell 值注入进程 env 覆盖空值),再验证 `pm2 env 0 | grep VAR`
- **规律**:.env 首次出现的键没问题;**从空值/占位改成真实值**的键必踩此坑;payments 类(USDT/PAYPAL/STRIPE)尤其常见(初始全是空占位)
- 顺带:PAY_METHOD 枚举是大写 `"USDT"`(z.enum),测试传 `usdt` 小写会 invalid_input 400——先过 schema 再打 API,别被误导成配置问题

