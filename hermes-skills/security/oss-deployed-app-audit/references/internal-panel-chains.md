# 内部运营面板链 → 数据仓库全量（2026-10 实测）

适用信号：目标有内部运营工具（CRM/后台/BI/备份/知识库）暴露在子域；或其开发/运营凭据流向 SaaS 文档工具。与 `references/metabase.md` 连用。

**链样板：弱口令内部后台 → 备份子系统 → 配置表明文密钥 → 文档库凭据档案 → BI 工具 → 数据仓库全量导出。**

## 1) 内部后台弱口令特征

- 管理员口令常是公司/品牌名+123 一类；**无锁定/无验证码/无速率限制很常见**（实测 1600+ 发零阻断）。
- 登录成功响应常直接给 JWT（role: admin）——拿 token 后测绘 API：SPA bundle 里 grep `"/api/` 路由表最全；接口客户端方法名（getUsers/updateUser/deleteUser）能从 bundle 直接读出。
- 后台路径特征：`/admin/`、`/api/auth/login`、`/api/backup/*`。

## 2) 备份子系统 = 最快全库出口

- SPA bundle 里 grep `backup` 找路由：`/backup/list` 列文件、`/backup/download/{filename}` 直下——**权限分级常缺失**（任意 admin 即可下全部历史备份）。
- 备份常是每日定时全量（SQLite .db / mysqldump）——一个请求 = 整个数据库（实测 299MB/日）。
- 只读优先：别触发 `/backup/create`（占盘/惊动）。

## 3) 配置/设置表 = 明文密钥金矿

- 后台 settings/config 表（key-value）常**明文**存：Slack bot token + webhook、ClickUp、Resend/SMTP、OpenAI key 等。
- 拿到即**只读验活**（auth.test / 用户信息 API），并全量导出该表（本地 JSON）。
- 顺带看表里有没有前人的探测痕迹（`__proto__.shell`、`outputFunctionName` 等污染探测常量）——说明已被测过但未修，报告里可引用。

## 4) 文档/知识库 = 凭据档案

- 用上一步 token 全量拉 SaaS 文档（ClickUp docs API、Notion、Confluence）后，**grep `password|pass:|vpn|ssh|creds|token|admin`**——团队 wiki 的 “Accounts/账号” 页经常是**全生态明文账密总表**（实测一次拿到 20+ 系统：预发环境 Basic/Django、供应商后台、BI、客服、Google、测试号）。
- 每日/每周会议纪要文档是组织情报（人员、分工、在做的项目）；“Important links” 页 = 全部后台入口清单。
- 收尾时把文档中引用的子域逐个 DNS/端口探——经常还有没列进去的。

## 5) BI 工具 → 数据仓库

- BI 凭据（Metabase 等）到手后的全量取数：见 `references/metabase.md`（自建卡 + CSV 导出全表，1M 行硬顶按切片覆盖）。
- 目标：从应用层数据升级到**仓库全量**（玩家/资金/合规全口径），报告数字用聚合口径（count/distinct）。

## 6) 慢磨纪律（触及生产后台时）

- 带 OTP 二因子的后台：不硬碰。
- 无锁定机制的后台也要**慢磨**（每 25 分钟 1 发、自建 watchdog）“永不触发锁定”——Django-axes 类全局锁一旦触发会锁全员（生产影响）。
- 用户新增/删改属于破坏性操作：能读到就够，**不要改人家生产账号**；确需验证写入能力时用最小副作用动作并记录。

## 7) 清理

- 收工时删除自建对象（如 BI 自建卡 DELETE /api/card/{id}），保持“未修改业务数据”口径；报告影响部分把“批量导出/下载”作为证据写明。
