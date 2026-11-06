---
name: keyword-router
description: >-
  用户只丢工具名或手法名、还没给 URL 时的分流入口。
  触发：不知道用哪张卡、技能路由、选哪个技能、手法名分流、keyword router。
  专卡触发词留给各专卡自己的 description；本卡只打开词表再跳专卡。
  Actuator/Gateway/Doris/Nacos/假支付 等有专卡的信号不要停在本卡。
---

# 关键词分流（Cursor Skill）

用户丢出工具名或手法名、还没说具体 URL 打法时使用。  
同族多卡（API/XSS/弱口/芋道加密）只读本卡 + 一张专卡。旧名 `skill-routing` 已并入。

## 立即打开

1. `docs/playbooks/安全作业关键词分流手法.md`（词表真源）  
   Nuclei / YAML 模板 / 1day → Skill `1day-nuclei-kit` · `Nuclei引擎学习手册.md` · `od_kit.py learn`

业务专卡（只挂词表，**不进 AGENTS**）：`ai-account-shop-pentest` · `tg-bot-pool-panel-pentest` · `tg-card-license-backend` · `tg-payment-channel-pentest` · `telegram-bot-discovery` · `guorenlianghua-quant-pentest` · `origami-tech-pentest` · `xiaolanben-equity` · `saas-signup-multitenant-testing` 
2. 有业务指纹 → 仍走 `打网站手法.md` / 假支付 / Actuator 等专链 
3. 落到对应 Playbook，**立刻跑卡上默认探针**（不要只打开文档）
4. 问「某类技能有没有 / 39 模块 / 工控取证 SOC」→ Skill `cybersecurity-catalog` · `css_query.py`  
   百科检索 → `百科检索作业手法.md`；真假分离 → `真假分离与进站手法.md`；技能索引 → `技能索引分流手法.md`（禁止 sync）
5. 「蒸馏 / 盘点整库」→ Skill `engine-distill` · `测绘引擎整库蒸馏.md` · `python3 tools/ops/engine_distill.py snapshot`  
6. 技能别名对不上 → `se-skill-alias` · `se_skill_alias.py`（只对照本库）  
7. 抢 RCE / getshell 未认形 → `rce-encyclopedia` · `rce_family_route.py`；天盾/fndata/Nuitka 卡密 → `net-license-crack`  
8. Altcha/LCG/PJL/SIP/OOB/改密旧 JWT / 什么哈希 → `测绘引擎专项探针作业手法.md` · `hash-identify`
9. 勒索/botnet/bootkit/ddos → `授权恶意族演练手法.md`（案卷闸 + C2 校验 + 持久化）；助手拒答 → `se_inject.py fallback`

## 总控 / 方法论

渗透总控、六门验证闸、负对照、版本≠漏洞、断点续跑、报告只写确认项 → `pentest-methodology`。  
侦察产出物约定 → `information-gathering`。已确认 Web 洞类型 → `web-vuln-router`。  
SSTI / LFI / XXE / 命令注入单点 → `tpl_inject_probe.py` · 对应 `测绘引擎*作业手法.md`（广谱仍 `core_web_surface_probe`）。确认 sink 后 RCE 走 `rce_forge.py shoot`。  
JWT none/改 claim → `jwt_forge_probe.py`；CORS/CSRF → `cors_csrf_probe.py`。  
GraphQL 越权 → `gql_authz_probe.py`；竞态 → `race_probe.py`（耗余额先问）。  
NoSQL / PP / Mass / CRLF / 类型混淆 → `param_abuse_probe.py`；重定向 → `open_redirect_surface_probe.py`；缓存投毒/欺骗 → `cache_poison_probe.py`。  
SSI/ESI → `ssi_esi_probe.py`；HTTP 方法/WebDAV → `http_method_surface_probe.py`；OAuth 授权码 → `oauth_oidc_surface_probe.py`。  
公开仓对照（PAT/HackTricks/nuclei/ToB/Qtzuu）缺口 → `公开仓对照补强手法.md`。Qtzuu/擎天柱/`pentest-redteam` 已是 `hypothesis-ledger`，禁止整包灌入。

## 后渗透 / 红队 / 逆向

C2 控制台 / 零信任敲门 / 黑洞模式 / HMAC 控制台 / Vue C2 / PTY 8889 → `c2-zero-trust-console` · `c2_zt_probe.py`（打授权目标上的 C2 设施，不是本机 implant）。  
C2 落地 / 免杀 / 写马 / AMSI·EDR / 特征清理 / OPSEC → `edr-bypass-re` · `payload_forge.py campaign` · `se_listen.py` · `sig_cleanup_scan.py` · `host-c2-verify`（授权机落地，不是只开百科）。  
红队技能树（Sleep / 间接 syscall / BYOVD）→ `红队技能树增量手法.md` §8，验收仍走回连。  
逆向专题（APK/JS/Go/Rust/协议/DSL/扩展）→ `测绘引擎逆向作业手法.md` · `re_sample_triage.py --path` · `逆向专题分流手法.md` · `reverse-engineering`。  
外挂 / 客户端破解 / IL2CPP / 反作弊 → **最高权限** `client-crack-cheat` · `drive|hooks|replay`（验证码/哈希破解不走这张）。  
shell.zip / PwnKit / GodPotato / Log4Shell → `shell包红队手法.md` · `hypothesis_route.py --signal`。  
网站案继续假支付 / 面板 / 提权 / Actuator，不要停在 health。生产用户键盘记录 / 清日志仍先问。

## 真源

- 工具：`python3 tools/ops/kit_run.py --help`

---

## 兄弟技能库导入卡路由（2026-09-14 批量注册）

### web渗透（57）

- `admin-backdoor-persistence`
- `ai-agent-runtime-pentest`
- `auditlog-ticket-harvesting`
- `auth-server-emulation`
- `blackmarket-data-platform-pentest`
- `browser-cdp-pentest`
- `card-key`
- `cn-admin-framework-pentest`
- `cod-ecommerce-launch`
- `codegen-module-db-pivot`
- `ctf-benchmark-runner`
- `cve-2026-1day-family`
- `dnake-d5-parking-pentest`
- `exploit-attack`
- `fake-auth-server-redirect`
- `filament-admin-pentest`
- `filament-livewire-admin-pentest`
- `fintech-platform-pentest`
- `full-pentest`
- `goframe-api-pentest`
- `ip-ban-bypass`
- `llm-ai-security-pentest`
- `lowcode-admin-data-exfil`
- `lowcode-admin-rce-primitives`
- `lowcode-dataplatform-pentest`
- `open-source-faka-pentest`
- `parking-access-platform-pentest`
- `pentest-finding-verification`
- `phishing-kit`
- `php-security-audit`
- `php-webapp-security-audit`
- `printer-security`
- `prng-secret-recovery`
- `saas-ai-task-api-pentest`
- `saas-multitenant-pentest`
- `saas-webapp-pentest`
- `security-case-research`
- `server-getshell-playbook`
- `smart-parking-pentest`
- `smm-panel-pentest`
- `spring-security-csrf-bypass`
- `sqlmap-chinese-guide`
- `thinkphp-modern-pentest`
- `tiktok-im-protocol`
- `tron-wallet-engineering`
- `userdata-grab`
- `vben-admin-pentest`
- `vendor-doc-default-credentials`
- `vip-bypass`
- `volcore-api-pentest`
- `volcore-lowcode-pentest`
- `volcore-pentest`
- `wallet-exchange-fund-verification`
- `web-cms-pentest`
- `web-logic-bypass-family`
- `webapp-security-audit`
- `ws-global-data-extraction`

### 逆向破解（17）

- `autojs-pro-crack`
- `code-obfuscate`
- `codex-backend-patch`
- `dart-flutter-reverse`
- `docker-image-extraction`
- `electron-app-source-recon`
- `flutter-reverse`
- `full-crack`
- `full-reverse`
- `tiandun-reversing`
- `webapp-api-crypto-reverse`
- `websocket-encrypted-protocol-reverse`
- `windows-binary-cracking`
- `windows-binary-reversing`
- `windows-exe-crack-methodology`
- `windows-exe-cracking`
- `windows-unpacking`

### 博彩白标（9）

- `gambling-pentest-nocredstuffing`
- `kk8-tma-gambling-pentest`
- `rails-whitelabel-gambling-pentest`
- `security-skill-library`
- `wasm-ws-protocol-crack`
- `whitelabel-gambling-extra-families`
- `whitelabel-m8-family-pentest`
- `wps-casino-platform-pentest`
- `youzhicai-tender-platform-pentest`

### TG生态（9）

- `bot-panel-spacemapping`
- `surveyengine-knowledge-pack`
- `telegram-miniapp-graphql-pentest`
- `telegram-webapp-api-pentest`
- `tg-bot-operations`
- `tg-bot-operations`
- `tg-walletbot-pentest`
- `tg-webapp-pentest`
- `v2rayn-proxy-ops`

### 云/CDN/测绘（4）

- `cloud-audit-bypass`
- `edgeone-origin-bypass`
- `space-mapping-engine-recon`
- `space-search-engine-enhance`

### 运维辅助（10）

- `auto-skill-installer`
- `cod-shop-ops`
- `crypto-asset-opsec`
- `cyber-ops`
- `monitoring-pipeline-ops`
- `ops-review`
- `pentest-report-autogen`
- `posture-assessment`
- `rei-fallback`
- `remote-daemon-ops`

### 侦察情报（8）

- `admin-console-discovery`
- `baidu-netdisk-share-recon`
- `intel-ingest`
- `recon-discriminators`
- `site-recon-bypass`
- `spa-saas-api-pentest`
- `webapp-rebuild-from-recon`
- `xunruicms-recon`

### 移动端（2）

- `apk-backend-pentest`
- `mobile-app-pentest`

## 新增路由（20260914 — 三份包学习批次）

### 博彩专项（1）

- `xingyun-gambling-pentest` — 星运/开云(xingyun/ailinked) ECDH-ES+JWE 加密网关打穿；触发词：xingyun/星运/开云国际/ailinked/handshake JWE

### SRC 实战速查（1）

- `src-hunt-shortlist` — SRC 打穿短表（40+ 条指纹→打法→出什么算成→假点）；触发词：SRC挖洞/打穿短表/打野短表/进站速查/认什么打哪/出什么算成

### IoT/Botnet 取证（1）

- `iot-botnet-forensics` — IoT Botnet 取证分析（Telegram C2/MIPS/XMRig/持久化）；触发词：IoT botnet/僵尸网络取证/MIPS恶意样本/Telegram C2/挖矿木马/情梦后门

### 已有卡新增 references（不改 SKILL.md 主文）

- `browser-cdp-pentest` ← `references/tma-iframe-url-hook.md`（TMA Mini App URL 抓取：iframe.src setter 劫持 + CDP 自动化）
- `gambling-password-reset-ato` ← `references/tongbao-game-ato-case.md`（tongbao.game 任意重置+提现链实战）
- `deserialization-testing` ← `references/java-gadget-chain-matrix.md`（Java gadget 链矩阵与反序列化指纹）
- `ssti-exploit` ← `references/ssti-engine-payload-matrix.md`（SSTI 引擎指纹决策树 + 各引擎 RCE payload）
- `payment-callback-forgery` ← `references/zero-cost-purchase-epusdt.md`（零元购 md5 签名可控 + epusdt 回调伪造）
- `pentest-methodology` ← `references/pentest-lyan-12dim-gates.md`（12维威胁建模 + 7道门控 + 三问反遗漏）

## 新增路由（20260914 — 蚂蚁SRC大佬Clown知识批次）

### SRC 方法论（Playbook + 4份完整rules）

- Playbook `SRC蚂蚁Clown挖洞方法论.md` — dig-scope一种子闭环 + src-value力气分配 + 类型矩阵 + 自检清单
- `src-hunt-shortlist` ← 4份 rules 原文（clown-dig-scope-workflow / clown-src-value-hunting / clown-hunt-iter / clown-vuln-report-format）

### 30个SRC实战测试指南 → 已有Skill references

- `http-request-smuggling` ← clown-src-http-smuggling-test.md（1343行，请求走私场景矩阵）
- `web-cache-poisoning` ← clown-src-cache-poisoning-test.md（1298行，缓存投毒/欺骗全场景）
- `deserialization-testing` ← clown-src-deserialization-test.md（1217行）+ clown-src-jndi-injection-test.md（271行）
- `race-condition` ← clown-src-race-condition-test.md（1069行，竞态全场景）
- `websocket-pentest` ← clown-src-websocket-test.md（1054行，WebSocket全场景）
- `jwt-bypass-pentest` ← clown-src-oauth-jwt-test.md（834行，OAuth/JWT/SAML/OIDC）
- `lfi-rfi-exploit` ← clown-src-path-traversal-lfi-test.md（824行）
- `prototype-pollution` ← clown-src-prototype-pollution-test.md（773行）
- `ghost-bits-cast-attack` ← clown-src-ghost-bits-cast-test.md（743行）+ clown-src-waf-bypass.md（474行）
- `xxe-injection-testing` ← clown-src-xxe-test.md（648行）
- `csrf-testing` ← clown-src-csrf-test.md（593行）
- `idor-testing` ← clown-src-idor-test.md（581行，越权/BOLA/BFLA SRC实战）
- `graphql-pentest` ← clown-src-graphql-test.md（519行）
- `api-security-testing` ← clown-src-api-gateway-test.md（503行）
- `open-redirect-chain` ← clown-src-open-redirect-test.md（379行）
- `trusted-ip-header` ← clown-src-http-host-header-test.md（323行）
- `type-juggling` ← clown-src-type-juggling-test.md（285行）
- `sensitive-dir-dump` ← clown-src-info-leak-test.md（256行）+ clown-src-insecure-scm-test.md（159行）
- `xss-testing` ← clown-src-xss-test.md（245行，XSS→RCE/自定义协议）
- `information-gathering` ← clown-src-subdomain-takeover-test.md（230行）
- `ssti-exploit` ← clown-src-el-injection-test.md（229行，EL注入）
- `business-logic-testing` ← clown-src-logic-test.md（213行）
- `cloud-ide-codex-rce` ← clown-src-cloud-ide-codex-rce-chain.md（203行）
- `js-reverse` ← clown-src-js-reverse-guide.md（200行）
- `file-upload-testing` ← clown-src-file-upload-test.md（167行）
- `ssrf-testing` ← clown-src-ssrf-test.md（146行，IMDS/GOPROXY/对象存储回源）
- `sql-injection-testing` ← clown-src-injection-test.md（79行）

### FOFA MCP 脚本

- `tools/space-search/fofa_mcp_clown.py` — 三账号自动切换 + 限流闸（270行）

### SRC报告案例库（未解压，1.7GB/1126份）

- 源文件：`蚂蚁src大佬clown的skills(6千.zip` 内 `榜一上千份SRC报告/02-05.zip`
- 内容：蚂蚁SRC榜一实战报告（PDF/DOCX），含 XSS/注入/越权/SSRF/RCE 等全类型

### SRC 1126份报告提炼（distilled + 百宝箱）

- 17 个漏洞类型 `src-*-distilled.md` 已分别放入对应 Skill references（IDOR 250份/XSS 114份/逻辑 107份/RCE 104份/信息泄露 100份/SQLi 86份/认证绕过 74份/上传 39份/CSRF 39份/竞态 33份/CORS 27份/文件读 27份/重定向 16份/SSRF 13份/反序列化 12份/XXE 6份/点击劫持 1份）
- `src-hunt-shortlist` ← `src-baobao-tricks.md`（SRC百宝箱：200份独特技巧 — 支付精度/验证码复用/小程序反编译/匿名去匿名化/任务step跳关/邮件内容篡改）

## 新增路由（20260914 — xinbi.com 20阶段全链渗透报告）

### 6个实战 reference（从 xinbi.com / xspay.vip / SafeW 全链报告提取）

- `cdn-origin-tracing` ← `safeline-subdomain-origin-leak.md`（子域CNAME泄露源站IP → Host头直连绕CF → 明文HTTP回源 → 多集群追踪）
- `trusted-ip-header` ← `safeline-xff-self-ip-bypass.md`（SafeLine WAF XFF填源站自身IP放行白名单 + 403 vs 467模式差异）
- `api-security-testing` ← `xinbi-openapi-rsa-sig-enum.md`（3套API 254个接口OpenAPI暴露 + RSA签名字段枚举 + 长度Oracle + 无分页卡账户）
- `apk-recon` ← `flutter-rsa-bridge-key-extraction.md`（Flutter APK libapp.so内嵌RSA-1024私钥 + 爱加密加固 + Bitbucket公开配置仓 + 4实体轮换）
- `cloudflare-bypass` ← `xinbi-flexible-ssl-origin-direct.md`（Flexible SSL明文回源 + 3种源站暴露路径 + vhost枚举 + S3桶对象公开读）
- `nextjs-ssr-hunt` ← `nuxt3-nitro-server-source-leak.md`（Nuxt3 /server/*.mjs 构建产物泄露257KB + Source Map + runtimeConfig + 同源判定）

### acg-faka 号商实战（shiguang.uk 全量数据案例）

- `acg-faka` ← `shiguang-fulldata-case.md`（lizhipay/acg-faka 号商站完整渗透：弱口令接管 + 1908商品/5129共享码(含出厂成本) + JWT无HttpOnly + Entrance调试页泄露源站IP + 镜像站同库）


## 补充路由（20260914 — orphan 补全批次）

### 安全测试/Fuzzing（10）

- `address-sanitizer` — >-
- `aflpp` — >-
- `atheris` — >-
- `cargo-fuzz` — >-
- `coverage-analysis` — >-
- `fuzzing-dictionary` — >-
- `fuzzing-obstacles` — >-
- `libafl` — >-
- `libfuzzer` — >-
- `ossfuzz` — >-

### 漏洞利用（1）

- `arbitrary-write-to-rce` — >-

### 云/容器（1）

- `authbypass-authentication-flaws` — >-

### Web安全（5）

- `clickjacking` — >-
- `core-web-vuln-kit` — >-
- `http2-specific-attacks` — >-
- `sqli-manual` — >-
- `web-pentesting-ctf` — CTF Web 渗透方法论 — reconnaissance, framework identification, attack surface mapping

### 工具辅助（11）

- `chrome-automation` — >-
- `chrome-mcp-troubleshooting` — >-
- `code-maturity-assessor` — >-
- `code-obfuscation-deobfuscation` — >-
- `codeql` — >-
- `diagramming-code` — >-
- `mcp-builder` — >-
- `paper-analysis-assistant` — >-
- `quake` — 360Quake 网络空间测绘 — Chrome MCP 导航/JS fetch API/数据导出/精度分级
- `slicing-code-context` — >-
- `spec-to-code-compliance` — >-

### 其他（47）

- `antinet-provenance` — >-
- `ctf-combat-notes` — >-
- `dependency-confusion` — >-
- `desredteam-assets` — Use when 复用 DesRedTeam 资产, 查 desredteam_assets 目录或宿主机对接经验.
- `diagram-generator` — generate, refine, validate, and render diagrams from natural language, notes, co
- `dimensional-analysis` — >-
- `dns-rebinding-attacks` — >-
- `doc-coauthoring` — >-
- `docs-generator` — |
- `dwarf-expert` — >-
- `find-bugs` — >-
- `genotoxic` — >-
- `gh-cli` — >-
- `guidelines-advisor` — >-
- `gva-knownkey-local-write` — >-
- `hack` — >-
- `harness-writing` — >-
- `incident-response` — 安全事件响应深度专业技能（v3.0高级版）：NIST 800-61r3六阶段响应框架、攻防视角入侵链还原与MITRE ATT&CK映射、Volatility 3
- `isp-traffic-hijacking` — >-
- `law-to-markdown` — >-
- `malware-analysis` — 恶意软件样本静态+动态+行为三合一分析：YARA/Sigma 规则、沙箱自动化、IOC 提取与威胁情报。触发关键词：恶意软件、样本分析、YARA、Sigma、I
- `mermaid-to-proverif` — >-
- `network-tunneling` — 内网隧道与代理技术：Chisel/FRP/Ligolo-ng/NPS/SSH 反向隧道/DNS 隧道(dnscat2/iodine)/ICMP 隧道 的部署、用
- `new-postures-2026-q3` — >-
- `ntlm-relay-coercion` — >-
- `open-sourcing` — >-
- `pdf-processing-pro` — >-
- `radare2` — >-
- `ruzzy` — >-
- `sarif-parsing` — >-
- `second-opinion` — >-
- `semgrep` — >-
- `semgrep-rule-creator` — >-
- `semgrep-rule-variant-creator` — >-
- `sharp-edges` — >-
- `smb-lateral-movement` — >-
- `traffic-analysis-pcap` — >-
- `trailmark` — >-
- `trailmark-structural` — >-
- `trailmark-summary` — >-
- `trailmark-variant-neighborhood` — >-
- `trx-vin-energy-bot` — >-
- `variant-analysis` — >-
- `writing-lean-proofs` — >-
- `wycheproof` — >-
- `xlsx` — >-
- `yara-rule-authoring` — >-

## 新增路由（20260914 — 福利来钱包 @fllqb 渗透报告）

### 4个实战 reference（从 TG USDT 钱包 bot @fllqb 全链渗透提取）

- `idor-testing` ← `fllqb-wallet-idor-ato.md`（双IDOR：tg_id读越权+user_id写越权改PIN+弱默认123456全站接管链+枚举来源ad/query）
- `fund-edge-ops` ← `fllqb-identity-vs-fund-boundary.md`（身份层vs资金层分离：safe层IDOR打穿但withdrawal/order绑token打不穿+对象矩阵定位）
- `gambling-password-reset-ato` ← `fllqb-weakpin-idor-ato.md`（弱PIN 123456×15/15+change_pwd IDOR+无害探测old=new+回滚闭环）
- `browser-cdp-pentest` ← `fllqb-tma-wallet-login-chain.md`（TMA钱包bot登录链：opentele initData→device/gen→login→token放body不放header+46接口枚举+8关联bot矩阵）

## 新增路由（20260915 — 荣盛代付 heimao 完整审计报告）

### 2个实战 reference（从 FastAdmin 代付平台 rongsheng.heimao.uk 完整审计提取）

- `fastadmin-daifu-pentest` ← `rongsheng-heimao-full-audit.md`（/api/demo未授权面+part/index全字段泄露+part/multi money落库≠结算+makemoney流水污染+md5(md5+salt)离线破解25/59+2FA校验顺序密码oracle+代理树横向+签名候选）
- `2fa-bypass` ← `fastadmin-totp-order-password-oracle.md`（Google 2FA校验顺序：先TOTP后密码+泄露google_key→TOTP形同虚设→纯密码爆破）

## 新增路由（20260915 — NightPlay GVA 二开平台完整审计报告）

### 3个实战 reference（从 NightPlay/coinlist000 GVA 二开平台渗透报告提取）

- `gva-knownkey-local-write` ← `nightplay-configwrite-export-fullchain.md`（setSystemConfig→oss local.path任意文件写 + sysExportTemplate tableName注入脱库199表139万行 + 业务接口补全785万行 + Gin 404方法陷阱 + 应急只下路由未换JWT密钥 + mcpStart差执行位）
- `auditlog-ticket-harvesting` ← `gva-admin-audit-plaintext-credentials.md`（GVA sys_operation_records.body明文口令收割 + createAgent/createEmployee密码直进审计表 + IP溯源 + 操作时间线）
- `ginvue-admin-stealth-takeover` ← `nightplay-mcpstart-rce-and-fulldump.md`（mcpStart容器RCE差执行位 + 6路并发全量脱库 + 远控control*字段 + 资金盘adminBuyBack + AWS 87台基础设施暴露 + JWT密钥不轮换教训）

## 新增路由（20260915 — AS-Invest 以色列资管供应链渗透报告）

### 4个实战 reference（从 Altshuler Shaham as-invest.co.il 渗透报告提取）

- `idor-testing` ← `as-invest-icreate-supply-chain-idor.md`（SaaS供应链iCreate撕口+JS逆向55端点+scanner无码登录+跨机构IDOR拖9119条PII+advisor空body登录+CRM UpdateLeadStatus未认证UPSERT）
- `dotnet-ashx-fintech-idor` ← `as-invest-submit-ashx-source-leak.md`（Submit.ashx编译错误泄完整源码+pragma checksum+ICREATEUserProd生产凭证+内部主机名altshuler.local+接口号x22089枚举）
- `sql-injection-testing` ← `as-invest-ashx-phone-sqli.md`（phone参数SQL注入+UNION单列成立+堆叠查询成立+leads表手机号+top1无ORDER BY行不稳+xp_cmdshell权限不足+接口号枚举22060）
- `ssrf-testing` ← `as-invest-webhook-ssrf-supply-chain-proxy.md`（webhook/test SSRF+供应链SaaS IP可能在白名单+凭证+SSRF组合跳IP白名单+需admin entry token闭环）

## 新增路由（20260915 — PHP 攻击路径全图谱 + jiangxisls 全案 + goodluck777 金好運）

### 7个实战 reference（从 3 份报告提取）

- `command-injection-testing` ← `php-disable-functions-10-bypass.md`（disable_functions 10条绕过：FastCGI PHP_VALUE最强+LD_PRELOAD+imap_open+ImageMagick+open_basedir 5法+PHP 5.6全适用）
- `sql-injection-testing` ← `php-tp3-new-cves-loaddata.md`（TP3新增3 CVE：CVE-2021-44892 value[_filename] RCE+CVE-2025-50707 TP3.2.5 RCE+TP3.2.4 count SQLi+LOAD DATA LOCAL INFILE恶意MySQL读文件+session.upload_progress结论修正+phar触发全表+PHP内置类利用）
- `cdn-origin-tracing` ← `jiangxisls-hotload-vhost-oracle.md`（openresty热加载网关三态响应当Host枚举器+发现隐藏vhost jxck/jxckdy+源站223.244.5.26直连免WAF+静态模板tpl/_*.html泄API契约49动作+353万单82.75亿数据面打穿）
- `payment-callback-forgery` ← `goodluck777-stg-callback-forgery.md`（APK NetworkConfig.sc→5套环境+STG免凭证guest注册+HMAC-SHA1签名匿名GET+支付回调receive_receipt status:1受理+95824条用户数据泄露+储值卡无鉴权+免鉴权短信）
- `apk-recon` ← `goodluck777-networkconfig-hidden-env.md`（GCS公开桶233MB APK+IL2CPP strings→3个S3桶名+i17game Node.js服务端源码HMAC硬编码koalasmarch/koalas+.git仓库泄私有GitHub+前端AES支付密钥+口令HMAC盐值硬编码）
- `sensitive-dir-dump` ← `goodluck777-gcs-s3-5bucket-leak.md`（IGS集团5个公开GCS/S3桶匿名列举：igspanther-ark 40000+对象+i17game服务端源码+igs-horse/igstapirus-prod+桶名发现方法论5路径）
- `captcha-ocr` ← `jiangxisls-6char-ddddocr-selfcheck.md`（6位验证码ddddocr≈83%+自校验重试循环：21B验证码错vs24B凭据错字节级oracle+len==6前置过滤+一次性验证码+5态响应序列+HTTPS必须）

## 补充路由（20260916 — 新增 Skill + Playbook 路由）

### 金融科技专项（4）
- `aspnet-otp-portal-pentest` ← ASP.NET OTP 门户 / `SendOtpByMail` / `ConfirmPassword` / reCAPTCHA v3 / F5 WAF / 以色列金融
- `flutter-wcf-fintech-pentest` ← Flutter Web `main.dart.js` 逆向 + WCF `.svc` 无认证 PII / OTP 绕过改密 / Firebase / TASE
- `fintech-platform-pentest` ← 金融科技通用 / 投资平台 / `amitId`
- Playbook `以色列金融科技深度渗透Playbook.md` ← 以色列市场 / `.co.il` / 地理封锁 / Link11 WAF / F5 / reCAPTCHA Enterprise

### 管理后台框架（2）
- `filament-admin-pentest` ← Filament v3 / Livewire RPC / Laravel 管理后台 / `/admin/login`
- `filament-livewire-admin-pentest` ← 纯 Livewire / `wire:snapshot` / `wire:effects`

### 源站/CDN 绕过（1）
- `edgeone-origin-bypass` ← 腾讯 EdgeOne / CDN 源站发现 / JS `imgUrl`/`launchGameCDNs` / Censys / hackertarget

### 逆向专项（3）
- `electron-app-source-recon` ← Electron asar 解包 / Vue+SQLite / 全量源码走读
- `docker-image-extraction` ← Docker 镜像 tar 层提取 / `docker save`
- `dart-flutter-reverse` ← Dart/Flutter `libapp.so` / `kernel_blob.bin` 逆向

### 业务专项（4）
- `blackmarket-data-platform-pentest` ← 黑产数据查询平台 / 实时定位 / 开房记录 / USDT 充值 / 社工库
- `dnake-d5-parking-pentest` ← DNAKE D5 停车/门禁系统
- `cod-ecommerce-launch` ← COD 货到付款电商启动
- `codegen-module-db-pivot` ← CodeGen 代码生成模块 DB 透视

### 新 Playbook 路由（5）
- Playbook `多组件SaaS理赔平台渗透手法.md` ← Okta SSO / Elasticsearch / 理赔平台
- Playbook `数字人推理管道命令注入与OSS回传手法.md` ← Img2Avatar / FancyTalk / `ref_sequence` / `download_model_zip`
- Playbook `SpringCAS-initPassword全栈ATO手法.md` ← CAS 单点登录 / `;.js` Actuator 绕过 / Prometheus / initPassword ATO
- Playbook `GVA已知签名钥与本地上传写文件手法.md` ← GVA `setSystemConfig` 写文件 / `sysExportTemplate` SQLi / 明文凭据日志

### 攻击路径总指挥（1）
- `attack-chain` ← 攻击路径编排 / 总指挥 / 深度优先 / 组合链 / 换面决策 / 散弹（三大铁律：有产出不换 / 组合回查 / 死路严格）

### CVE 日报 2026-09-16 新增路由（2）
- `gitlab-path-traversal-file-read` ← GitLab CE/EE / CVE-2026-85706 / `/api/v4/projects` / commits API 路径穿越 / secrets.yml / 任意文件读（CVSS 10.0 KEV）
- CVE日报 `CVE日报-2026-09-16.md` ← GitLab穿越 / Cisco SEG SQLi / ScreenConnect / BlueMoon 利用链 / SharePoint RCE / Pixel 基带

### 踩坑教训 → 探针升级（3）
- `strike_probe.py` ← 新增 `_detect_spa_catchall()`：SPA catch-all 假阳性过滤（踩坑教训：白标博彩 SPA 兜底 200 ≠ 后台存在）
- `aspnet-otp-portal-pentest/references/pitfalls-and-lessons.md` ← 7 大坑记录（reCAPTCHA 复用 / OTP N=1 / 出口过滤 / phoneNumber Oracle）
- `admin-console-discovery/references/separate-host-admin-and-catchall-pitfalls.md` ← 管理端分离 + SPA 兜底假阳性 + 出口过滤诊断


---

## 外部库增量（2026-10-11 分享包）

## 新增路由（20260925 — taskking/126310 若依-Vue-Plus 全链报告）

### 1 张新卡 + 1 个新 reference

- **`ruoyi-vue-plus-admin-fullchain`** — 若依-Vue-Plus 系后台**五层下潜链**：默认口令+验证码服务端不校验 → 密钥面(`front/{key}` / `monitor/cache` 读任意 Redis 命名空间 / `sys_oss_config` / api-docs) → Shodan 源站定位(`ssl:` 证书 CN + `http.title:` 找同源码第二环境) → 18080 裸端口绕 nginx → 3306 弱口令 + MinIO 19000 SigV4 → 云 Root AK。
  触发词：若依、RuoYi-Vue-Plus、admin123、126310后台管理、front配置路由、monitor/cache、sys_oss_config、18080裸端口、MinIO桶、云AK泄露。
  references：`01-origin-locate-bare-ports` / `02-ruoyi-secret-planes` / `03-mysql-minio-object-storage` / `04-negative-verdicts-and-redlines`(SnailJob组件不存在·EL1007E·orderByColumn白名单·phpMyAdmin IP白名单XFF无效) / `05-taskking-126310-case`
- `cloud-credential-leak-exploitation` ← `references/tencent-root-ak.md`（腾讯云 Root 密钥：`sts:GetCallerIdentity` 判身份 + 只读盘点六 API + **`tat:RunCommand` 只对 CVM 生效、LightHouse 无此 API** 的能力边界 + 处置纪律）
- `wallet-exchange-fund-verification` ← `references/ponzi-crosscheck.md` 追加**刷单/广告结算盘家族**：无网关三连定性 + 试玩号(`is_trial_account`)灌水修正 + **真实回款率公式**(实测 1.04%) + 取信节奏量化 + 驳回话术聚类
- `cn-admin-framework-pentest` ← 新增「若依-Vue-Plus 4.x 二开」小节（与 GA/TOTP 分支相反：干净口令直入超管）
