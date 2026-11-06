# 实战回补：catch-all 假阳性 与 **异步导出直链** 这条数据源

> 来源：ugameL/777club 族实战（okadmin/adminapi 目标）。两条都是本 skill 主流程里
> “容易被漏掉或误判”的地方。

## 1. ⚠️ catch-all 判据必须用**内容差分**，不能用长度

实战：[skill:admin-cred-and-auth-bypass] 的 `admin_cred_hunter.py` 在 TP6 站上报了 ...[truncated]