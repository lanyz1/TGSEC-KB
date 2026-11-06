# 链上资金流追踪配方（TRON / TRC20 USDT）

## 接口（免 key、无需认证）
- 账户：`GET https://apilist.tronscanapi.com/api/account?address=<T...>` → `balance`(sun)、`totalTransactionCount`、`date_created`、`addressTag`/`publicTag`（有标签=已知实体，直接采信）
- 代币余额：`GET .../api/account/tokens?address=<T...>`
- **交易反查**：`GET .../api/transaction-info?hash=<64hex>` → 返回 `hash` 字段即证实是 txid（用于区分私钥，见 SKILL 铁律 2）
- 转账明细：`GET .../api/token_trc20/transfers?limit=50&start=<n>&relatedAddress=<T...>&sort=-timestamp`
- TRC20 USDT 合约：`TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`

请求头带个普通 UA 即可；加 `time.sleep(0.3~0.5)` 避免被限速。

## 归集链重建
1. 对候选地址拉出款明细，**只保留 `from_address == 目标` 且 `contract_address == USDT`** 的记录（不筛会把转入也算进去）。
2. 按 `to_address` 聚合求和，取 TOP N —— 单笔占绝对多数的那个 to 就是下一层归集钱包。
3. 递归追下一层，直到目的地数量暴增（进入散播/提现层）或余额清空。
4. **判据：余额只剩激活底额 + 交易数很多 = 资金已全部转走**，该地址是纯中转，不是资金池。（TRON 账户激活底额常见 8.57 USDT / 0.5 TRX 这种零头，别把它当余额。）

## 交易所/服务商落点识别（启发式，需人工确认）
- **多个互不相关的归集钱包都往同一地址打款**，尤其每个都带一笔小额"测活" → 交易所充值地址的典型特征。
- `addressTag`/`publicTag` 有值 = 已标注实体，直接采信；`CreatedByContract` 类标记可区分合约生成地址。

## 出款批次 / 到账时序推断
平台侧通常只有 `create_time`(提交) 与 `update_time`(审核)，**没有链上到账时间字段**。可做的：
- 把全量订单 `update_time` 按小时直方图化 → 看是否集中在固定时段（= 人工/批量打款批次）。
- `update_time - create_time` = **审核时长**（口径必须写明是审核，不是到账）。
- 统计**中位数与含大额的均值两个数都给**，并说明小额/大额分段差异，别只给一个平均数。
- 样本量必须说清：某通道历史单量为 0 或 1 时"平均时长"无样本可算 —— 直接说明，不要拿自测单冒充平台速度。

## 报告诚实性
- 归集层级与金额用脚本聚合后输出，附脚本与原始回执文件路径。
- 启发式识别（交易所落点、批次规律）标注为推断并给依据。
- 只覆盖了部分地址/时间窗就明说覆盖范围，不要把样本说成全量。
