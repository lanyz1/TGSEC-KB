# 后台自助域名绑定 — sudoers 白名单模式(2026-08 xeelee.top 实战)

用户需求: 后台左侧菜单加「域名绑定」, 输入新域名一键绑定 + HTTPS 证书 + 切换主域名, 不碰服务器。
实现模式: PHP(apache 用户) exec → `sudo -n` 白名单 root 命令。

## 1. sudoers 安装(服务器 root 一次性)

```bash
cat > /tmp/zengda-sudoers <<'EOF'
# zengda 域名绑定白名单 (由后台「域名绑定」使用)
Defaults:apache !requiretty
apache ALL=(root) NOPASSWD: /bin/cp /tmp/zengda_http.conf /etc/httpd/conf.d/zengda.conf, /bin/cp /tmp/zengda_https.conf /etc/httpd/conf.d/zengda-le-ssl.conf, /usr/bin/systemctl reload httpd, /bin/systemctl reload httpd, /usr/bin/certbot *
EOF
visudo -c -f /tmp/zengda-sudoers        # 语法校验, 失败别装!
install -m 440 -o root -g root /tmp/zengda-sudoers /etc/sudoers.d/zengda
# shell 层验证:
sudo -u apache sudo -n /bin/systemctl reload httpd; echo $?   # 0
sudo -u apache sudo -n /usr/bin/certbot --version             # certbot 1.11.0
sudo -u apache touch /tmp/zengda_http.conf; echo $?           # 0
```

要点:
- **`Defaults:apache !requiretty` 必须**: apache 无 TTY, 默认 requiretty 会导致 sudo 失败
- 白名单只给 cp 两个 vhost 文件 + reload + certbot —— apache 无法执行其他 root 操作
- CentOS 7 systemctl 实际路径 /usr/bin/systemctl(/bin 是链接, 两个都写防路径歧义)
- 确认 PHP `disable_functions` 不含 exec(生产 php.ini 若禁用需放开)

## 2. vhost 双文件结构(现状基线)

```
/etc/httpd/conf.d/zengda.conf       # 80 段: ServerName + ServerAlias + https 跳转
/etc/httpd/conf.d/zengda-le-ssl.conf # 443 段: 证书固定指向 live/xeelee.top/
```

80 段跳转(通用 SERVER_NAME, 不枚举域名; **必须排除 acme 验证路径**):
```
RewriteEngine on
RewriteCond %{REQUEST_URI} !^/\.well-known/acme-challenge/
RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
```

443 段证书行:
```
Include /etc/letsencrypt/options-ssl-apache.conf
SSLCertificateFile /etc/letsencrypt/live/<cert-name>/cert.pem
SSLCertificateKeyFile /etc/letsencrypt/live/<cert-name>/privkey.pem
SSLCertificateChainFile /etc/letsencrypt/live/<cert-name>/chain.pem
```

## 3. PHP 生成 + 安装 + 签发(核心代码模式)

```php
// 生成(域名已严格校验, 拼接安全)
$http  = domain_gen_http($serverName, $aliases);   // 80 段
$https = domain_gen_https($serverName, $aliases);  // 443 段, 证书固定主证书
file_put_contents('/tmp/zengda_http.conf', $http);
file_put_contents('/tmp/zengda_https.conf', $https);

// 安装
exec('sudo -n /bin/cp /tmp/zengda_http.conf /etc/httpd/conf.d/zengda.conf 2>&1', $o, $rc);
exec('sudo -n /bin/systemctl reload httpd 2>&1', $o, $rc);

// 签发/扩展(单证书 SAN 全域名)
$cmd = 'sudo -n /usr/bin/certbot --webroot -w /var/www/zengda -d a.com -d www.a.com'
     . ' --cert-name xeelee.top --expand --non-interactive --agree-tos --email <EMAIL-REDACTED>';
exec($cmd . ' 2>&1', $o, $rc);

// 切换主域名(config.php 正则替换)
$src = preg_replace("/('site_domain'\s*=>\s*)'[^']*'/", "$1'" . $d . "'", $src, 1);
```

## 4. DNS 预检(防白签)

```php
function domain_dns_ok(string $d): bool {
    $ip = gethostbyname($d);
    return $ip !== $d && $ip === SERVER_IP;   // SERVER_IP = 公网 IP 常量
}
```
未解析 → 拒绝并提示「请先在域名商解析 A 记录」(实测返回友好 JSON, 不触发 certbot)。

## 5. Web 层 exec 链路验证(部署后必做)

临时探针上传 → curl 访问 → 删除:
```php
<?php
exec('sudo -n /bin/systemctl reload httpd 2>&1', $out, $rc); echo "reload rc=$rc\n";
exec('sudo -n /usr/bin/certbot --version 2>&1', $out2, $rc2); echo "certbot rc=$rc2\n";
```
预期 rc=0; 测完 `rm -f /var/www/zengda/probe_exec.php`。

## 6. 后台页面要素

- 统计卡: 绑定域名数 / 当前主域名 / 证书到期(openssl_x509_parse cert.pem 的 validTo_time_t)/ 证书 SAN
- 绑定列表: 域名 + 主/别名徽章 + 「设为主域名」「移除」; 移除保护(主域名不可移除, 先切换)
- 添加表单: 域名输入 + 步骤说明(① DNS 解析 ② 绑定并切换)
- 结果区显示 certbot 日志尾部(失败时定位)

## 7. 实测结果(2026-08-20)

- 页面 200 / 27.5KB; DNS 预检拦截 / 格式校验 / 重复绑定 / 移除主域名保护 全过
- 切换主域名 xeelee.top ↔ www.xeelee.top 即时生效(config.php)
- web 探针: reload rc=0 / certbot 1.11.0 / tmp 写 OK
- 站点无影响: 商品页 200 132KB

## 关联坑

- **配置类接口 POST 覆盖坑**: `isset($_POST['bot_token'])` 即覆盖的接口, 测试传占位符(`USE_SAVED`)会把已保存真 token 覆盖 → 后续 getMe/getUpdates 全 404。测试传真值, 或接口设计成空值不覆盖。`array_merge(现有配置, $_POST)` 防字段缺失清空。
- 证书目录多个 cert-name 并存(历史分开签的 www.xeelee.top)是残留, 实际 443 vhost 只用主证书 —— 别被 live/ 下多个目录误导。
