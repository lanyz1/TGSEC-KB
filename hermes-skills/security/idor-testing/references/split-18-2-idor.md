## 2. IDOR 批量测试要点

- 参数名随接口变:`user_id / uid / id / child_uid / member_uid` — 逐个换目标 uid 看返回变化。
- 优先测资金/绑定/身份返回类(getXxxIncome、getBindXxx、user_account、agent_whether)。
- 采样 uid 全段(1/1000/50000/max-1)证明可遍历 + 数据因人而异 → 影响面实锤写报告。
- 写接口(提现/改资料/绑卡)只验证校验缺失,不真动账;资金操作先征得用户同意。

