---
name: selfhosted-auth-surface-triage
description: Use when triaging a self-hosted app's auth surface.
---

# 自研站认证面分诊

黑盒打自研/二开系统时，认证面的胜负在**开打前**就定了：先量出限速维度、每挑战尝试上限、密钥空间，再决定要不要爆破。跳过这一步，几十万次请求全打在 4 秒延迟的 `pam_faildelay` 上。

触发词：自研系统后台进不去、登录三重门、429 限速、session cookie 名未知、Origin 校验、验证码爆破要不要做。

## 0. 先判「这是不是自研」

- `cf-cache-status` 有、`cf-ray` 没有 → **不是 CF 边缘**，是源站 nginx 自己加的头。判 CDN 只看 `cf-ray`（或 `server: cloudflare`）。
- 响应头出现 `x-<品牌>-cache-policy`、`server-timing: <业务>;dur=` 这类手写头 → 自研。
- 未知路径一律 200 + 固定字节数 HTML、而 `/api/*` 返回 `{"error":"未找到接口。"}` → SPA fallback + 真 API 前缀。
- chunk 名 / 事件名 / 错误串里带品牌缩写（`ymx-`、`wusi-`）→ 拿这些串全网搜，能直接定位同源代码仓库。

## 1. 先读 fetch 封装，再列端点

不要逐条 grep 路径。先找前端统一的请求函数（`async function uu(` / `fetch(` 包装），它一次暴露：鉴权头、`credentials` 模式、超时特判、哪些端点是「特殊动作」。再按 template literal 抓全部 `/api/...`。

- 带特殊超时/特殊 header 的端点 = 后端重点逻辑（支付、交付、供应商调用），优先打。
- `X-Storefront-Shop` / `X-Tenant` 这类头传无效值会被忽略并 fallback 默认租户——别把 fallback 当漏洞。

## 2. 三道门逐个拆

1. **Origin/Referer 门**：POST 回「请从本站重新打开页面 / 请从本站提交操作」= 只校验 Origin。补 `-H "Origin: https://<host>" -H "Referer: https://<host>/"` 即可，不是鉴权。
2. **Cookie 名 oracle**：拿任意值塞进猜测的 cookie 名，对比错误串。认得出名字 → 「登录已过期」；认不出 → 「请先登录」。**一次请求就能拿到真实 session cookie 名**，再决定伪造还是爆破。
3. **限速维度**：见 `references/ratelimit-and-otp-math.md`。XFF / `X-Real-IP` / `CF-Connecting-IP` / `True-Client-IP` 轮换能绕的只是「按 IP 记」那层；**按账号 / 挑战 / 全局记的那层不绕**。逐层测，别一次开 50 并发把全局计数打爆，之后所有测试全 429。

## 3. 爆破前先算，算不出来就别打

- OTP：`密钥空间 / (每挑战尝试上限 × 有效期内可换的键数)`。6 位 + 每挑战 5 次 + 10 分钟 = 死路，直接放弃。
- SSH：先测 `tries/min`（hydra 状态行）。低于 200/min 就别上大字典——2 万条也是几小时，密码多半不在里面。多开 hydra 会互相覆盖 `hydra.restore`，一律加 `-I`。
- 服务端 OTP 用 `crypto/rand` / `secrets` 生成时，任何预测/爆破都别做，直接转源码或服务器侧。

## 4. 源码到手 = 先读认证模块

特征串命中公开仓库（GitHub/Gitee）先 clone，读序：`internal/auth`、`internal/security`、`internal/payments`、路由注册处。

- token 若是 `HMAC(secret, ...)`：**.env 里的 secret 就是唯一钥匙**，伪造 token 比爆破快一千倍——火力全转到「读 .env」（SSH / 文件读 / SSRF）。
- 看四项：验证码生成源、比较函数（`subtle.ConstantTimeCompare`）、每挑战 attempts 上限、TOTP 防重放表。四项齐全 = 应用层已封死，别再试。
- 脱敏过的开源仓库（`OPEN_SOURCE_REVIEW.md`、单根 commit、Gitleaks 声明）**不会有真实密钥**；`git rev-list --all --count` = 1 就是没有历史，别在 git 历史里耗。
- 反向利用：同代码的**旧部署**（更早域名、无 CDN、错误串更详细）通常少一层防护，优先打旧版。

## 5. 资产扩展（同源更快）

- `/16` 段 masscan 443 + 逐个请求一个自研特征头，能在几分钟内找出同代码的其他部署。
- Wayback/快照里抓 `/r/<code>`、`/s/<code>` 租户码：多租户系统里这些码就是独立店铺，`?partner=<code>` 直接列该租户的商品/价格/单量。
- favicon 用 `mmh3(base64(icon))` 算 hash，但无 FOFA/Shodan key 时检索渠道基本为零——别在这上面耗。

## 6. 打不动就并行，不要单线程硬耗

长时间单点卡住时，按**互不依赖**的方向 fan-out 子代理（SSH/端口敲门、OSINT+资产、前端源码审计、支付供应商链、社工投递），主线程只留最有产出的那条。每个子代理的 context 必须自包含：目标、已确认事实、已排除项、工作目录、禁止动作。

- 子代理报回的「拿到 cookie / 登录成功」必须自己复验一次再信。
- 需要公网投递页时：`cloudflared tunnel --url http://127.0.0.1:PORT --logfile /tmp/cf.log`，URL 只出现在日志里（stdout 会被截断）；短链服务多半拉黑 trycloudflare，先试 `https://clck.ru/--?url=<encoded>`。

## Pitfalls

- ffuf 打在 SPA 上必须 `-fs <index.html 字节数>`，否则满屏 200 全是 fallback；`/api/` 的 404 JSON 才是真面。
- 应用常有两层限速（按 IP + 全局）。XFF 绕过第一层后仍 429 就说明第二层按全局/账号记，此时继续加并发只会把自己锁更久。
- 订单号「日期+4 位」看着可枚举，但归属校验按 cookie/token 做，枚举只会拿到 404——先测一条跨订单读，再决定要不要扫。
- 邮箱存在性 oracle（404 无单 / 200 发码）只证明该邮箱下过单，**不等于能读该邮箱的订单**；recovery 会话绑定的是验证码，不是邮箱。
- 任务未完成不输出「总结」；用户说「继续」= 加深不是收尾。给数字战报（已验证的洞、当前在跑的动作、下一步）代替总结。
