## 提现链路（USDT 收款地址,2026-08 完善）
- 流程：用户填金额 + **USDT TRC20 收款地址** → 冻结余额(REVIEWING) → 管理员在 `admin/withdrawals` 看到地址**人工打款** → approve(置 COMPLETED)/reject(退回余额+理由,note 存理由)
- **★最低提现 100 USDT(2026-08 用户要求)双层校验**:后端 `requestWithdraw` 内 `amount < 100 → WalletError("min_amount")`(service 层铁律)+ route schema `z.number().min(100).max(1_000_000)`(入参层);前端弹窗 `min={100}` + submit 校验 `amount < 100 → setError(withdrawMinError)`(本地即时提示,不发请求);错误映射 route 里 `min_amount → 400 min_amount`;文案键 `withdrawMinError`(\"最低提现 100 USDT\")+ label 显示 `最低 100 · ≤ 可用`
- schema：`WalletTransaction.payToAddress String?`(WITHDRAW 类型必填；admin.ts listPendingWithdraws 返回 address 字段)
- **TRC20 地址格式校验**：`/^T[1-9A-HJ-NP-Za-km-z]{25,42}$/`（base58 字符集，**不含 0/O/I/l**）；宽松校验防误填，前端同正则
- ★测试/夹具地址必须用合法 base58 字符：如 `TAbcdefghijkmnopqrstuvwxyz23456789`——`TTest1234567890...` 含 `0` 会 invalid_address 拒掉（正则校验对测试数据同样生效，别用随手编的串）
- 前端提现弹窗：金额 + 地址输入(必填,font-mono) + 时效说明"审核通过后 1-3 个工作日打款"；成功视图显示进度提示
- 管理端列表加"收款地址"列（`font-mono break-all` + title 完整值），管理员照地址打款——地址是人工打款流程的必要信息
- API：`POST /api/wallet/withdraw {amount, address}`；错误映射 invalid_address / insufficient_balance(400)
- `requestWithdraw(userId, amount, payToAddress)` 改为 3 参数——**改签名必须同步改测试**（tests/admin/admin.test.ts、tests/wallet/ledger.test.ts 里所有调用点，否则 typecheck 红）
- **人工加余额(客服/运营操作,2026-08 实测)**:生产 `cd /srv/tikflow && node -e "..."` 用 PrismaClient 直接 `user.update({where:{email}, data:{balance:{increment:N}}})`(balance 在 User 表,无独立 Wallet 表);先 `findUnique` 确认用户存在并打印 before→after;临时脚本用完删除;注意生产 node 读 .env 用 prisma 直连(不走 Next)

