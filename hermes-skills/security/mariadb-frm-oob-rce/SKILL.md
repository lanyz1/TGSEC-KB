---
name: mariadb-frm-oob-rce
description: "Use when 打 MariaDB：.frm 解析 OOB 读→RCE。"
---

# MariaDB `.frm` 解析器 OOB 读 → RCE（CVE-2026-107821 / MDEV-40571）

类型：**OOB Read + RCE**。

## 影响版本（对表即判）

```
MariaDB 13.1 系列（Preview）
MariaDB 13.0 系列（Preview）
MariaDB 12.3.1 – 12.3.2
MariaDB 11.8.1 – 11.8.8
MariaDB 11.4.1 – 11.4.12
MariaDB 10.11.1 – 10.11.18
MariaDB 10.6.1 – 10.6.27
老 MySQL（≤ 5.1）及老 MariaDB Community Server
```

## 机制

`.frm` 文件（表结构定义，MySQL 5.x 遗留格式）的解析器对字段描述区做**长度/偏移未校验读取**，越界字节被当作元数据处理，最终控制流可导到可执行路径。PoC 仓里两个脚本：

```
/exploit/13.1.0/lab_exploit.py            # 实验室版，payload 执行 /tmp/heal_t16.sh
/exploit/10.4.18/na_frm_rce2_exploit.py   # 实战版（渗透测试中用过的）
/exploit/10.4.18/target_reliable.py       # THOST=... USER=... TPWD=... python3 target_reliable.py --fire
```

## 前置（决定能不能打）

1. **要有一个 MariaDB 账号**（任意权限即可，不是 root）——本洞不是预认证。
2. 目标 `secure_file_priv` 为空串或含可写目录。
3. `local_infile=1` 时更好打（可以本地喂 `.frm`）。

判：

```sql
SELECT @@version, @@secure_file_priv, @@local_infile;
SHOW VARIABLES LIKE 'datadir';
```

## 实战链（PoC 作者的完整路径，值得学）

```
Phase1  固件里挖硬编码 API key → 日志 API 打 XSS（HttpOnly 拦 cookie，但 fetch 可以发请求）
        → 找到建账号接口 → 建一个已知口令的管理员
Phase2  Excel 导出功能 SQLi → sqlmap 拿 DBMS 账号 + hash
        hash 无盐 → 字典直接破
Phase3  MDEV-40571 → 反向 shell + 读 SSH 私钥
```

**这条链的价值不在 SQLi，在它的节奏**：先拿任意一个低权面（日志 API），再用它去够数据库，最后才用数据库洞。任何“只暴露了一个日志接口”的嵌入式设备，都该按这个顺序想。

## 坑

- `.frm` 在 MySQL 8.0+ 已被数据字典取代；MariaDB 一直保留到 10.x/11.x，所以这条主要打 MariaDB。
- PoC 自述“针对我自己环境定制”，`target_reliable.py` 需按目标改偏移——别当通用 exploit 用。
- 版本号硬分界：10.11.18 中，10.11.19 才修好。
