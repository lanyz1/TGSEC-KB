## 10. 后台自助域名绑定(一键切换, sudoers 白名单模式)

用户要求后台能自己绑域名/切换主域名, 不碰服务器时用的模式: **PHP(apache 用户) exec → `sudo -n` 白名单 root 命令**。

1. **sudoers**(/etc/sudoers.d/zengda, 先 `visudo -c -f` 校验再 install -m 440; **`Defaults:apache !requiretty` 必须**——apache 无 TTY):
   ```
   Defaults:apache !requiretty
   apache ALL=(root) NOPASSWD: /bin/cp /tmp/zengda_http.conf /etc/httpd/conf.d/zengda.conf, /bin/cp /tmp/zengda_https.conf /etc/httpd/conf.d/zengda-le-ssl.conf, /usr/bin/systemctl reload httpd, /bin/systemctl reload httpd, /usr/bin/certbot *
   ```
2. **vhost 双文件结构**: 80 段(zengda.conf, ServerName + ServerAlias + 全量 https 跳转)+ 443 段(zengda-le-ssl.conf, 证书固定指向 live/<cert-name>/)。PHP 生成内容写 `/tmp/zengda_*.conf`(apache 可写)→ `sudo -n /bin/cp` 安装 → `sudo -n systemctl reload httpd`
3. **一键绑定流程**: 域名格式校验(`/^[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?$/i`)→ **DNS 预检**(`gethostbyname($d) === 服务器IP`, 未解析直接拒绝不白签; www 也解析就一起绑)→ 新域名做 ServerName 其余做 ServerAlias → 安装 + reload → **certbot --webroot expand 全部域名进主证书**(单证书 SAN 全域名, 续期一次管全部)→ 改 config site_domain
4. **大坑: 80 段跳转规则必须排除 acme 验证路径**, 否则 webroot 挑战被 301 到 https → 签发失败:
   `RewriteCond %{REQUEST_URI} !^/\.well-known/acme-challenge/`
5. **不要用 certbot --apache 自动改 vhost**(它按 ServerName 拆段/覆盖证书行, 多域名结构不可控); 用 `certbot --webroot -w <docroot> -d d1 -d d2 --cert-name <主证书> --expand --non-interactive --agree-tos --email admin@<主域名>`
6. **验证 exec 链路**: 临时 web 探针 `exec('sudo -n /bin/systemctl reload httpd 2>&1', $o, $rc)` 返回 rc=0 即通, 测完删探针。`sudo -u apache sudo -n <cmd>` 可先 shell 层验证。
7. 后台页面: 统计卡(域名数/主域名/证书到期/证书 SAN)+ 绑定列表(主/别名徽章, 设为主域名/移除)+ 添加表单; 保护: 不能移除当前主域名。

详细实现(生成 vhost 的 PHP 函数/证书到期解析/实测结果): `references/domain-bind-sudoers.md`

