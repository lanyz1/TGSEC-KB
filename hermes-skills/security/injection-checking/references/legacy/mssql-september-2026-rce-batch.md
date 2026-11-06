<!-- archived from /root/.hermes/skills/security/mssql-september-2026-rce-batch/SKILL.md on 2026-10-21 -->

---
name: mssql-september-2026-rce-batch
description: MSSQL September 2026批量RCE：CVE-2026-78456/CVE-2026-67636等9个CVE；堆溢出+整数溢出+提权链；SQL Server 2017-2025全系列；与mssql-stacked-query-takeover互补
---

> 归档卡：原目录 `/root/.hermes/skills/security/mssql-september-2026-rce-batch`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/mssql-september-2026-rce-batch/…')`，不要相对 `references/legacy/` 解析。

# Microsoft SQL Server September 2026 RCE Batch

> **多 CVE 批量** · CVSS 8.0-8.8 · 堆溢出/整数溢出/越界读/提权 · 2026-09-08 发布

## 概述

2026 年 9 月 Patch Tuesday，微软披露了 **9+ 个 SQL Server 漏洞**，其中多个为网络可达的 RCE。攻击者通过认证后发送特制查询/请求触发内存损坏条件，实现代码执行。

覆盖 SQL Server **2017/2019/2022/2025** 全系列。

## CVE 矩阵

| CVE | CVSS | CWE | 类型 | 认证 | 备注 |
|-----|------|-----|------|------|------|
| CVE-2026-78456 | 8.8 | CWE-122 | 堆溢出→RCE | PR:L | 经典堆溢出，认证用户直接打 |
| CVE-2026-67643 | 8.8 | CWE-122 | 堆溢出→RCE | PR:L | 同上，不同触发路径 |
| CVE-2026-67384 | 8.8 | CWE-190 | 整数溢出→堆溢出→RCE | PR:L | 整数运算导致缓冲区分配过小 |
| CVE-2026-68787 | 7.8 | CWE-122 | 堆溢出→RCE | PR:L | — |
| CVE-2026-67636 | 8.0 | CWE-125 | 越界读→RCE | PR:L, AC:H | 高复杂度但可改变作用域(S:C) |
| CVE-2026-68785 | 4.9 | CWE-122 | 堆溢出→DoS/RCE | PR:H | 需高权限 |
| CVE-2026-77486 | 8.8 | CWE-190 | 整数溢出→客户端RCE | **PR:N**, UI:R | **无需认证**，需诱导连接恶意服务器 |
| CVE-2026-67381 | 8.8 | — | 提权 | PR:L | 低权→高权 |
| CVE-2026-77480 | 8.8 | — | 提权 | PR:L | 低权→高权 |

## 影响版本与修复

| SQL Server 版本 | 修复累积更新 | 修复版本号 |
|----------------|-------------|-----------|
| SQL Server 2025 | CU8 | 17.0.4085.5 |
| SQL Server 2025 | GDR | 17.0.1135.8 |
| SQL Server 2022 | CU26 | 16.0.4275.2 |
| SQL Server 2022 | GDR | 16.0.1200.5 |
| SQL Server 2019 | CU32 | 15.0.4490.9 |
| SQL Server 2019 | GDR | 15.0.2190.7 |
| SQL Server 2017 | CU31 | 14.0.3550.4 |
| SQL Server 2017 | GDR | 14.0.2130.4 |

## 攻击面分析

### 路径 A：认证用户→RCE（主路径，CVE-2026-78456 等）

```
认证凭据（sa/低权用户/应用连接串）
    ↓
构造特制 SQL 查询或 TDS 协议请求
    ↓
触发堆溢出/整数溢出
    ↓
内存损坏→代码执行
    ↓
以 SQL Server 服务账户运行（通常 NETWORK SERVICE 或域服务账户）
```

**实战场景**：
- 从 heapdump/配置文件/`.env` 拿到 MSSQL 连接串
- 应用层 SQLi 升级为 RCE（无需 `xp_cmdshell`）
- 低权 SQL 用户直接打内存损坏

### 路径 B：恶意服务器→客户端 RCE（CVE-2026-77486）

```
架设恶意 MSSQL 服务器
    ↓
诱导 DBA/开发者连接（钓鱼/SSRF）
    ↓
恶意响应触发客户端整数溢出
    ↓
SSMS/sqlcmd/应用进程 RCE
```

**实战场景**：
- 社工 DBA 连接恶意 SQL Server
- SSRF→内网恶意 MSSQL 实例→客户端 RCE

## 指纹识别

```bash
# 端口扫描
nmap -sV -p 1433 TARGET --script ms-sql-info

# 版本获取（需认证）
sqlcmd -S TARGET -U sa -P 'PASSWORD' -Q "SELECT @@VERSION"

# Python 快速版本检测
python3 -c "
import pymssql
conn = pymssql.connect(server='TARGET', user='sa', password='PASSWORD')
cursor = conn.cursor()
cursor.execute('SELECT @@VERSION')
print(cursor.fetchone()[0])
"
```

## 验证流程（授权内）

### Step 1：确认版本号
```sql
SELECT @@VERSION;
SELECT SERVERPROPERTY('ProductVersion') AS Version,
       SERVERPROPERTY('ProductLevel') AS Level,
       SERVERPROPERTY('Edition') AS Edition;
```

### Step 2：对照修复版本
```python
#!/usr/bin/env python3
"""MSSQL September 2026 Patch 版本检查"""
FIXED = {
    '17': '17.0.4085.5',   # 2025 CU8
    '16': '16.0.4275.2',   # 2022 CU26
    '15': '15.0.4490.9',   # 2019 CU32
    '14': '14.0.3550.4',   # 2017 CU31
}

import sys
ver = sys.argv[1]  # e.g., "16.0.4100.1"
major = ver.split('.')[0]
if major in FIXED:
    parts_cur = [int(x) for x in ver.split('.')]
    parts_fix = [int(x) for x in FIXED[major].split('.')]
    if parts_cur < parts_fix:
        print(f"[!] VULNERABLE: {ver} < {FIXED[major]}")
    else:
        print(f"[*] PATCHED: {ver} >= {FIXED[major]}")
else:
    print(f"[?] Unknown major version: {major}")
```

### Step 3：与已有 MSSQL 技能联动

已有 `mssql-stacked-query-takeover` 技能覆盖：
- `sa` + 堆叠查询→RCE（`xp_cmdshell`/`sp_oacreate`/CLR）
- 本批次 CVE 补充了**不需要 `xp_cmdshell`** 的内存损坏 RCE 路径

```
SQLi/弱口令登录
    ├── xp_cmdshell（传统路径）→ 被禁用？
    ├── sp_oacreate（备选）→ 被禁用？
    ├── CLR 加载（需 sysadmin）→ 权限不够？
    └── 内存损坏 CVE（本批次）→ 只需低权认证，绕过功能限制
```

## 渗透实战要点

1. **拿到 MSSQL 凭据不要只想着 `xp_cmdshell`**：本批次 CVE 提供了绕过功能禁用的 RCE 路径
2. **版本号是关键**：`SELECT @@VERSION` 一条命令决定能否利用
3. **CVE-2026-77486 可用于钓鱼/SSRF 场景**：架恶意 MSSQL 服务器，无需认证
4. **提权链**：低权用户→CVE-2026-67381/77480 提权→sysadmin→xp_cmdshell 或内存 RCE
5. 打完 MSSQL 后标准动作：`xp_dirtree` 窃 NTLMv2 hash → Relay → 横向

## 与已有技能关系

- `mssql-stacked-query-takeover`：互补关系，传统功能 RCE + 本批次内存损坏 RCE
- `heapdump-credential-hunter`：heapdump 拆出 MSSQL 连接串→用本批次 CVE 打
- `credential-harvest`：配置文件/环境变量泄露 MSSQL 密码→本卡利用

## 修复

安装 2026 年 9 月累积更新或 GDR。
