# 工具链（便携扫描 / BitBrowser-CDP / SearXNG / puppeteer）

> 摘自 `web-penetration-testing` 主体（2026-09 拆分，主体原 122K 撞 100K 硬限）；references 按需加载。

---

## 五、工具链

### 5.1 Python 便携端口扫描（当 /dev/tcp 或 nmap 不可用时）

在受限环境下（安全检测系统拦截 /dev/tcp、无 nmap/nc），用 Python socket 代替：

```python
import socket
def scan_port(host, port, timeout=3):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except:
        return False

# 多IP多端口扫描
targets = [('target.com', '1.2.3.4'), ('www.target.com', '1.2.3.5')]
for name, ip in targets:
    print(f'--- {name} ({ip}) ---')
    for port in [80, 443, 8080, 8443, 8888, 7777, 9090, 21, 22, 3306, 3389]:
        if scan_port(ip, port):
            print(f'  {ip}:{port} OPEN')
```

**注意**: CDN/负载均衡节点会将所有端口显示为 OPEN（TCP handshake 被代理接受），需结合 HTTP 探测区分真实服务与代理透传。

### 5.2 子域名枚举（crt.sh + DNS 爆破 + CNAME 追踪）

无 subfinder/amass 时的替代方案：

```bash
# 1. crt.sh 证书透明度（JSON模式）
curl -s 'https://crt.sh/?q=%25.target.com&output=json' | python3 -c "
import sys,json
data=json.load(sys.stdin)
subs=set()
for entry in data:
    for n in entry.get('name_value','').split('\\n'):
        n=n.strip()
        if n: subs.add(n)
for s in sorted(subs): print(s)
"

# 2. DNS 爆破（nslookup，适用于常见子域名列表）
for sub in www m api admin cdn img static test dev mail ftp blog web app vpn \
           ns1 ns2 mail pop smtp mx autodiscover direct remote support \
           git jenkins demo beta staging chat docs wiki status shop portal \
           pay login register account user panel agent; do
  result=$(nslookup "$sub.target.com" 2>/dev/null | grep -E 'Name|Address|CNAME|Aliases')
  if [ -n "$result" ] && ! echo "$result" | grep -q "NXDOMAIN"; then
    echo "$sub.target.com: $result"
  fi
done

# 3. CNAME 链追踪（发现真实基础设施）
nslookup www.target.com  # 找 CNAME 值
nslookup <cname-value>   # 递归追踪，直到拿到真实 A 记录
```

### 5.3 多端口 HTTP 服务发现

同一域名在不同端口可能跑不同服务/面板：

```bash
# 扫描常见端口上的 HTTP 服务
for port in 80 443 8080 8443 8888 7777 9090; do
  code=$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' --connect-timeout 5 -k \
    "https://target.com:$port/" 2>/dev/null)
  echo "$port: HTTP $code"
  code2=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 \
    "http://target.com:$port/" 2>/dev/null)
  if [ "$code2" != "000" ] && [ "$code2" != "$code" ]; then
    echo "  (http) $port: HTTP $code2"
  fi
done
```

### 5.4 BitBrowser 本地 API 控制

**来源**：比特指纹浏览器（bitbrowser.cn）提供本地 HTTP API 服务，可远程控制浏览器实例。用于 IP 被 CDN 封禁时通过不同环境/代理访问目标。

**开启方式**（用户操作）：
1. 打开比特浏览器软件 → 系统设置 → 本地接口
2. 开启本地 API 服务 → 复制接口地址和 API Key

**本地 API 地址格式**：`http://127.0.0.1:52xxx`

**认证方式**：HTTP Header `x-api-key: <token>`（所有请求都必须带此头）

**所有请求均为 POST，JSON body**（不是 form-data，不是 URL 传参）。

**核心 API**：

| 功能 | Endpoint | Body 参数 | 说明 |
|:-----|:---------|:----------|:-----|
| 列表窗口 | `/browser/list` | `{"page":1, "pageSize":50}` | 分页列出所有环境；totalNum=返回总数，list=具体条目 |
| 打开窗口 | `/browser/open` | `{"id":"环境ID"}` | 启动一个已存在的浏览器环境 |
| 关闭窗口 | `/browser/close` | `{"id":"环境ID"}` | 关闭指定环境 |
| 更新窗口 | `/browser/update` | 须含 `browserFingerPrint` | 更新环境配置 |
| 新建窗口 | `/browser/save` | 含 name/open_urls 等配置 | 创建新环境 |
| 启动浏览器 | `/browser/launchBrowser` | 含 id/name/open_urls | 创建+启动浏览器（速率限制：每秒最多10次） |
| 分组列表 | `/group/list` | `{"page":1, "pageSize":50}` | 列出分组 |

**API 调用示例**：
```bash
# 打开环境
curl -s -X POST http://127.0.0.1:54345/browser/open \
  -H "x-api-key: <token>" \
  -H "Content-Type: application/json" \
  -d '{"id":"environment_id"}'

# 列出环境
curl -s -X POST http://127.0.0.1:54345/browser/list \
  -H "x-api-key: <token>" \
  -H "Content-Type: application/json" \
  -d '{"page":1, "pageSize":50}'
```

**常见问题**：

| 问题 | 原因 | 解决 |
|:-----|:-----|:-----|
| `"ID不合法"` | ID 含特殊字符（如点号 `96.62.43.35`） | 使用 UUID 风格 ID（32位hex）或无点号的合法标识符 |
| 列表 `totalNum>0` 但 `list=[]` | API key 不匹配/权限不足 | 确认 API key 是管理员账号生成的，而非子账号 |
| 返回 `请求太过频繁` | 速率限制 10 req/s | 每次请求间隔至少 100ms |
| 浏览器打开了但看不到窗口 | 窗口可能在后台/最小化 | 检查 BitBrowser 主界面 |
| 列表返回 `totalNum>0` 但 `list=[]` | API key 权限不足，或数据在不同用户下 | 用管理员 API key 重试；或直接从本地 SQLite 查询 |
| 需要找浏览器的真实 UUID ID | API 列表不返回具体 ID | 直接查 BitBrowser 本地数据库：`~/AppData/Roaming/BitBrowser/db.sqlite` → `browser_persistent_data` 表获取 `browser_id` |

**BitBrowser 运行端口观察**：打开浏览器环境后，BitBrowser 会在以下常见端口段启动子进程：
- 43xx 系列（4301、4310）— BitBrowser 内部服务
- 47xx 系列（4709）— BitBrowser 内部服务
- 9xxx 系列（9210、9410）— HTTP API（返回 Base64 JWT 格式数据）
- 53xxx/60xxx 系列（53067、60812）— 其他内部通信

这些端口**不是**标准 Chrome DevTools Protocol（CDP），无法直接通过 `http://127.0.0.1:port/json/version` 调试。

**注意**：该 API 运行在用户本地 Windows 桌面，从 Hermes 终端（同样运行在用户主机上）可以调用。从云端环境不可直接访问。

**BitBrowser CDP (Chrome DevTools Protocol) 原始 WebSocket 控制**：

当需要通过 CDP 控制 BitBrowser 打开的浏览器页面时（如注入 JavaScript、获取 WebSocket 数据），标准 WebSocket 库可能被 Origin 校验拒绝。使用原始 socket 连接绕过：

```python
import socket, base64, os, json, time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(30)
s.connect(("127.0.0.1", <CDP_PORT>))  # 从 /browser/open 返回的 ws 端口

ws_key = base64.b64encode(os.urandom(16)).decode()
handshake = (
    f"GET <devtools_page_path> HTTP/1.1\r\n"
    f"Host: 127.0.0.1:<CDP_PORT>\r\n"
    f"Upgrade: websocket\r\n"
    f"Connection: Upgrade\r\n"
    f"Sec-WebSocket-Key: {ws_key}\r\n"
    f"Sec-WebSocket-Version: 13\r\n"
    f"\r\n"
)
s.send(handshake.encode())
resp = s.recv(4096)

if b"101" in resp:
    # 发送 CDP 命令（必须使用 masked frame）
    cmd = json.dumps({"id": 1, "method": method, "params": params or {}})
    mask_key = os.urandom(4)
    payload = cmd.encode()
    frame = bytearray([0x81])
    if len(payload) < 126:
        frame.append(0x80 | len(payload))
    elif len(payload) < 65536:
        frame.append(0x80 | 126)
        frame.extend(len(payload).to_bytes(2, 'big'))
    frame.extend(mask_key)
    frame.extend(bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload)))
    s.send(bytes(frame))
    
    # 读响应（自行解析帧头）
    time.sleep(1)
    data = b""
    while True:
        try:
            b = s.recv(4096)
            if not b: break
            data += b
        except: break
    # 解析：第1字节opcode，第2字节payload_len+mask
    if len(data) >= 2:
        plen = data[1] & 0x7F
        off = 2
        if plen == 126: plen, off = int.from_bytes(data[2:4], 'big'), 4
        if plen == 127: plen, off = int.from_bytes(data[2:10], 'big'), 10
        if len(data) >= off + plen:
            result = json.loads(data[off:off+plen].decode())
```

**关键**：原始 socket 不需要 Origin header，不会被 403 拒绝。适合在 WebSocket 库受限时使用。

**CDP 命令发送（WebSocket frame 构造）**：客户端到服务器的帧必须使用 **masked frame**（掩码加密）。坑点：服务器到客户端的帧**不加掩码**，但库函数（`websocket-client`）自动处理。当用原始 socket 时，必须手动构造 masked frame：

```python
import os

def make_masked_frame(payload_bytes, opcode=0x1):
    """构造客户端→服务器的 WebSocket masked frame"""
    mask_key = os.urandom(4)
    frame = bytearray()
    frame.append(0x80 | opcode)  # FIN + opcode
    length = len(payload_bytes)
    if length < 126:
        frame.append(0x80 | length)  # 0x80 = masked flag
    elif length < 65536:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, 'big'))
    else:
        frame.append(0x80 | 127)
        frame.extend(length.to_bytes(8, 'big'))
    frame.extend(mask_key)
    frame.extend(bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload_bytes)))
    return bytes(frame)

# 发送
s.send(make_masked_frame(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": "..."}}).encode()))
```

**注意**：`websocket-client` 库可能因 Chrome 的 `--remote-allow-origins` 限制返回 403 forbidden。原始 socket 方式可绕过该限制。如果原始 socket 也报 Host header 错误，不加 Host header 或 `Host: 127.0.0.1:port`。如果返回 500 "Host header is specified and is not an IP address or localhost"，确保 Host header 值为 IP 形式。

**WebSocket frame 解析（服务器响应）**：服务器帧**不加掩码**，解析方式：
```python
def parse_frame(data):
    if len(data) < 2: return None
    opcode = data[0] & 0x0F
    length = data[1] & 0x7F
    offset = 2
    if length == 126:
        length = int.from_bytes(data[2:4], 'big')
        offset = 4
    elif length == 127:
        length = int.from_bytes(data[2:10], 'big')
        offset = 10
    if len(data) < offset + length: return None  # 数据不完整
    payload = data[offset:offset+length]
    return {'opcode': opcode, 'payload': payload}
```

**适用场景**：
- 注入 JS 到已打开的页面（Runtime.evaluate）
- 监听 WebSocket 帧（Network.enable + Network.webSocketFrameReceived）
- 导航页面到指定 URL（Page.navigate）
- 获取页面 DOM/cookie/localStorage（Runtime.evaluate）

**注意**：BitBrowser Chrome 实例可能带 `--remote-allow-origins` 限制。如果 WebSocket 库连接失败，原始 socket 方式通常可行。

**Chrome 标准浏览器启动+CDP（当 BitBrowser 不可用时）**：

当 BitBrowser API 不可用时，可启动标准 Chrome/Chromium 浏览器带 remote debugging 端口，用于注入脚本和抓取数据：
