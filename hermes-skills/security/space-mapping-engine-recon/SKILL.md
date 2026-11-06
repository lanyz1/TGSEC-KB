---
name: space-mapping-engine-recon
description: "空间测绘引擎(Shodan/Fofa/Censys)找bot面板/后台/源站, 含各引擎语法与额度坑。"
---

# 空间测绘引擎侦察(Shodan / Fofa / Censys)

用测绘引擎"搜代替扫"定位 bot 管理面板、后台、源站、兄弟资产。本技能沉淀各引擎的**正确语法、免费额度限制、登录态恢复、批量提取**方法。

## 何时使用

- 找 TG Bot / 小程序 / 灰色站的管理后台面板
- 源站 IP / 兄弟域名发现
- 按品牌词/业务特征反查资产
- 用户提到「空间测绘」「shodan」「fofa」「censys」「bot面板」

## 工作原则(用户偏好,2026-08 实战纠正)

1. **针对性优先,禁止全网乱扫**: 用户明确「不要全网扫杂乱的面板,只要针对性的扫专属 bot 面板」。先提取目标的**专属指纹**(bot 用户名/品牌词/客服 @ 账号/已知域名),用指纹搜;通用 `bot+telegram` 全网搜索命中大量无关项目(AlgoGoodSignalsBot/TRX Bot/个人作品集),浪费额度且跑偏。
2. **引擎选择**: 中文特征 → **Fofa 优先**(中文覆盖最强);服务指纹/非标端口 → **Shodan**;Censys 免费版对中文内容弱(搜 `zhoushi` 全是公司名/路名误命中)。用户有 Shodan 账号。
3. **没有账号 → 教注册,不要反复要 key**: 给注册教程(注册页 URL + 3 步 + API key 位置),不是列「我没有账号」然后卡住。

## 引擎语法与坑

### Shodan(shodan.io)

```
http.title:"bot" port:443
http.html:"bot_token"
http.title:"panel" http.html:"telegram"
# 针对性: http.html:"<bot用户名>" / http.html:"<品牌词>"
```

**API 坑(2026-08 实测)**: 免费注册默认 **OSS plan = query_credits=0**。`api.shodan.io/api-info` 能验证 key(返回 plan/credits),但 `shodan/host/search` 返回 **403 Cloudflare「Just a moment...」** 且额度 0 → **API 搜索用不了**。**网页版登录后搜索免费不耗 credits**。正确路径:引导用户在浏览器登录 `https://www.shodan.io/search?query=<词>`,截图/文本发回;或 CDP 驱动已登录浏览器翻页批量抓取(每页结果含 IP/端口/标题/组织/国家,总分页 URL `?query=X&page=N`)。

**免费账号翻页墙(2026-08 实测)**: 网页版免费账号**只能看前 2 页(~15 条)**,页面提示「Please purchase a Shodan membership to access more than 2 pages of results」;1380 条全量需 $69/月。**结论: 不要为全量买会员** —— 用精准指纹词搜,命中 <15 时免费 2 页就覆盖;专属词 0 命中 = 目标面板不暴露公网,及时转攻平台 API(而不是无限换词空转)。

**已登录浏览器驱动(computer_use 不可用时的替代)**: 用户已在普通 Chrome 登录 Shodan 但没开 CDP 端口时,用 **Windows UI Automation**(PowerShell `UIAutomationClient`)驱动,不丢登录态、不打断用户窗口:
1. `Get-Process chrome | Where MainWindowTitle -match "Shodan"` 找窗口 PID
2. `AutomationElement.FromHandle($hwnd).FindAll(Descendants, TrueCondition)` 读控件树(地址栏 Edit `view_1012`、搜索结果条目、分页链接)
3. `AppActivate($proc.Id)` + `SendKeys "^l"`(聚焦地址栏)+ 输入 URL + `{ENTER}` 导航翻页(Shodan SPA 不接受 `page=N` 直接翻页会重复第 1 页,需页面内滚轮或点 NEXT)
4. `CopyFromScreen` 截屏窗口 → vision 读结果(IP/标题/组织/国家);结果条目可用 UIA 直接读 Text/Hyperlink 节点

### Fofa(fofa.info)

```
title="Bot" && body="telegram"
body="bot_token" && port="443"
title="Dashboard" && body="bot" && country="US"
# 针对性(中文品牌词直接搜):
title="周氏" / body="zhoushipg" / body="kefuzhou"
```
注册即用,免费版每天 100 次搜索;API 信息在「个人中心 → API 信息」(email + 32 位 key)。

### Censys(platform.censys.io)

**2026 迁移后 legacy 语法已失效**(`services.http.response.body:"x"` → Invalid Query),新平台正确语法:
```
host.services.endpoints.http.html_title:"bot" and host.services.endpoints.http.html_title:"panel"
host.services.endpoints.http.body:"bot_token"
```
- **登录态恢复**: Chrome profile `chrome_censys`(CDP 端口)里的 cookies(auth_v1 / search.censys.io.session.id / csrf_v2 / cf_clearance)未过期时直接可用;用 CDP 的 Network.getAllCookies 取出后注入 API 请求。
- **API 端**: `search.censys.io/api/v2` 会 302,需跟随到 platform;免费版仅 5 次搜索/天,额度显示在页面「CREDITS 55/100」。
- **搜索入口整体重定向(2026-08 实测)**: `search.censys.io/search?...` 现在直接 302 到 `censys.io/platform-redirect?target=...` 再到 platform。**页面标题「Censys - Not Found」+ body「You have run out of credits. Buy credits now!」= 免费额度已耗尽**(免费版 5 次/天 + 100 credits,用完即 404 页,不是语法错)。额度耗尽后不要反复试 — 换 Shodan 网页版/CDN 绕过/直接源站探测。
- **批量提取**: CDP 导航搜索结果页 → `window.scrollBy` 滚动 → `document.body.innerText` 正则提取 IP。

### 单 IP 权威指纹验证(端口扫描假象纠正)

本机有 v2rayN TUN 时,Python socket 直连扫描会显示"全部端口开放"(0.0s 扫完 N 端口全 open)——**TUN 劫持假象,绝不可信**。用 Censys 查单 IP 权威数据:
- 页面: `search.censys.io/hosts/<IP>`(自动跳 platform)→ 显示开放端口/OS/服务软件/ASN/位置
- 用已登录 CDP profile(chrome_censys)导航, `document.body.innerText` 提取结果
- 判定: 本机扫描 vs Censys 不一致时**以 Censys 为准**(被动观察 > 本地主动假象); Censys 确认仅 22/80/443 时别在端口面浪费(连 SSH banner 都不回 = 源 IP 限制/fail2ban,放弃)
- 实例: 惊蛰 13.250.123.177 本机扫出 64 端口全开(含 27017 MongoDB),Censys 证明只有 22/80/443

**CDP Chrome 启动坑(2026-08 实测)**: Chrome 新版默认拒绝外部 WebSocket 连接(websocket-client 报 `Handshake status 403 Forbidden ... Rejected an incoming WebSocket connection from the http://127.0.0.1:9227 origin`)。必须加 `--remote-allow-origins=*`:
```
chrome --remote-debugging-port=9227 --remote-allow-origins=* --user-data-dir=<profile>
```
不加这个 flag 时 CDP /json 能返回但 WebSocket 连不上,白费一轮。

### 证书 SAN 挖隐藏兄弟域名(被动侦察)

目标主域名证书的 SAN 常暴露隐藏 vhost/备用域名:
```bash
echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -text | grep -A3 "Subject Alternative Name"
```
命中新域名后: 解析看是否同 IP(备用域/回源),再验证 HTTP 行为是否独立应用; 若 APK/JS 里 grep 不到 = 纯证书/配置层资产,记录进资产清单即可。实例: 惊蛰 app.jing-zhe.com 证书 SAN 挖出 `app.jingzhelh.com`(同 IP 隐藏 vhost,主域无 A 记录)。

## 登录态恢复通用套路

1. 找已登录的 Chrome profile(用户平时登录过目标引擎): `ls /c/Users/<user>/chrome_<engine>*/Default/Network/Cookies`
2. 用 CDP 启动该 profile: `chrome --remote-debugging-port=<p> --user-data-dir=<profile>`
3. `Network.getAllCookies` 检查/提取 session cookie;页面 `innerText` 确认登录态(未登录会显示 Register/Login 按钮)

## 参考

- `references/bot-panel-recon-202608.md` — 周氏PG/AYX 实战:品牌反查平台、API 头逆向、面板验证


---

## 外部库增量（2026-10-11 分享包）

## 账号/额度实测状态（2026-09-25，勿重复探）

| 引擎 | 本机凭据 | 实测结果（原文） | 可用的路 |
|---|---|---|---|
| Quake | 有 key | `GET /api/v3/user/info` → `{"code":"q2001","message":"该账户尚未进行身份认证，请登录Quake平台认证后再试。"}` ⇒ 搜索全拒 | 先去 quake.360.cn 实名认证 |
| Censys | 有 token | Platform `POST /v3/global/search/query` → **403** `This endpoint requires an organization ID for API access. Free users can only access this endpoint through the Platform UI.`；旧 v2 → **401** + `The Censys Search v2 API will be shut down on September 30, 2026.` | ① 登录 UI（`templates/cdp_ui_query.py`）② 拿到 org ID 后走 Platform API |
| Shodan | 无（`chrome_profile_shodan` 里 0 cookie） | — | 需注冊/API key |
| FOFA | **有月卡(经中转站)** | `?key=` 鉴权实测通过;`search/all` 消费=返回条数 | 可用,配置见上「Fofa」节 |
| ZoomEye | 无 | 同上 | 需注册 |

★`chrome_censys` / `chrome_profile_censys` 里有 `cf_clearance`(300+ 天) 与 `remember_me`，但**页面仍是未登录** ⇒ cookie 活着不等于 session 活着。
