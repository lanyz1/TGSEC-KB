---
name: flask-security-testing
description: Use when 目标为 Python Flask/Werkzeug 应用。侦察、认证扫描与常见陷阱。
---

# Flask / Werkzeug 应用安全评估

针对 Python Flask（Werkzeug）Web 应用的专项资产测绘与安全评估。识别特征：`Server: Werkzeug/x.y.z Python/x.y.z` 响应头、`Content-Disposition: inline; filename=index.html`（`send_file` 服务静态页）。与 `fastapi-security-testing` 对称，覆盖 Flask 特有的 session 认证、开发服务器行为与 JSON 误报陷阱。

## 1. 侦察 — 前端 JS 是首要金矿

Flask 单页后台的 `app.js` + `index.html` 通常泄露**完整 API 端点清单、业务逻辑、默认密钥值**，价值高于目录爆破：

```bash
curl -s http://TARGET/app.js -o app.js
curl -s http://TARGET/ -o index.html
# 提取全部 API 端点（含动态拼接）
grep -oE "'/api/[a-z_/]*'" app.js | sort -u
grep -oE "api\(`/api/[^`]*\$\{[^`]*`" app.js   # 动态路径如 /api/products/${id}/inventory
# 默认密钥/占位符/业务架构说明
grep -niE "secret|token|key|default|placeholder|config|mysql|redis" index.html app.js
```

实测「号铺机器人」的 `app.js` 明文暴露 `okpay_notify_secret` 默认值 `okpay_notify_secret`，`index.html` 暴露支付回调 URL 与「MySQL 和 Redis 连接信息走 config.py / 环境变量」。前端文件是攻击面地图，先抓再爆破。

## 2. 认证模型

Flask 后台常见 **session cookie 认证**（响应头 `Vary: Cookie`）+ 密码登录：

- `/api/login` POST `{username,password}` → 成功才 `Set-Cookie`（失败 401 无 cookie）
- `/api/check_auth` 返回 `{"authenticated":false}` + 401（软认证探针），其余端点 401 `{"error":"请先登录"}`

session 伪造需知道 `secret_key`（Flask 默认 signed cookie，salt=`cookie-session`，itsdangerous `URLSafeTimedSerializer`）；若 `os.urandom` 随机生成则不可伪造，弱 secret_key 字典测试（675 组合量级）通常秒级跑完但未必命中。

## 3. JSON 双引号误报陷阱（关键）

在 JSON body 里测 SQL 注入时，**双引号 payload 会破坏 JSON 结构**，导致 `request.json` 为 None，后端抛 `'NoneType' object has no attribute 'get'`（500）。这**不是 SQL 注入**，是 JSON 解析失败：

```bash
# 错误：admin" OR "1"="1 里的双引号使 JSON 非法 -> 'NoneType' object has no attribute 'get'
curl -d '{"username":"admin" OR "1"="1","password":"x"}' ...
# 正确：用 json.dumps 转义后重测，才是真实注入判定
python3 -c "import json;print(json.dumps({'username':'admin\" OR \"1\"=\"1'}))"
```

单引号在 JSON 里合法可正常传；双引号必须先转义。正确转义后若仍返回统一错误（"用户名或密码错误"）且无时间延迟，才是参数化查询（无注入）。

## 4. 时序侧信道枚举用户名（慢哈希）

密码哈希为慢哈希（bcrypt/pbkdf2 ~300ms+）时，响应时间可区分用户名是否存在：

- 用户名存在 → 查库 + 计算哈希 ≈ **440ms**
- 用户名不存在 → 查库无结果直接返回 ≈ **100ms**（约 4 倍差距）

多次取中位数确认（避免冷启动/网络抖动干扰）。这既证实某用户名有效，也暴露慢哈希（暴力破解每密码 ~340ms，速率受限，需并发）。

## 5. Werkzeug 开发服务器特性

- **单线程默认**：`nuclei -rl 15` 等并发扫描会压垮它，触发 `Connection reset by peer`（Errno 104）。先停并发扫描再单测，或降低 `-rl`。
- **直连公网暴露**：`Server: Werkzeug` 直接出现在公网端口（绕过 Caddy/Nginx 反代）本身是配置问题（生产应 gunicorn/uwsgi），且暴露面大于反代后的入口。
- **debug 模式判定**：访问不存在路径，返回 HTML traceback = debug True（有 Werkzeug debugger/PIN）；返回统一 JSON 错误（404 被包装成 500）= debug False + 全局错误 handler。

## 6. 支付回调端点 stub 判定

`/api/recharge/okpay/notify/{secret}` 类回调端点常是 **stub**：对任意 secret 路径、任意参数（含不存在的订单号、超长串、非法 JSON）都返回固定 `{"status":"success"}`。先用时间盲注确认它是否真的处理输入（`order_no="test' OR SLEEP(5)-- -"` 无延迟 = 不查库），避免在 stub 上浪费时间。真正可利用的回调应返回业务匹配错误（"未匹配到订单"）而非固定 success。

## 7. Pitfalls

- **双引号 JSON 误报**：见 §3，是最常见的假阳性来源，会把人带进"SQL 注入"的岔路。
- **404 包装成 500**：错误信息泄露内部异常（如 `'NoneType' object has no attribute 'get'`），但无 debug traceback 时不可 RCE，勿误判为 debug 模式。
- **诚实报告**：弱口令、session 伪造（弱 secret_key）、JWT 伪造可能全部失败（强密钥）；如实说明障碍与后续路径，不要虚构"已突破"。
- **关联资产**：duckdns 动态域名（如 `wangliuliu.duckdns.org`）可能指向另一台服务器（不同 IP），记录为关联资产但需单独授权再测，不越界。
