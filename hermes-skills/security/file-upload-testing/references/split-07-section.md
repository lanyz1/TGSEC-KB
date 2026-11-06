## 六、中间件解析漏洞速查

| 中间件 | 漏洞类型 | Payload | 影响版本 |
|--------|---------|---------|---------|
| IIS 6.0 | 目录解析 | `/test.asp/1.jpg` | IIS 6.0 |
| IIS 6.0 | 分号解析 | `shell.asp;.jpg` | IIS 6.0 |
| IIS 7.0/7.5 | PHP解析 | `shell.jpg/.php`（cgi.fix_pathinfo=1）| IIS 7.x + PHP |
| Apache HTTPD | 多扩展名 | `shell.php.jpg`（AddHandler）| 所有版本配置不当 |
| Apache HTTPD | CVE-2017-15715 | `shell.php%0a` | 2.4.0-2.4.29 |
| Apache HTTPD | CVE-2021-41773 | 路径穿越 | 2.4.49 |
| Apache HTTPD | CVE-2021-42013 | 路径穿越 | 2.4.50 |
| Nginx | 解析漏洞 | `shell.jpg/.php` | 0.5.x/0.6.x/0.7<=0.7.65/0.8<=0.8.37 |
| Nginx | CVE-2013-4547 | `shell.jpg%00.php` | 0.8.41-1.5.6 |
| Nginx + Apache | 解析差异 | Nginx传给Apache | 后端Apache + .htaccess |
| Tomcat | PUT方法上传 | PUT上传JSP | Tomcat配置不当 |
| Tomcat | CVE-2017-12615 | PUT任意文件上传 | 7.0.0-7.0.81（Windows）|
| WebLogic | 任意文件上传 | 多个CVE | 多个版本 |
| JBoss | JMXInvoker上传 | 未授权部署war | JBoss 4.x/5.x/6.x |
| Resin | 解析漏洞 | `shell.jsp%00.jpg` | 老版本Resin |

