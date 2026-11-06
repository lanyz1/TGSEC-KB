## 2. 环境安装(CentOS7 + PHP 8.2)

```bash
yum install -y epel-release
yum install -y https://rpms.remirepo.net/enterprise/remi-release-7.rpm
yum-config-manager --enable remi-php82
yum install -y httpd mod_ssl php php-cli php-pdo php-sqlite3 php-mbstring php-xml php-json
timedatectl set-timezone Asia/Shanghai
```

- **大坑: CentOS7 自带 SQLite 3.7.17 不支持 UPSERT(需要 3.24+)**。代码里所有 `INSERT ... ON CONFLICT(k) DO UPDATE SET v=excluded.v` 在服务器上抛 `PDOException: near "ON": syntax error`(500, Content-Length 0)。**一律用 `INSERT OR REPLACE INTO`**(全版本兼容)。写 PHP+SQLite 代码时直接只用 OR REPLACE, 别用 UPSERT 语法。
- php.ini: `display_errors=Off` + 追加 `error_log=/var/log/php_errors.log`(chown apache)

