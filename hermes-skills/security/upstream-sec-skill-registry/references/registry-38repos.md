# 上游安全技能源索引（38 仓库）

来源：`din4e/Skills4RedTeam` README（自述数据 2026-09-05）· 本地采集 2026-09-25  
校验：README 内 github 链接去重 = **38 条**，与本表行数一致（无遗漏）。
用法：先跑 `scripts/dedupe_gate.py` 过闸，只拉真缺口。

## 一、优先拉取（本地去重结论）

| 仓库 | 为什么值得拉 |
|------|--------------|
| `bluechips-zhao/av-evasion-skills` | **缺口最大**:免杀三件套(Indirect Syscall/ETW 补丁/Module Stomping)深水区 |
| `yoanbernabeu/supabase-pentest-skills` | 本库仅 `supabase-rls-pentest` 单卡,24 skill 可扩面 |
| `CreditTone/android-reverse-engineering-skill` | jadx + **Fernflower/Vineflower** 工具链,本库 0 命中 |
| `incogbyte/android-reverse-engineering-claude-s` | 同上(APK/XAPK/AAB/DEX/JAR/AAR 全格式) |
| `SimoneAvogadro/android-reverse-engineering-ski` | Retrofit/OkHttp API 提取段可核对 |
| `Fausto-404/ai-mobile-reverse-skills` | 移动 6 阶段总控:流量↔代码对齐、SO/JNI 深挖、加密与验证设计 |
| `ADScanPro/Claude-AD` | AD 的**技术遥测与合规映射**视角,本库 AD 深但缺这块 |
| `x-glacier/kali-pentest` | 269 CLI 工具 14 类清单 → 工具/别名索引源 |
| `zhaoxuya520/reverse-skill` | 任务类型自动路由 + 工具链自举 + 经验库进化 |
| `P4nda0s/reverse-skills` | IDA-NO-MCP 导出 → 符号/数据结构重建 |
| `0rangec3t/Black-cat` | 状态机 RECON⇄ENUMERATE⇄VALIDATE,核假设回退细节 |
| `elementalsouls/Claude-OSINT` | 80 dork + 80 secret-regex + 9 只读凭证验证器 |
| `SpecterOps/skills` | 26 插件:C2(CS/Mythic/Outflank)+AD+SCCM+MSSQL |
| `transilienceai/communitytools · crazyMarky/pentest-skills · mukul975/Threatswarm · blacklanternsecurity/red-run` | 编排型(scope 强制/kill-chain agent),与 `pentest-methodology` 同构,缺细节才拉 |
| `tanweai/wooyun-legacy · Pa55w0rd/secknowledge-skill · trailofbits/skills · alirezarezvani/claude-skills · mukul975/Anthropic-Cybersecurity-Skills` | **已吸收/高重合**(本库 secknowledge-skill 含 WooYun 88,636 案例、trailmark 系为 ToB 派生)——拉前必过闸 |
| `Batman0506/openclaw-sec-skills · DaoYiSec/SecSkills` | **索引型商城**非内容,只做交叉核对 |

```bash
git clone --depth 1 https://github.com/<owner>/<repo>.git D:/skills4redteam/<repo>
python3 scripts/dedupe_gate.py --src D:/skills4redteam/<repo> --quiet-ok
# 卡文件名不是 SKILL.md 的仓库(如 <中文名>-<English>.md):加 --glob '*.md'
```

## 二、38 仓库全表

| # | 仓库 | 更新 | 说明 | 链接 |
|---|------|------|------|------|
| 1 | `elementalsouls/Claude-BugHunter` | 2026-09-04 | 红队 / 外部渗透漏洞挖掘技能包 —— 82 个 skill + 15 个 slash command + 681 份已披露报告模式（覆盖 24 类核心漏洞）+ 企业身份与基础设施攻击矩阵，聚焦 bug bounty 与红队行动方法论 | https://github.com/elementalsouls/Claude-BugHunter |
| 2 | `SpecterOps/skills` | 2026-09-03 | SpecterOps（BloodHound 作者公司）出品的红队 AI skills marketplace，Outflank 与 Fortra 协作共建（）—— 26 个插件覆盖 C2（Cobalt Strike/Mythic/Outflank C2）、AD 攻防（ADCS/SCCM/MSSQL/侦察）、Windows/Linux/mac 三平台 tradecraft、payload、社工、逆向、报告生成，集成 BloodHound/Ghostwriter/Binary Ninja MCP，对标 Trail of Bits marketplace | https://github.com/SpecterOps/skills |
| 3 | `Masriyan/Claude-Code-CyberSecurity-Skill` | 2026-09-03 | 19 个 Claude Code 安全技能，覆盖攻击性安全、防御运营、逆向工程、威胁狩猎、CSOC 自动化、红队行动、密码分析等，较为全面的 Cybersecurity 技能集合 | https://github.com/Masriyan/Claude-Code-CyberSecurity-Skill |
| 4 | `zhaoxuya520/reverse-skill` | 2026-09-03 | 逆向/渗透/安全研究技能路由包 —— AI 自动路由（识别任务类型匹配方法论）+ 按需自举工具链 + 自动进化经验库；覆盖 Android/iOS/二进制/.NET/JS 逆向、恶意代码分析、Pwn、CTF（40+ 子技能）、固件 IoT、N-day、EDR 规避、API 安全、LLM 安全等 18+ 场景；支持 Claude Code / Kiro / Cursor / Cline 等 | https://github.com/zhaoxuya520/reverse-skill |
| 5 | `jiker666/src-6k-security-research-skills` | 2026-09-02 | SRC 众测安全研究技能包 —— 黑盒 SRC 挖掘、固定范围测试、品牌/集团资产发现、JS/API 分析、漏洞验证、中文报告与白盒 0day 审计；48 个按需加载专题模块、L0-L4 分层运行时规则、Evidence-First 证据链方法论（Signal → Hypothesis → Controlled Test → Differential Evidence → Impact → Finding），内置 FOFA MCP | https://github.com/jiker666/src-6k-security-research-skills |
| 6 | `trailofbits/skills` | 2026-09-02 | Trail of Bits 出品，17+ 安全研究技能 —— 漏洞检测、差分代码审查、审计上下文构建、修复验证，专注安全研究、漏洞检测与审计工作流，质量较高 | https://github.com/trailofbits/skills |
| 7 | `gadievron/raptor` | 2026-09-01 | 将 Claude Code 转为通用攻防安全 agent，覆盖侦察 → 入侵 → 横向移动 → 后渗透全流程，自动编排攻击链（疑为 GitHub Trending 榜首的全自动 AI 渗透测试员） | https://github.com/gadievron/raptor |
| 8 | `mukul975/Anthropic-Cybersecurity-Skills` | 2026-08-31 | 817 个结构化网络安全技能，映射 MITRE ATT&CK、NIST CSF 2.0、MITRE ATLAS、D3FEND、NIST AI RMF、MITRE F3 等 6 大框架，覆盖 29 个安全域、进攻 / 防御 / 合规全谱系，支持 Claude Code / Copilot / Codex / Cursor / Gemini CLI 等 20+ 平台，目前规模最大的 AI 安全技能库 | https://github.com/mukul975/Anthropic-Cybersecurity-Skills |
| 9 | `SnailSploit/Claude-Red` | 2026-08-30 | 37 个即插即用的攻击性安全技能 —— Web 攻击（SQLi/XSS/SSRF/SSTI/XXE）、Shellcode 编写、EDR 规避、漏洞利用开发、红队行动、OSINT、模糊测试等 | https://github.com/SnailSploit/Claude-Red |
| 10 | `elementalsouls/Claude-OSINT` | 2026-08-30 | OSINT / 侦察技能包 —— 8 个 skill、100+ 侦察能力、80 个 secret-regex 模式、80+ Google dorks、9 个只读凭证验证器、27 个攻击路径模板，约万行结构化 tradecraft | https://github.com/elementalsouls/Claude-OSINT |
| 11 | `alirezarezvani/claude-skills` | 2026-08-30 | 380+ 技能大型集合（30+ Agents、70+ 自定义命令），包含多个安全相关子技能：senior-security（威胁建模/渗透测试/OWASP）、ai-security（Prompt 注入检测/模型安全）、cloud-security（CSPM 云安全）、security-pen-testing 等，推荐作为技能库底座 | https://github.com/alirezarezvani/claude-skills |
| 12 | `Gabson0x/bountyforge` | 2026-08-29 | 全能 bug bounty 技能 —— 8 个专项 agent 并行攻击不同面：Web/API（IDOR/XSS/SSRF/SQLi/GraphQL/CORS 等）+ 智能合约审计（EVM/Move/Solana/TRON），发现去重、CVSS 打分，产出 HackerOne/Bugcrowd/Intigriti/Immunefi 提交级报告 | https://github.com/Gabson0x/bountyforge |
| 13 | `7onez/cti-expert` | 2026-08-28 | 网络威胁情报（CTI）& OSINT 分析技能 —— 67+ commands、35 项技术，IOC 提取、威胁画像、情报收集与关联，无需 API key | https://github.com/7onez/cti-expert |
| 14 | `ADScanPro/Claude-AD` | 2026-08-24 | Active Directory 内网渗透方法论 —— 阶段顺序、环境约束、技术遥测与合规映射，覆盖 Kerberoasting、ADCS ESC1-17、DCSync、NTLM Relay；驱动 netexec/impacket/certipy/bloodyAD/BloodHound CE 标准工具链（skills + agents + slash commands） | https://github.com/ADScanPro/Claude-AD |
| 15 | `Fausto-404/ai-mobile-reverse-skills` | 2026-08-14 | 移动安全分析 6 阶段总控 —— APK 静态侦察、流量与代码对齐、SO/JNI 深度分析、加密与漏洞综合分析、验证设计与报告交付，支持 JADX/Burp/Yakit/IDA/Ghidra MCP | https://github.com/Fausto-404/ai-mobile-reverse-skills |
| 16 | `bluechips-zhao/av-evasion-skills` | 2026-08-10 | Shellcode 免杀技能 v5.2 —— Indirect Syscall、ETW 补丁、Module Stomping、.text Code Cave、IPv4/XOR 混淆、HeapAlloc 缓冲等技术，从静态特征、行为轨迹、EDR 感知三层绕过主流杀软与 EDR（Python 处理脚本 + C Loader 完整生成链） | https://github.com/bluechips-zhao/av-evasion-skills |
| 17 | `0rangec3t/Black-cat` | 2026-08-03 | 假设-证据驱动的红队技能（Hypothesis-Driven Cognitive Architecture）—— 区别于流水线式 pentest skill，采用状态机设计（RECON ⇄ ENUMERATE ⇄ VALIDATE），失败与新发现可回溯重启早期阶段；覆盖信息收集、Web 渗透、内网横向、云安全、EDR 规避、数据库利用、逆向工程等 7 个 technique | https://github.com/0rangec3t/Black-cat |
| 18 | `transilienceai/communitytools` | 2026-07-29 | 面向 AI 驱动渗透测试的开源 skills / agents / slash commands 集合 | https://github.com/transilienceai/communitytools |
| 19 | `tanweai/wooyun-legacy` | 2026-07-14 | WooYun 漏洞知识库 —— 88,636 个真实漏洞案例（SQL 注入 27%、命令执行 19%、XSS 11% 等 15 种类型），86MB 精炼安全方法论 | https://github.com/tanweai/wooyun-legacy |
| 20 | `DaoYiSec/SecSkills` | 2026-07-06 | 刀义安全出品，53 个安全技能索引，覆盖代码审计、渗透测试、JS 逆向、CTF、红蓝对抗、移动安全、应急响应等 16 个分类 | https://github.com/DaoYiSec/SecSkills |
| 21 | `x-glacier/kali-pentest` | 2026-06-25 | Kali Linux 渗透测试技能 —— 269 个 CLI 工具 14 类，agent 经 SSH/Docker 接入 Kali 后自主规划攻击路径、跨阶段整合分析并产出结构化报告；15 场景 playbook、授权检查与高危动作人工确认门，支持 Claude Code/OpenClaw/Hermes | https://github.com/x-glacier/kali-pentest |
| 22 | `Batman0506/openclaw-sec-skills` | 2026-06-25 | OpenClaw 社区安全技能大全，150+ 技能索引，涵盖代码审计、渗透测试、逆向工程、CTF、威胁建模、移动安全、应急响应、安全工具 8 大领域 | https://github.com/Batman0506/openclaw-sec-skills |
| 23 | `incogbyte/android-reverse-engineering-claude-skill` | 2026-06-20 | Android 逆向自动化技能 —— APK/XAPK/AAB/DEX/JAR/AAR 反编译（jadx + Fernflower）、Retrofit/OkHttp HTTP 端点提取 | https://github.com/incogbyte/android-reverse-engineering-claude-skill |
| 24 | `Pa55w0rd/secknowledge-skill` | 2026-06-17 | Web 与 AI 安全测试知识技能 —— 克隆到 skills 目录后自动加载，提供测试方法论与安全知识库 | https://github.com/Pa55w0rd/secknowledge-skill |
| 25 | `RuoJi6/audit-skills` | 2026-06-16 | Java Web 源码安全审计 —— 路由提取、SQL 注入/XXE/文件上传/鉴权绕过多维度自动化审计；轻量化设计，只负责安全边界（原 `java-audit-skills`，已改名） | https://github.com/RuoJi6/audit-skills |
| 26 | `SimoneAvogadro/android-reverse-engineering-skill` | 2026-06-10 | Android APK/XAPK/JAR/AAR 逆向 —— jadx 反编译、Retrofit/OkHttp API 提取、调用流追踪、ProGuard 混淆分析 | https://github.com/SimoneAvogadro/android-reverse-engineering-skill |
| 27 | `Eyadkelleh/awesome-skills-security` | 2026-06-08 | 从 SecLists 打包的安全测试工具包，提供 wordlists、injection payloads、patterns、webshells 等，即插即用，适合 pentest、CTF、bug bounty | https://github.com/Eyadkelleh/awesome-skills-security |
| 28 | `crazyMarky/pentest-skills` | 2026-06-04 | 模块化渗透测试技能 —— 自然语言驱动专业级 pentest（信息收集 → 漏洞利用 → 后渗透），支持 Claude Code / Gemini CLI | https://github.com/crazyMarky/pentest-skills |
| 29 | `BrownFineSecurity/iothackbot` | 2026-06-01 | IoT 渗透测试技能集 + 混合 IoT pentest 工具链（固件分析、硬件接口、无线协议等） | https://github.com/BrownFineSecurity/iothackbot |
| 30 | `yunmengya/PHP_AUDIT_SKILLS` | 2026-05-08 | PHP 代码审计 —— 基于 Agent Teams 多智能体协作，静态分析 + 动态追踪 + AI 辅助三重审计，覆盖 21 种漏洞类型 | https://github.com/yunmengya/PHP_AUDIT_SKILLS |
| 31 | `CreditTone/android-reverse-engineering-skill` | 2026-05-07 | 专为 Codex 适配的 Android 逆向分析技能 —— jadx + Fernflower/Vineflower 反编译 APK/XAPK/JAR/AAR，梳理 Manifest/包结构/网络层/调用链，提取接口/URL/鉴权头/token/签名逻辑，并提供 Frida、抓包、JNI/SO 分析前的静态侦察方法（与同名 的 Claude Code 版不同，本仓库面向 Codex） | https://github.com/CreditTone/android-reverse-engineering-skill |
| 32 | `P4nda0s/reverse-skills` | 2026-05-06 | 二进制逆向工程 —— 配合 IDA-NO-MCP 导出反编译结果，分析函数符号、重建数据结构（rev-symbol / rev-struct） | https://github.com/P4nda0s/reverse-skills |
| 33 | `mukul975/Threatswarm` | 2026-04-29 | 27 个 scope 强制 agent 组成的全 kill-chain 渗透插件 —— recon → exploit → post-ex → DFIR → 报告一条命令跑完，背后由 754 个 MITRE ATT&CK 映射技能驱动（与 同作者） | https://github.com/mukul975/Threatswarm |
| 34 | `blacklanternsecurity/red-run` | 2026-04-01 | 攻击性安全工具包，结合 Skills + MCP Servers + Agent Teams，实现 recon → initial access → lateral movement → privilege escalation → post-access 完整红队流程路由 | https://github.com/blacklanternsecurity/red-run |
| 35 | `Orizon-eu/claude-code-pentest` | 2026-03-11 | 6 个 skill 自动化完整 pentest 生命周期 —— 给一个域名，从 recon 到漏洞利用链再到 bug bounty 报告；43 个脚本零 pip 依赖 | https://github.com/Orizon-eu/claude-code-pentest |
| 36 | `BehiSecc/VibeSec-Skill` | 2026-02-17 | 安全优先代码审查 —— 以漏洞猎手视角审视代码，捕获 Web 应用常见漏洞（OWASP Top 10），防御性安全辅助 | https://github.com/BehiSecc/VibeSec-Skill |
| 37 | `3stoneBrother/code-audit` | 2026-02-13 | 通用代码审计 —— 支持 55+ 漏洞类型，双轨审计模型（自动化 + 专家模式），覆盖 Java/Python/Go/PHP/JS/C 等多语言 | https://github.com/3stoneBrother/code-audit |
| 38 | `yoanbernabeu/supabase-pentest-skills` | 2026-01-31 | Supabase 应用安全审计专项 —— 24 个 skill 覆盖 secret key 提取、RLS 策略测试、IDOR 检测、存储桶审计、证据收集与综合报告 | https://github.com/yoanbernabeu/supabase-pentest-skills |