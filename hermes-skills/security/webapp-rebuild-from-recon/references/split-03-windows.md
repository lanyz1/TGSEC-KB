## 环境准备(Windows)

```bash
# PHP Windows 版(windows.php.net 302 到 downloads.php.net)
curl -L -o php.zip "https://downloads.php.net/~windows/releases/php-8.3.33-nts-Win32-vs16-x64.zip"
# php.ini 启用: extension=sqlite3 / pdo_sqlite / mbstring / curl / gd
# 本地跑:
D:/tools/php83/php.exe -S 127.0.0.1:8080 -t <站点目录>
# php -S 直接 serve 静态文件 + 把路由请求交回 index.php
```

