## 一、SSRF完整攻击面

### 1.1 SSRF触发点
| 功能/参数 | 说明 |
|---------|------|
| URL预览/分享 | `?url=http://xxx`、`?link=xxx` |
| 网页截图/转PDF | `?src=http://xxx`、wkhtmltopdf/PhantomJS |
| 文件上传（远程URL）| `?remote_url=http://xxx/image.jpg` |
| Webhook/回调 | 支付回调、消息通知Webhook URL |
| API代理/转发 | 后端代理请求外部API |
| 数据导入 | `import?url=http://xxx/data.xml` |
| 图片处理 | 远程图片拉取、缩略图生成 |
| PDF生成 | wkhtmltopdf加载远程资源 |
| oEmbed/OpenGraph | 社交分享预览 |
| 远程头像/封面 | 通过URL拉取头像 |
| RSS/ATOM订阅 | RSS源URL |
| Trackback/Pingback | WordPress/Trackback |
| 健康检查/监控 | URL连通性检测 |
| 文件格式转换 | pandoc/ffmpeg拉取远程文件 |
| 验证码服务 | 远程验证码图片拉取 |
| 下载功能 | `?file_url=http://xxx` |
| OCR/图片识别 | 远程图片URL |
| 翻译服务 | 翻译远程网页 |
| DNS查询/域名验证 | 域名所有权验证 |

### 1.2 协议支持
| 协议 | 端口/利用 | 支持情况 |
|------|---------|---------|
| `http://` / `https://` | 80/443，内网Web、云元数据 | 几乎所有语言/库支持 |
| `file:///` | 本地文件读取 | PHP/cURL支持、Java支持、.NET部分支持 |
| `gopher://` | 任意TCP协议构造（Redis/FastCGI/MySQL等）| PHP/cURL、部分语言库 |
| `dict://` | 端口探测、发送TCP命令 | PHP/cURL |
| `ftp://` | FTP访问、匿名FTP | 多数支持 |
| `ldap://` / `ldaps://` | LDAP注入、信息泄露 | Java/PHP |
| `tftp://` | UDP文件传输（UDP SSRF）| 部分支持 |
| `ssh2://` | SSH连接（需认证）| PHP |
| `telnet://` | TCP原始通信 | PHP/cURL |
| `jar://` | Java解压读取文件 | Java（ZIP Slip）|
| `netdoc://` | Java本地文件读取 | Java旧版本 |
| `php://` | PHP流包装器 | PHP |
| `data://` / `data:text/html` | 内联数据 | 多数支持 |
| `glob://` | 文件查找 | PHP |
| `expect://` | 命令执行（需expect扩展）| PHP |
| `ogg://` | 音频流 | PHP |
| `zlib://` / `zip://` | 压缩包文件读取 | PHP |
| `phar://` | PHP反序列化触发 | PHP |

### 1.3 漏洞危害等级
```
Level 1: 内网端口/服务探测（端口扫描、服务识别）
Level 2: 本地文件读取（file://协议）
Level 3: 云元数据访问（AWS/GCP/Azure/阿里云AK/SK窃取）
Level 4: 内网未授权服务访问（Redis/Memcached/Elasticsearch）
Level 5: 内网Web漏洞利用（Struts2/WebLogic/Jenkins未授权）
Level 6: 协议级RCE（Gopher→Redis/FastCGI RCE）
Level 7: 内网横向移动（SMB哈希捕获/NTLM Relay）
Level 8: 云环境容器逃逸/元数据命令执行
```

