# gambling-family-router 全文 第 4/4 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## References

- `references/rtg-fairgo-case.md` — FairGo 案例:RTG LobbyCore 架构、CDK.js 方法清单、SignalR 协议细节、源站发现(190.4.90.11 IIS)
- `references/rtg-login-and-cashier.md` — **RTG 登录绕过 + 收银台数据面:CDK.logIn 10 参数高层 API 绕过 ProduceSessionID、登录后 GetPlayerBalances/GetAccountInfo(密码哈希)/GetCashierSettings(RTGPID+HashedPassword+CashierSessionID)/GetAvailableCouponsInfo 全通、Router.ashx 收银台入口、源站防火墙限制**
- `references/fairgo-signup-bff-case.md` — FairGo 注册体系:signup 子域、BFF API、错误驱动字段枚举、预检接口、PhoneNumber 校验坑
- `references/casino-batch-10-sites.md` — 10 站点批量侦察结果:各站技术栈/保护/WAF 行为/分级
- `references/m9600-wasm-ws-protocol.md` — m9600 二进制 WS 协议完整逆向:wasm-in-Node 驱动、帧格式 dump、9999 拒绝分析、握手方向
- `references/m9600-rank-leak-credential-stuffing.md` — **m9600 后续突破:msgCb 返回 true 修复 1006 断连、排行榜接口(2544/2714)泄露 1454 账号、撞库工作流(123456 命中)、登录绕过全失败、管理端挖掘结论、客服系统 AES API**
- `references/gambit-mgs-platform.md` — MGS/Gambit 平台(luxury.casino):data-js-vars Base64(UTF-16LE)解码、BFF /settings 泄露、deviceinfo JSON 坑、/gambit/api 415 面、appSettings 全家族、UCP 401 鸡生蛋、launch 406 DTO 泄露
- `references/slotswin-api-enum-case.md` — slotswin 无鉴权 API 枚举:fetch() 提取站点专属 API 前缀(/slotswin-api/)、POST+JSON 绕过 SPA 兜底、SUCCESS/INVALID 用户名与邮箱枚举器、**get-player-subscriptions 完整邮箱 PII 泄露、GetOutBonusForPlayer/RedeemCoupon 现金返还兑换链、充提/余额篡改面四步定位法**
- `references/aq777-wps-rsa-des-case.md` — **AQ777(/wps/* REST 加密平台,完整打通):EdgeOne 567 挑战绕过(Python urllib)、真实 merchantCode 来源、RSA little-endian 复刻代码、DES-ECB(非 CBC!动态解码确认)、loginDeviceId 生成、无验证码注册+geetest 任意值绕过登录+用户枚举、数据面接口清单、IDOR 阴性结论、47 域名/配置/客服链接泄露、APK 硬编码 Hipush Swagger 公开、decryption.err→geetest_captcha_err 诊断字典**
- `references/ayx-nextjs-xapi-platform.md` — **AYX/c7 爱游戏体育(Next.js SPA + X-API-* 自定义头平台,2026-08):TG bot 目标链识别、xklink.js 域名矩阵、__NEXT_DATA__ preInfo 泄露、X-API-CLIENT/VERSION/SITE/UUID/XXX 请求头体系(X-API-SITE:1001 是"平台类型错误"的钥匙,签名填 test 也通)、sec 密钥对、注册/登录/支付/银行卡端点族、Next.js catch-all 200HTML vs 404JSON 判断法**
- `references/phpwind-yipay-bifa-case.md` — **PHPWind 7.3.2 落地页 + 彩虹易支付(bifa 必发系镜像站群,2026-08):c7a50_ cookie 指纹、注册零防护(regreason 坑)、pay3.php 金额映射(tid/pid 费率档)、submit.php 错误码字典→pid 商户池枚举、彩虹易签名算法变体(弱密钥阴性结论)、支付平台后台 ddddocr 验证码+403 语义浏览器弹窗判别法、PHPSESSID 跨会话一致性、PHPWind 加固面(admin.php 删/注入补丁/发帖需验证)**
- `scripts/batch_recon.py` — 批量侦察脚本(10 站点 DNS/HTTP 头/指纹一轮出结果)
- `scripts/signalr_probe.py` — SignalR 2.x longPolling 探测脚本(negotiate→connect→send→poll)
- `scripts/cdp_wasm_driver.js` — CDP 驱动真实 Chrome 逆向 wasm 二进制 WS 平台(预注入绕过反自动化 + 强制激活后台 tab + 页面内 Writer/writeData 全套;改 URL/账号即用)
- `templates/emscripten-ws-driver.js` — Node 加载 emscripten wasm 网络库并驱动 C++ WebsocketClient 的通用模板(改 WS_URL/命令号即用)

---

<!-- 补充视角: white-label-pentest (兄弟技能库 2026-09-12) -->

---
name: white-label-pentest
description: Pentest white-label platforms (RTG casinos, SaaS tenants).
version: 1.0.0
author: SurveyEngine Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
    category: security
    related_skills: [web-pentest, gambling-platform-risk-control]
---

# White-label Platform Pentest

渗透"白标/多租户平台"的方法论:不研发自己的产品,而是聚合第三方能力(游戏厂商 API、AI 模型)做统一分发运营的平台。典型:RTG 白标赌场、包网平台、多租户 AI SaaS。核心特征:前端壳 + 独立平台子域(signup/cdk/api)+ 自定义租户头 + BFF 架构。

## When to Use

- 目标是赌场/博彩/游戏平台(找 RTG、LobbyCore、CDK、SignalR 特征)
- 目标是多租户 SaaS(前端有 Custom-Origin/租户标识头、注册即入企)
- 目标是"聚合类"平台(游戏厂商 API / AI 能力中心 / 广告联盟)
- 注册流程异常复杂(多步表单)或登录被 WAF/验证码挡住时

## Prerequisites

- 授权目标(CTF/学习/审计)
- curl + python + 浏览器(headless 或 desktop)
- 注意本机代理/TUN 对端口扫描的干扰(全端口 OPEN 假象)

## 核心方法论

### 1. 识别白标平台架构

```
前端 SPA(Vue/Next/React) → 平台子域矩阵 → 后端 API + 实时通道(SignalR)
signup.xxx.com(BFF 注册)  cdk/play.xxx.com(游戏/核心)  api.xxx.com
```

- 抓主页 JS 里的 baseURL/环境变量/子域(CSP 头也泄露子域)
- 找注册/登录跳转子域(`/signup` 302 → signup.xxx.com)
- 常见白标商:RTG(RealTime Gaming, LobbyCore)、Softech、包网(见 gambling-platform-risk-control)
- 平台 CDN 常暴露版本号(如 LobbyCore 26.07.0.26.7.0.11)

### 2. 注册流程攻破(核心入口)

- 注册 API 常走 BFF 路径:`/bff/api/auth/signup`(前端 `rootUrl` 配置在 JS 里)
- **错误驱动字段枚举**:发空/部分 body,服务端返回完整必填字段清单 → 逐个补齐
- **逆向前端 JS 找提交格式**:搜索表单提交函数,看字段映射(如 `normalizePhoneNumber` 把号码变 `00`+国家码+本地号)
- 常见校验陷阱:3 字母 ISO 国家码、E.164/00 前缀手机号、UserAgent 必填
- 注册成功关注响应:`providerSignInToken`/`providerSignInUrl`(自动登录 token,免密登录 URL)
- KYC 去重(同名+生日)→ 错误消息可能泄露已有用户名+邮箱(**用户枚举**)

### 3. SignalR 2.x 实时 API(ASP.NET 平台)

- 端点:`/signalr/negotiate` → 拿 ConnectionToken/ConnectionId
- 流程:`negotiate → connect → send(form-urlencoded data) → poll`
- hub 方法清单在核心 JS 里(SDK 里 `*HubMethods = Utilities.mapArray([...])`)
- 浏览器里用 `CDK.invokeHubMethod(hubObject, method, args...)`(第一参是 hub 对象)
- 公开方法(奖池/菜单/中奖者)通常无鉴权可调;玩家方法(余额/历史)需会话
- 平台 bug 可能保护数据(如 ProduceSessionID 反射错误挂掉所有会话方法)

### 4. 源站发现(绕过 Cloudflare)

- 找非 CF 的子域 DNS(m.xxx.com → 哥斯达黎加/直连 IP)
- 源站直连:curl 源站 IP + `Host: 子域` 头 → 200 = 绕过 WAF
- HTTPS 443 常被防火墙挡(仅 CF 可达),HTTP 80 可直连

### 5. 常见白标平台漏洞清单

- 注册无验证码/无邮箱验证/无限速 → 批量注册
- 验证码字段传空串绕过(服务端不校验)
- 弱口令(联系手机号 + 123456)
- 对象存储签名接口(Policy 无 Content-Type 限制)→ 任意文件上传 + 存储型 XSS
- 开放 API 文档接口(getApiDoc)→ 完整能力清单
- 应用密钥明文返回(app_secret)
- 用户枚举(注册接口"账号已存在"/KYC Welcome back)

## Pitfalls

- **手机号格式是最大坑**:前端可能用 `00`+国家码+本地号(libphonenumber 兼容),直接传 E.164 会失败
- 字段名大小写敏感:`CountryCode`(后端扁平)vs `countryCode`(前端嵌套)— 以服务端错误提示为准
- 浏览器无头环境 Angular/React 表单 JS 赋值不生效 → 用真实键盘输入或直接调 API
- SignalR send 用 **form-urlencoded**(`data=URL编码JSON`),不是 JSON body
- 端口扫描被 TUN/代理污染时,以 HTTP 层行为为准
- 平台"损坏的 key"(anon key 截断为占位符)= 注册/登录功能整体不可用,别浪费时间绕验证码

## Verification

- [ ] 完成注册 API 调用链(字段全齐,拿到 userId/状态)
- [ ] 拿到至少一个无鉴权可调的平台方法并返回数据
- [ ] 源站绕过验证(Host 头直连非 CF IP)
- [ ] 记录 KYC/枚举/密钥泄露等附加发现

## References

- `references/rtg-casino-platform.md` — RTG 赌场白标平台(fairgo 案例:架构/注册字段/SignalR/源站)
- `references/saas-tenant-platform.md` — 多租户 AI SaaS 白标(umi6 案例:Custom-Origin/验证码绕过/OSS 上传)
- `scripts/signalr_probe.py` — SignalR 2.x longPolling 探测脚本

