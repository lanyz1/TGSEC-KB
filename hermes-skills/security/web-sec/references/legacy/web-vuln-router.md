<!-- archived from /root/.hermes/skills/security/web-vuln-router/SKILL.md on 2026-10-21 -->

---
name: web-vuln-router
description: >-
  通用 Web 漏洞利用场景分流。已确认具体漏洞类型时，根据类型找到对应的专用 Skill。
  用户提到 XSS、SQLi、SSTI、SSRF、LFI、CORS、CSRF、HTTP走私、缓存投毒、
  原型链污染、NoSQL注入、竞态、质量分配、命令注入、Java反序列化、IDOR、GraphQL、
  JWT、CRLF、XXE、API参数挖掘、2FA绕过、PHP调试泄露、Werkzeug、Django DEBUG、开放重定向、缓存欺骗、
  SSI、ESI、WebDAV、OAuth redirect_uri、Next.js Server Actions、ASP.NET ViewState、gRPC 反射 时使用本路由。
---

> 归档卡：原目录 `/root/.hermes/skills/security/web-vuln-router`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/web-vuln-router/…')`，不要相对 `references/legacy/` 解析。

# 通用 Web 漏洞场景分流（Router）

**适用时机**：已通过 `strike_probe` / `core_web_surface_probe` 或手工探测确认漏洞类型，需要进入利用阶段。无专用栈先跑 `strike_probe.py`。总控闸门先读 `pentest-methodology`。

## 判定原则（注入/架构共用）

1. **先无害信号再武器化**：回显标记 / 延时 / OOB 回连成立后，才进 dump、写马、反弹。
2. **负对照必做**：时间盲注必须带零延时孪生 payload；布尔盲注必须有 `AND 1=1` / `AND 1=2` 成对；排除网络抖动。
3. **版本 ≠ 漏洞**：组件版本命中 CVE 只是线索，必须证明 sink 可达。
4. **sqlmap 不是首轮扫描器**：手工确认注入点后再 `sqlmap_kit.py ladder`。

## 漏洞 → Skill 速查表

| 漏洞类型 | 触发关键词 | 走哪张卡 |
|----------|-----------|----------|
| XSS（Stored/Reflected/DOM） | XSS、存储型、DOM注入、CSP绕过 | `xss-exploit` |
| SQL 注入 | SQLi、注入、盲注、sqlmap | `sqli-manual` → `sqlmap-tamper-kit` |
| 登录旁路 / 认证绕过 | admin'--、登录 SQLi、OR 1=1、authentication bypass | `authbypass-authentication-flaws`（网狐走 `whgame-tp5-login-sqli`；弱口走 `auth-brute`） |
| 模板注入（SSTI） | SSTI、Jinja2、Twig、FreeMarker | `ssti-exploit` · `tpl_inject_probe.py ssti` · `rce_forge.py shoot --family ssti-jinja` · `测绘引擎SSTI作业手法.md` |
| SSRF + 内网探测 | SSRF、服务端请求伪造、内网代理 | `ssrf-internal-pivot`（→ `ssrf-internal-pivoting`）<br>Echo 框架→ `echo-ssrf-internal-scanning` |
| 路径穿越 / LFI | LFI、路径穿越、`/etc/passwd`、PHP wrapper | `lfi-rfi-exploit` · `tpl_inject_probe.py lfi` · `测绘引擎LFI作业手法.md` |
| 文件上传 + WebShell | 文件上传、绕类型检测、落点 | `file-upload-webshell` |
| CORS 错配 | CORS、跨域、`Allow-Origin`、凭据反射 | `cors-exploitation` · `cors_csrf_probe.py cors` · `测绘引擎CORS作业手法.md` |
| CSRF | CSRF、SameSite 缺失、表单重放 | `csrf-testing` · `cors_csrf_probe.py csrf` · `测绘引擎CSRF作业手法.md` |
| HTTP 请求走私 | HTTP Smuggling、TE-CL、CL-CL | `http-request-smuggling` |
| 缓存投毒 / 欺骗 | Cache Poisoning、`X-Cache:HIT`、`/account/x.css` | `web-cache-poisoning` · `cache_poison_probe.py` · `测绘引擎缓存投毒作业手法.md`（旧名 `web-cache-deception` 已并入） |
| SSI / ESI | `.shtml`、`<!--#echo`、`esi:include` | `ssi-esi-injection` · `ssi_esi_probe.py` · `测绘引擎SSI-ESI作业手法.md`（不是 SSTI） |
| HTTP 方法 / WebDAV | OPTIONS、TRACE、PUT、PROPFIND | `http-method-webdav` · `http_method_surface_probe.py`（ownCloud 走专卡） |
| OAuth / OIDC 授权码 | `redirect_uri`、`openid-configuration`、`response_type=code` | `oauth-oidc-flow` · `oauth_oidc_surface_probe.py`；`grant_type=password` → `oauth2-password-grant-login-testing` |
| 原型链污染 | `__proto__`、prototype pollution、merge | `prototype-pollution` · `param_abuse_probe.py proto` · `测绘引擎原型链污染作业手法.md` |
| NoSQL 注入 | MongoDB、Elasticsearch、NoSQL | `nosql-injection` · `param_abuse_probe.py nosql` · `测绘引擎NoSQL作业手法.md` |
| 竞态条件 | Race Condition、并发扣款、Turbo Intruder | `race-condition` · `race_probe.py` · `测绘引擎竞态作业手法.md` |
| 质量分配 | Mass Assignment、批量参数绑定 | `mass-assignment` · `param_abuse_probe.py mass` · `测绘引擎批量赋值作业手法.md` |
| 命令注入 | RCE、命令注入、`; id`、shell exec | `command-injection-testing` · `tpl_inject_probe.py cmdi` · `rce_forge.py shoot --family cmdi-unix` · `测绘引擎命令注入作业手法.md` |
| 抢 RCE / getshell（未认形） | 抢rce、getshell、RCE 百科、拿 shell | **`rce-encyclopedia`** · `rce_family_route.py --signal` → 再进上表专卡。写文件/DNSlog ≠ GetShell |
| Java 反序列化 | ysoserial、ObjectInputStream、反序列化 | `java-deserialization` |
| IDOR / BOLA | 越权访问对象、IDOR、BOLA、水平越权 | `idor-bola-chain`（注册越权→`register-bypass-idor`） |
| GraphQL | 内省、`__schema`、GraphQL 越权 | `graphql-pentest` · `gql_authz_probe.py` · `测绘引擎GraphQL作业手法.md` |
| JWT 弱密钥 | alg:none、弱 JWT、空签名 | `jwt-bypass-pentest` · `jwt_forge_probe.py` · `测绘引擎JWT作业手法.md` |
| CRLF 注入 | CRLF、Header 注入、Response Splitting | `crlf-injection` · `param_abuse_probe.py crlf` · `测绘引擎CRLF作业手法.md` |
| XXE | 外部实体、XXE、SSRF via XML | `xxe-injection-testing` · `tpl_inject_probe.py xxe` · `测绘引擎XXE作业手法.md` |
| API 参数挖掘 | 隐藏字段、参数爆破、API Fuzzing | `api-param-name-discovery` |
| API 设计越权 | REST 越权、API 审计 | `api-security` · `api-security-patterns` |
| 2FA / OTP 绕过 | 2FA 绕过、验证码跳过、步骤跳过 | `2fa-bypass` |
| PHP 调试泄露 | phpinfo()、框架调试页、debug=true | `php-debug-mode-exploitation` + `php-framework-debug-leak-pentest` |
| Python Debug / Werkzeug PIN / Django DEBUG | Werkzeug、`/console?__debugger__`、Django traceback | `core-web-vuln-kit` 指纹 → `ssti-exploit` 算 PIN；Django SECRET_KEY≠pickle RCE |
| 开放重定向 | returnUrl、next=、重定向链 | `open-redirect-chain` · `open_redirect_surface_probe.py` · `测绘引擎开放重定向作业手法.md` |
| PHP 反序列化 | phar://、unserialize、PHP 链 | Playbook `PHP反序列化作业手法.md` |
| 变体对照 / same-body / 过滤器漏过 | http_probe_batch、近成功 | `agent-evidence-gate` · `http_probe_batch.py` |
| highlight 源码 / 着色 PHP | source_extract | `agent-evidence-gate` · `source_extract.py` |
| 401 / 403 拒访 | X-Original-URL、方法覆盖、管理后台 403 | `401-403-bypass-techniques` |
| 点击劫持 | iframe、frame-ancestors | `clickjacking` |
| Host 头 | 重置链接 Host、缓存 Host | `http-host-header-attacks` |
| PHP 弱比较 | `==`、0e hash、type juggling | `type-juggling` · `param_abuse_probe.py juggl` · `测绘引擎类型混淆作业手法.md` |
| JNDI / Log4j | `${jndi:` | `jndi-injection` |
| Ghost Bits / Java 收窄 | Unicode 绕 WAF、char→byte | `ghost-bits-cast-attack` |
| LDAP / XPath / HPP / CSV 公式 | LDAP 注入、参数污染 | `ldap-injection-testing` · `xpath-injection-testing` · `http-parameter-pollution` · `csv-formula-injection` |
| 实战包其它洞 | 只丢了卡名 | `shizhan-pack-router` · `shizhan_pack_route.py --name` |
| Next.js 通用猎面 | `x-nextjs`、`/_next/image`、`Next-Action`、ISR/RSC | NEXTAUTH/Kyber → `tg-bot-nextauth-takeover`；其它 → `nextjs-ssr-hunt` · `nextjs_surface_probe.py` |
| ASP.NET ViewState / Telerik | `__VIEWSTATE`、`.aspx`、`elmah.axd` | SharePoint → `sharepoint-unauth-rce`；其它 → `aspnet-viewstate-hunt` · `aspnet_surface_probe.py` |
| gRPC 反射 / 后端无鉴权 | `:50051`、`grpc-status`、grpcurl | `grpc-reflection-hunt` · `grpc_surface_probe.py`；DoS 禁止 |
| 企业 SSL VPN 门户 | `+CSCOE+`、GlobalProtect、Ivanti、NetScaler | FortiOS → FortiOS Playbook；矩阵 → `sslvpn-perimeter-fingerprint`（网站案默认降权） |

单次 payload 无回显或远端 same-body **不是** NO_PATH。源码 sink、表单/参数、对照 DIFF 还在就继续。

## 不要做

- 先猜漏洞类型再试工具；用 `core_web_surface_probe` 先探，再进本路由
- 把各卡混用（SQLi 工具打 SSTI，SSRF 工具打 CORS 等）
- 高信号未耗尽就写结案（走 `evidence_gate.py`）

## 真源

- 总控：`.cursor/skills/pentest-methodology`
- 手法：`docs/playbooks/核心Web漏洞面作业手法.md`
- 工具：`python3 tools/ops/core_web_surface_probe.py --help`
- 单点：`python3 tools/ops/tpl_inject_probe.py --help`
- 打穿：`python3 tools/ops/rce_forge.py --help`
- 本卡是入口路由，利用细节在各子 Skill 与对应 Playbook。
- 旧名 `injection-checking` / `file-access-vuln` 已并入本卡。
