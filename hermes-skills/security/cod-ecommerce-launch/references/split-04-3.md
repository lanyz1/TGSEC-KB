## 3. 代码上传(本地/服务器配置分离!)

- 本地 tar.gz → SFTP 上传 → 服务器解压到 /var/www/<site>
- **大坑: 批量同步把本地开发 config.php 覆盖服务器生产配置**(后台密码被改回 admin123, 之后的"登录成功"全是登录页假阳性)。上传文件列表**排除 config.php**, 部署后用 sed 单独写服务器配置; 或上传后立即校验 `grep admin_pass config.php`。
- 权限: `chown -R apache:apache` + `find data -type f -exec chmod 664 {} \;`; SELinux: `chcon -R -t httpd_sys_content_t`
- httpd vhost: `AllowOverride All` + `Options -Indexes`(伪静态 .htaccess 生效)

