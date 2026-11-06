## 十、SSRF测试清单

- [ ] 所有URL参数（url/link/src/href/file/remote/img/page等）
- [ ] 所有POST JSON/表单字段（URL字段）
- [ ] HTTP头（X-Forwarded-For/Host/Referer/X-Forwarded-Host）
- [ ] 协议探测（http/https/file/gopher/dict/php/data等）
- [ ] 本地回环（127.0.0.1/localhost/0/0.0.0.0/[::1]）
- [ ] IP编码绕过（十进制/八进制/十六进制/IPv6/混合）
- [ ] DNS重绑定测试
- [ ] 302跳转绕过
- [ ] @符号URL解析差异
- [ ] 云元数据探测（AWS/GCP/Azure/阿里云/腾讯云）
- [ ] 本地文件读取（/etc/passwd、Windows hosts、配置文件）
- [ ] 内网端口扫描（常见端口）
- [ ] 内网Web服务探测（Tomcat/WebLogic/Jenkins等）
- [ ] Gopher协议利用（Redis/FastCGI/MySQL）
- [ ] Dict协议利用
- [ ] PHP流包装器（php://filter/phar://）
- [ ] Blind SSRF DNS/HTTP外带
- [ ] 白名单域名绕过（xip.io/子域名/@符号）
- [ ] 非HTTP协议端口探测（SSH/Redis/MySQL banner）
- [ ] CRLF注入
- [ ] Docker/Kubernetes API探测
- [ ] 凭证文件（.ssh/.aws/配置文件）

