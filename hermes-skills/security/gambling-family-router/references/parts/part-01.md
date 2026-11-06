# gambling-family-router 全文 第 1/4 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## 6. 通用侦察命令（Phase-0.5）

在指纹识别后、分发前的补充侦察：

```bash
# 注册探测（看是否需要邀请码/实名/绑卡）
curl -sk "https://TARGET/app-api/member/auth/register" \
  -X POST -H "Content-Type: application/json" \
  -d '{"mobile":"<PHONE-REDACTED>","password":"Test123456"}' | python3 -m json.tool

# 支付渠道探测
curl -sk "https://TARGET/app-api/pay/channel/list" \
  -H "Authorization: Bearer <TOKEN>" | python3 -m json.tool

# 资金 API 探测（wallet_id 面）
curl -sk "https://TARGET/app-api/member/wallet/get" \
  -H "Authorization: Bearer <TOKEN>" | python3 -m json.tool

# USDT 收款地址探测
curl -sk "https://TARGET/app-api/pay/order/deposit" \
  -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"channelCode":"usdt_trc20","amount":100}' | python3 -m json.tool

# Actuator 补查（资金面阴性后打）
curl -sk "https://TARGET/actuator" -o /dev/null -w '%{http_code}'
curl -sk "https://TARGET/actuator/env" | head -c 500
```

### 6.1 批量指纹识别脚本

```python
#!/usr/bin/env python3
"""gambling_family_fingerprint.py - 批量识别白标家族"""
import subprocess, json, sys

TARGET = sys.argv[1] if len(sys.argv) > 1 else input("TARGET: ")
results = {}

fingerprints = {
    "yudao":    ["/app-api/member/auth/sms-login", "/app-config.js", "/admin-api/system/auth/login"],
    "1z":       ["/qpuserapi/", "/api/game/list"],
    "dingyi":   ["/api/v1/user/verifyKey"],
    "gofun":    ["/"],  # grep SINGKETY
    "lsm":      ["/"],  # grep lsmview
    "qzino":    ["/api.html"],
    "brazil":   ["/api/trpc/health"],
    "whgame":   ["/"],  # grep QPAccountsDB
    "dujiao":   ["/dj.svg"],
    "wali":     ["/trial.do"],
    "kk8":      ["/gc?c=test"],
}

for family, paths in fingerprints.items():
    for path in paths:
        url = f"https://{TARGET}{path}"
        try:
            r = subprocess.run(
                ["curl", "-sk", url, "-o", "/dev/null", "-w", "%{http_code}",
                 "--connect-timeout", "5", "--max-time", "10"],
                capture_output=True, text=True, timeout=15
            )
            code = r.stdout.strip()
            if code in ("200", "405", "401", "403"):
                results[family] = {"path": path, "status": code}
        except Exception:
            pass

print(json.dumps(results, indent=2, ensure_ascii=False))
if results:
    families = list(results.keys())
    print(f"\n[+] 识别到家族: {', '.join(families)}")
    print("[!] 请立刻 Read 对应专卡并深入打击")
else:
    print("\n[-] 未识别到已知家族，尝试 strike_probe 通用突击")
```

---

## 7. 成功口径

| 档 | 成立条件 | 不算 |
|----|----------|------|
| L1 指纹 | 确认家族归属 + 分发到专卡 | 只扫首页未判族 |
| L2 侦察 | 注册成功 / API 可达 / 支付渠道可枚举 | 只判族未深入 |
| L3 利用 | 专卡完成至少一个利用（假支付/IDOR/ATO/接管） | 停在路由卡层 |

---

## 8. 上下游关联

### 上游
- `case-triage` → 定级后进入本卡
- `tma-web-asset-discovery` → FOFA 侦察后导入

### 下游（按家族）
- 芋道系：`yudao-appapi-pentest` → `yudao-daifu-mock-file-rce` → `encrypted-api-spa`
- 资金面：`fund-edge-ops` → `usdt-deposit-attribution-hijack` → `payment-callback-forgery`
- 密码重置：`gambling-password-reset-ato` → `ato_reset_withdraw_probe.py`（oracle / dummy-reset / bola-reset / 提现三件套）
- 社工面：`autonomous-social-engagement`

### 横切工具
- `tools/ops/auto_campaign.py` — 指纹菜单
- `tools/ops/yudao_appapi_probe.py` — 芋道探针
- `tools/ops/strike_probe.py` — 通用突击 S1-S8
- `tools/ops/scope_expand.py` — 授权写入
- `tools/ops/yudao_daifu_probe.py` — 芋道代付探针

---

## 9. FAQ / 常见陷阱

1. **Q: 扫了 /actuator 就结案？**
   A: 禁止。资金面阴性后才打基础设施（Actuator/宝塔），且 Actuator 要走 Spring Gateway 全链。

2. **Q: 芋道和 Qzino 长得像怎么区分？**
   A: 芋道有 `/app-api` + `VITE_APP_TENANT_ENABLE`；Qzino 有 `/api.html` 文档页。勿套芋道信封给 Qzino。

3. **Q: 看到 sk_encrypt 但不确定是哪族？**
   A: 直接走 `encrypted-api-spa`（加密 API 通用逆向），不必先定族。

4. **Q: 多个指纹同时命中？**
   A: 叠层打——入口卡 + 家族卡 + 横切卡并行，不合并。

5. **Q: FOFA 找到疑似同源实例？**
   A: 不在 scope 的禁止扩权。已授权主站发现的中转域可 `scope_expand` 静默并入。

---

<!-- 补充视角: white-label-casino-pentest (兄弟技能库 2026-09-12) -->

---
name: white-label-casino-pentest
description: 白标赌场/博彩平台渗透 — RTG 识别、SignalR 协议、源站绕过。
version: 1.0.0
author: SurveyEngine Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
    category: security
---

# 白标赌场/博彩平台渗透

针对白标在线赌场(白标 = 自己不研发,租用第三方游戏平台如 RTG/Softech 的站点)的渗透方法论:批量站点侦察、白标平台识别、SignalR 实时 API 攻击、Cloudflare 源站绕过。目标是授权资产/CTF 靶场。

## When to Use

- 用户一次给多个赌场/博彩站点要求批量渗透
- 站点出现 `cdk.<domain>` / `play.<domain>` 子域(游戏平台入口)
- 主站 `/signup` 302 到 `signup.<domain>`(独立注册子域,BFF 架构)
- 页面加载 `signalr.js` / `LobbyCore` / `games.club` 模板 / `gamelauncher.min.js`
- 目标疑似 RTG(RealTime Gaming)、Softech、BetConstruct 等白标平台
- 需要绕过 Cloudflare WAF 找真实源站 IP
- 前端 JS 出现 `CMD_MB_*` / `SUB_MB_*` / `MDM_*` 协议号 + emscripten wasm 网络库 → **自定义二进制 WebSocket 协议平台**(非 SignalR,见「二进制 WS 协议平台」节)
- HTML `<html data-js-vars="...">` Base64(UTF-16LE)配置属性 + `casinoLoginUrl` 指向 `*.gameassists.co.uk/gambit/` → **MGS/Gambit 白标平台**(见 references/gambit-mgs-platform.md)
- 主站引用 `/media/system/js/core.min.js` + `/media/templates/site/<name>/` → **Joomla CMS**(RTG 系赌场主站常见;`/api/index.php/v1/config/application?public=true` = CVE-2023-23752 未授权配置泄露,常被 CF WAF 挡,试源站直连)
- 用户对批量任务说「从一个开始一个一个来,挖到无法突破再继续下一个」→ **串行深入模式**:按漏洞量/突破潜力排序,单目标打穿到瓶颈再切,不要全部并行蜻蜓点水

## Prerequisites

- 目标为授权资产 / 用户自有学习材料
- 本机 v2rayN singbox_tun 会使 TCP 端口扫描全部显示 OPEN(假象),HTTP 层结果可信
- 批量任务先跑一轮统一指纹,再按信号分级深入,不要逐站全量打

## Quick Reference

```bash
# 1. 批量侦察(10 站点一轮):见 scripts/batch_recon.py
# 输出每站:IP / Server / X-Powered-By / CF 与否 / Title / 是否有 WP / body 大小

# 2. 白标平台识别信号
#    - 登录页 302 到 cdk.<domain>/lobby?SkinId=N  ← 游戏平台子域
#    - 页面引用 signalr.js → 实时 API(SignalR)
#    - LobbyCore/CDK.js/games.club 模板 → RTG 系
#    - gamelauncher.min.js + /Scripts/ + /bundles/ → ASP.NET MVC

# 3. 源站发现:找解析到非 Cloudflare IP 的子域
for s in m api cdk play; do echo "$s.<domain>: $(python -c "import socket;print(socket.gethostbyname('$s.<domain>'))")"; done
# 非 104.x/172.x/188.x/103.x 段 = 可能源站!直接 Host 头打:
curl -sS -I "http://<origin-ip>/" -H "Host: cdk.<domain>"   # 200 = 绕过 CF 成功

# 4. SignalR 2.x 探测
curl "https://cdk.<domain>/signalr/negotiate?clientProtocol=1.5&connectionData=%5B%7B%22name%22%3A%22lobbyhub%22%7D%5D"
# → 无鉴权返回 ConnectionToken(DPAPI 加密)+ ConnectionId

# 5. hub 方法枚举:下载平台核心 JS 找方法数组
grep -oE "LobbyHubMethods[^]]{0,2000}" CDK.js   # 100+ 方法:CreatePlayer/GetPlayerBalances/ForgotPassword...
```

## Procedure

1. **批量侦察** — 写脚本一轮抓全部站点的 DNS/IP、HTTP 头、Title、body 大小、是否 WP。按信号分级:有源站/特殊后端/API 泄露的深入,Next.js 常规站快速跳过。
2. **白标平台识别** — 登录页 302 到 `cdk.<domain>/lobby?SkinId=N` 是强信号;页面加载 signalr.js + LobbyCore = RTG 系;`/Scripts/gamelauncher.min.js` + `/bundles/` = ASP.NET MVC。
3. **下载平台核心 JS(CDK.js)** — 从 lobby 页面 HTML 提取 `LobbyCorePackages/<版本>/AllSpark3/CDK.js` 或 `LobbyCore/All`(注意路径有**双斜杠**,Azure Blob 路径敏感);CDK.js 含全部 hub 方法数组(`LobbyHubMethods` / `gamehub` / `databasenotifyhub` / `tournamentshub`)。
4. **SignalR 协议探测** — `GET /signalr/negotiate`(无鉴权,返回 DPAPI ConnectionToken + ConnectionId)→ `GET /signalr/connect`(S:1 = 连接成功)→ `POST /signalr/send` → `GET /signalr/poll`。hub 名全小写(`lobbyhub`)。**send 的 data 参数是 form-urlencoded 的 JSON 字符串,不是 JSON body!**
5. **hub 方法调用限制** — 多数平台未登录不建立 hub 连接(`hub.server` 不绑定),方法调用需先登录;此时记录方法清单作为攻击面,转向注册流程或源站。
6. **注册体系攻破(BFF 路径)** — 主站 `/signup` 302 到 `signup.<domain>` 就是注册子域;其 SPA 资源路径(`./bff/api/...`)泄露 BFF 前缀;对 `POST /bff/api/auth/signup` 发 `{}` 用**错误驱动字段枚举**(服务端逐轮返回缺失字段,补齐再试,直至还原完整扁平字段清单);预检接口 `POST /bff/api/auth/validate-email`、`/auth/check-username-availability` 可做邮箱域名黑名单探测 + 用户名枚举。**手机号格式卡住时逆向前端 JS 找提交前转换函数**(如 FairGo `normalizePhoneNumber(e) = "00"+数字清洗` → 提交格式 `00`+国家码+本地号,盲试组合浪费时间)。注册成功后若响应带 `providerSignInToken`/`providerSignInUrl`(免密登录 URL)= 设计缺陷,记录为漏洞。细节见 references/fairgo-signup-bff-case.md。

7. **KYC 用户枚举(注册接口)** — 注册时用某人姓名+生日,若与现有用户匹配,返回 `"Welcome back, <NAME>..."` 并泄露**该用户用户名 + 部分掩码邮箱**(errorDetails 字段甚至给完整邮箱)= 用户存在性枚举 + 账号关联。同名+同生日去重(KYC 反欺诈)会阻止重复注册 — 换姓名/生日再注册。此机制同时是反批量注册的识别点,报告里分别记录漏洞与防护。
7b. **登录态建立(CDK.logIn)与登录后数据面** — 在 lobby 页面 console 里 `CDK.logIn('user','pass',true,false,true)`(见 Pitfall 的 10 参数还原)登录成功后,立即批量调用敏感方法(全部返回明文):
    - `GetPlayerBalances` → 余额结构(Balance/BonusBalance/CompPoints/WithdrawableBalance)
    - `GetAccountInfo` → **完整 PII + 密码哈希**(Firstname/Lastname/Email/Address/DOB/HashedPassword — 长哈希格式,离线爆破面)
    - `GetCashierSettings("deposit"/"payout"/"coupon")` → **收银台 URL + RTGPID + CashierSessionID + HashedPassword(SHA1 短格式)**
    - `GetAvailableCouponsInfo(true,false)` → 优惠券清单(Code/描述/流水要求 — 如 WELCOME 100% 首存 $1000 x30 流水)
    - `GetPlayerMessages` → 玩家消息(欢迎奖金等)
    - 这些接口拿到的 RTGPID/CashierSessionID/token 是收银台会话凭据,收银台入口:`https://m.<casino>.com:2500/audfairg/Mobile.WebSite/Handlers/Router.ashx?route=Cashier&pid=<RTGPID>&token={GUID}s@Lt&type=1&clienttype=f&skinid=1&force=true&platformUrlHostSet=1&theme=dark`(token 每次触发刷新,`s@Lt` 后缀 = RTG 会话 token)。**收银台源站常有源站级防火墙**(curl 超时 / fetch Failed / iframe 间歇成功) — 用页面内点击 Cashier 按钮由 CDK 生成 iframe,或接受间歇性访问。详情见 references/rtg-login-and-cashier.md。
8. **源站绕过** — 子域枚举找非 CF IP(常见 `m.` / `api.` / `cdk.`);直接 `http://<ip>/` + `Host: <子域>` 测试;IIS 响应(Server: Microsoft-IIS) = 源站确认;HTTPS 443 常被防火墙限制只放行 Cloudflare。
9. **IIS/ASP.NET 攻击面** — 测 `/elmah.axd` `/trace.axd`(500/301 而非 404 = handler 存在)、`/web.config`(403 = IIS 正常)、`/iisstart.htm`(200 = 默认站);ViewState 检查(`__VIEWSTATE` 在页面中)。
10. **CSP 泄露子域矩阵** — 响应头 `content-security-policy` 的 `frame-ancestors`/`frame-src` 常泄露全部游戏子域(`play.<d>`、`m.<d>:2750` 等),全部列入资产表。
11. **WAF 识别** — 主页返回 403 "Malware detected" 类页面 = WAF 行为检测;此时 `/login` 等白名单路径可能仍通,关联子域(cdk 等)常无 WAF。
12. **MGS/Gambit 平台探测** — HTML `data-js-vars` Base64(UTF-16LE)解码出 casinoLoginUrl/mgsId/apiDomain;casinoLoginUrl 指向 `*.gameassists.co.uk/gambit/` 即 MGS Gambit;加载 SPA 需 `deviceinfo` 参数且必须是 **JSON**(字符串会报 `'D' is an invalid start of a value`);`/gambit/api/*`(register/authenticate/player/state)POST 返回 415 = 端点存在但需正确 Content-Type/格式。细节见 references/gambit-mgs-platform.md。
13. **报告** — 批量报告按站点表格汇总 + 高危发现详述 + 盈利性分析(资金账号/撞库/支付欺诈);复制到桌面。

