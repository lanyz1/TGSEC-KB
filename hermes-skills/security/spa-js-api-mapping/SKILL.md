---
name: spa-js-api-mapping
description: "Use when SPA/JS frontend: map API surface from assets; reverse anti-bot/PoW gates via in-browser replay."
version: 1.0.0
tags: [pentest, web, spa, js, api, recon, webpack, chunk, 前端打包, 找接口]
---

# SPA 前端资产 → API 面测绘

来源: 2026-10 betmaster（白标博彩）案例。适用一切现代前端目标（vite/rolldown/webpack SPA、白标站、后台管理面）：前端跑得起来，后端 API 面就藏在 JS 资产和运行流量里。

## 核心顺序（按此走，不要跳）

1. **首页配置提取**：curl 首页 HTML → 找内联配置：`window.__ENV=`、`__NEXT_DATA__`、`__NUXT__`、`window.__APP_CONFIG__` 等。一个 JSON 常含：实例名、品牌码、Sentry DSN、S3/对象存储桶、图片代理/静态云 URL、统计 ID。压缩单行用 Python 切片解析（先定位起点再按 JSON 括号配对；正则字符类易报 Invalid range end 的坑）。
2. **资产全量爬取**：解析 `<script src>` + 运行时动态 `import(` 的 chunk（hash 目录结构如 `assets/<hash>/<name>`）。落盘后分析；压缩 bundle 直接 grep 关键字常 0 命中，**别因此下“没 API”结论**。
3. **字符串字面量提取再过滤**：全量提取每个 JS 的字符串字面量与 `/` 开头路径（见 `scripts/extract_js_strings.py`），再按前缀统计/过滤出 `/api`、`/challenge`、自定义头名 —— 比 grep 关键字可靠得多。方法级路由正则 `(get|post|put|patch|delete)\s+/[a-zA-Z0-9_/{}$.:-]+` 直扫包装函数（`kA(\`post /x\`)` 类），一次拿全端点清单——带 `{user_id}`/`{transaction_id}` 占位的即 IDOR 候选清单（本案例一键 171 条）。
4. **headless 抓包（最可靠一步）**：Playwright 真浏览器跑首页 + 关键流程，抓 XHR/fetch/WS（见 `scripts/capture_net.py`）。初始化顺序、挑战流程、第三方上报域只有运行流量能看到。
5. **未鉴权端点验证**：逐个行为验证（状态码/响应体），标注：免登录吐数据的（最高价值）、要登录的（IDOR 候选）、被风控挡的。
6. **风控/反爬门复现（本技能最高价值环节）**：端点返回挑战结构（`{func, params}` PoW）、边缘 403、或「凭据错误」时，按此顺序处理：
   - **先怀疑假错误**：现代风控对非浏览器客户端（curl/requests/裸 TLS 指纹）返回**语义合理的假响应**（如注册端点对任何输入都回 `invalid login/password`，实际是机器人评分拒答）。判定：同一请求改从真浏览器上下文（Playwright `page.evaluate` 页内 fetch）重放——响应不同（出现真实校验错误/挑战）即坐实。**坐实之前不要对错误语义下任何结论。**
   - **页内 RPC 是终极通道**：挑战求解、注册/登录等敏感调用，一律改为「页面内 fetch + 页内求解 + 自动重试循环」（模板 `templates/browser_rpc.py`），比任何请求头伪造都稳。
   - **PoW 求解照抄 JS 语义**：`zeros`=找最小 i 使 `SHA256(Utf8(b) + uint32BE(2^31+i))` 前 a 个半字节为 0，答案=`btoa` 4字节BE（标准 base64 带填充）；`sha256`=输入重复 ceil(a) 次后哈希取 hex。常见自造坑：**JS `TextEncoder.encode` 编码的是 hex 字符串本身而非 hex 解码**；重发带三个头 `X-Verify-data`/`X-Verify-sign`（挑战响应头原样回传）+ `X-Verify-result`，循环到非挑战响应为止（每轮换新 token；客户端节流 1s→2s→4s…）。
   - **字段 schema 用空载荷逼出来**：空/畸形 body 的报错即字段清单（`"currency":"Field required"`、`"marketing":"Invalid format"`、`value_error.discriminated_union.missing_discriminator` → 判别字段 `shape_id`）。可选字段按真实客户端行为**省略**（undefined 会被 JSON.stringify 丢弃），别乱塞 null/False。
   - **枚举全部认证通道再选最弱一条**：同平台多通道（email/phone/whatsapp/account_id/oauth）门禁不同——本案例 email/phone 注册被地区门 418+反匿名全拦，而 `account_id` 通道**无短信/邮箱/证件/地区检查直接发号**（响应里连生成密码都在）。通道清单来自 JS 路由表，逐个页内 RPC 实测。
   - **登录后再测绘令牌面**：同平台常多 token 并存（普通 + 服务专用，如 `api_auth_token_promo_action`），TTL 不同、过期报 `JWT token expired`——勿跨会话缓存，用前重登刷新（signin 响应即含新 token）；路径参数多为 **UUID（user.id）而非数字账号**（塞数字 → 404/500）。跨账号探测换真实他人 UUID：对方服务直接 500 而非清洁拒绝 = 边界守住 + 健壮性缺陷（记入报告，非击穿）。

## 高价值目标清单（见到优先测）

- 平台配置 API（`/api/init/*`、`/api/manifest`）——免登录吐币种/地区/license/功能开关。
- 目录/列表 API（catalog、promotion-codes）——批量数据、常免登录。
- 支付/账户面（`/api/payment/history/${id}/invoice` 类）——IDOR 候选，需登录后枚举（确认门：默认 5 / 硬顶 20）。
- 自定义头名（JS 里 `VND-*`、`X-*` 字面量）——复现请求的必要条件，也常是后端信任判断点。

## Pitfalls

- 压缩单行 JS：grep 关键字 0 命中 ≠ 无内容；换字符串提取全量落盘再过滤。
- 静态源常在独立云域（`src.<cloud>`），页面域名下不挂资源；证书/CNAME 里找。
- 图片代理（imgproxy 类 `/_/<opts>/plain/<url>`）可当 SSRF 原语测：外链代理先确认，内网地址做负对照。
- 版本 ≠ 漏洞；JS 里读到的路由要行为验证（状态码/响应体）。
- 挑战/风控门：先读 JS 求解逻辑再复现；边缘（openresty 等）403 多为缺请求头/流程，不是端点不存在。
- **假错误铁律（2026-10 定型）**：非浏览器客户端可能收到机器人评分的**假响应**（恒回格式正确的 `invalid login/password` 等）；对认证/注册语义下结论前，必须用真浏览器上下文做对照臂（细法见 `references/antibot-pow-reversal.md`）。
- 浏览器版本/平台头必须用**真浏览器抓包值**：同站不同市场构建号不同（`production-1087` vs `malta-1474`），平台值（`browser`/`desktop`）直接影响边缘放行；用错吃 openresty 403。
- 地区门（418 "service is not available for your region"）≠ 终点：先比通道差异（某些通道不查地区），再判反匿名（同地区 Tor 出口照样被拒）。

## Support files

- `references/betmaster-white-label-case.md` — betmaster.com.mx 完整测绘记录（关联面发现 → API 面 → imgproxy → 账号生命周期/令牌面 → torrero.cloud 族 → 接棒）。
- `references/antibot-pow-reversal.md` — 机器人评分假响应 + X-Verify PoW 完整逆向（求解器语义/三头重放/页内 RPC/认证通道枚举）。
- `scripts/capture_net.py` — Playwright 抓 XHR/fetch/WS 流量（headless）。
- `scripts/extract_js_strings.py` — JS 字符串字面量/路径全量提取。
- `templates/browser_rpc.py` — 页内 fetch RPC + PoW 自动求解循环模板（Playwright，适配即用）。

## Related

- JS 混淆（obfuscator.io）去混淆 → `js-deobfuscation`
- 逆向任务路由（webpack/前端加密）→ `reverse-skill`（js-reverse）
- 管理面（OpenMetadata/Grafana/Airflow 等）测试 → `oss-deployed-app-audit`
