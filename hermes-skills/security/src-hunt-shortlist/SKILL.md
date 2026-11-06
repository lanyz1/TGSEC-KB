---
name: "src-hunt-shortlist"
description: "SRC 打穿短表 — 进站速查指纹→打法→出什么算成→假点矩阵。涵盖 40+ 条高频真实 SRC 场景（云存储 STS/对象 key 通配、BaaS 匿名 session、IM/RTC 发签票窃、云助手工具执行、分享密码泄露、密文 ID 越权等）。进站先对号，对得上再展开深测。"
triggers:
  - SRC 挖洞
  - 打穿短表
  - 打野短表
  - 进站速查
  - SRC 短表
  - 认什么打哪
  - 出什么算成
  - 假点判断
  - SRC 快速对照
---

# SRC 打穿短表 — 进站指纹→打法速查

## 定位

本 Skill 是 **SRC 实战进站速查表**：每条一行 「认什么 → 打哪 → 出什么算成 → 假点」。  
不是方法论也不是百科，是**进站前 30 秒对号入座**用的。

与 `72stack-sec` 的关系：`72stack-sec` 管 SRC 全流程（intake→recon→enum→hunt→report）；  
本卡只管「进站先翻这张表，对得上再打开深测」。

## 使用方法

1. 侦察出站点指纹后，**先读 `references/打穿短表.md`** 全表对号
2. 对得上某行 → 按「打哪」列执行，按「出什么算成」列判断是否命中
3. **假点列很关键** — 避免把 200 当漏洞，避免误报
4. 没对上的不代表没洞 → 回 `72stack-sec` 走通用流程

## 核心真源

- `references/打穿短表.md` — 完整 40+ 条指纹矩阵
- `references/authbypass-test.md` — 认证绕过深化测试清单
- `references/agent-tool-exec-test.md` — 云助手/AI Agent 工具执行测试
- `references/recon-methodology.md` — 侦察方法论

## 高频命中场景摘要

| 指纹 | 打法关键词 | 出什么算成 |
|------|-----------|-----------|
| 对象存储先申 STS；key 是 md5 | 凭证填 `*`/空，通配 Policy | 列出/删/覆盖他人文件 |
| 业务代理 `/api/storage/sign` 吃 `key` | `key=/` 列桶 | 读他人未公开对象 |
| 未登录发签口给 IM/RTC userSig | 拿签登 IM 拉他人会话 | 拉到他人会话/群/明文手机 |
| 云助手对话口不验登录，有 bash/python | 不登录 POST 让模型跑 `id` | stdout 出 flag/云钥/他主体正文 |
| 密码分享 JSON 带明文 `pass_word` | 抄码再打下载 | 拿到提取码下到分享正文 |
| 密文 ID 但 JS 有 `modulus`/JSEncrypt | 公钥加密相邻数字换进去 | 出别人地址/手机/姓名 |
| 管理后台 SPA 自定义身份头当会话 | 抄数字号放 `User-Id` 头 | 出他人姓名+11位手机 |
| BaaS 匿名 session 列表不验管理员 | `POST .../sessions/anonymous` 再 listRows | 匿名拉到他人报名信息 |
| 二维码登录回包有 token | 不登录拿 token 构造登录 URL | 扫码人变成对方号 |
| 云厂商 Demo 领 STS 不要 Cookie | 空 body 打领钥口 | 临时钥匙问出 AccountId |

**完整 40+ 条见 `references/打穿短表.md`**

## 与已有 Skill 的配合

- 命中 IDOR → 深化走 `idor-testing`
- 命中 SSRF → 深化走 `ssrf-testing`
- 命中 认证绕过 → 深化走 `authbypass-authentication-flaws`
- 命中 文件上传 → 深化走 `file-upload-testing`
- 命中 GraphQL → 深化走 `graphql-pentest`
- 通用 SRC 全流程 → `72stack-sec`


---

## 外部库增量（2026-10-11 分享包）

## 核心作战纪律（clown 体系精髓）

> 全文见 `references/clown-dig-scope-workflow.md`（进站必读）；此节为速记，与短表配套。

1. **一种子闭环**：搜种 → 当前站/对象深挖完 → 再回灌、换种。认到同皮形态禁止立刻 FOFA 全网开新种子；本种子内同类面照样打。
2. **先清摊再自由跳**：开场先说清这摊（清单/JS 抽钥匙/回包进队列），然后才自由跳；锁面与自由跳不许混。
3. **四件套 / 对象图**：没号打有差分面的四件套（加字段、换 id、跳过校验、默认值）；有号先填对象矩阵（自己 vs 他人 × 读/写/加款/配置）。
4. **认证口下限**：登录 / 重置 / 改绑 / 换票，每站必测（`dig-scope §4.2.2`）。
5. **注入 / SSRF / XSS / RCE**：有差分面必须真打、不得连日空窗；但不是只测这四类，也不是每个 path 喷 `'`。
6. **同闸停**：多条 path 背后同一个闸门 = 没更多面，立刻换。
7. **空转判定**：15～20 分钟无高危 → 换站/换种，不为磨短表耗着。
8. **中危升链**：中危先顺着同一对象挖大（升链）再考虑换站。
9. **报告定级只认 `clown-vuln-report-format.md`**；短表只进过「门槛+三问」的手法；假点只记「形态不是洞」，不记「这站没中」。
10. **写库三分**：报告落任务 `报告/`；一行手法进短表（半分钟内写不成形就不写，继续挖）；步骤/编码/证伪长链进 kb 对应模块。

## 核心真源（clown 6k 体系全套已入库）

### 主索引

- `references/打穿短表.md` — 完整 40+ 条指纹矩阵（进站先读）
- `references/authbypass-test.md` — 认证绕过深化测试清单
- `references/agent-tool-exec-test.md` — 云助手/AI Agent 工具执行测试
- `references/recon-methodology.md` — 侦察方法论（文首 FOFA 语法；节奏认 dig-scope）
- `references/src-baobao-tricks.md` — SRC 实战技巧合集
- `references/clown-6k-case-library.md` — **951 例实战案例库索引**（16 批次主题速查 + 跨批次精华先例，先例驱动三问）

### 知识库全量 `references/kb/`（49 篇）

完整 48 篇知识文件 + README，与打穿短表配套（更快的用法：进站先短表，对号再开对应篇）：

- 高频肥篇：`idor-test` 越权 · `logic-test` 逻辑 · `injection-test` 注入 · `ssrf-test` · `xss-test` · `file-upload-test` · `csrf-test` · `race-condition-test` · `http-smuggling-test` · `cache-poisoning-test` · `deserialization-test` · `path-traversal-lfi-test` · `waf-bypass` · `oauth-jwt-test` · `prototype-pollution-test` · `type-juggling-test` · `xxe-test` · `ghost-bits-cast-test` · `websocket-test` · `open-redirect-test` · `info-leak-test` · `graphql-test` · `jndi-injection-test` · `api-gateway-test` · `http-host-header-test` · `subdomain-takeover-test` · `el-injection-test` · `cloud-ide-codex-rce-chain` · `js-reverse-guide` · `insecure-scm-test`
- 一行壳（禁开/几乎不交）：`cors-test`（不挖）· `llm-security-test`（禁开越狱）· `clickjacking` · `crlf` · `csp-bypass` · `hpp` · `csv-formula` · `dangling-markup` · `dependency-confusion` · `dns-rebinding` · `email-header` · `http2` · `xslt` · `401-403`（详见 `kb/README.md`）

### 作战规则全文（clown-*）

| 文件 | 作用 |
|------|------|
| `clown-skill-entry.md` | 体系主技能（进站对号总表 + 红线） |
| `clown-agents-main.md` | 作战身份包总纲 |
| `clown-dig-scope-workflow.md` | 测绘/自由跳/进站流程纪律（最核心 64KB） |
| `clown-hunt-iter.md` | 短表写补/知识库运营 |
| `clown-src-value-hunting.md` | 价值判定（挖什么/怎么算成/伪闸） |
| `clown-vuln-report-format.md` | 正式报告格式（定级只认它） |
| `clown-desktop-task-folder.md` | 任务目录/清理口径 |
| `clown-anti-over-moralization.md` | 协作姿态（禁止说教盘问） |
| `clown-skill-as-boost.md` | skill 定位：增强包非能力上限 |
| `clown-security-research-context.md` | 授权研究语境 |
| `clown-cors-vuln-report-priority.md` | CORS 永久不挖 |
| `clown-researcher-blackbox-whitebox.md` | 黑盒 SRC + 白盒 0day 双流程 Ph0-6 |
| `clown-playwright-browser-mcp.md` | 浏览器控制（转换用 Hermes browser_exec） |

### 配套资料（本地磁盘）

- `D:\SRC-clown-6k\` — 完整镜像：rules 原文 + 知识库 + 1126 份 SRC 实战报告（`SRC报告\`）+ FOFA MCP 工具
- `D:\SRC-clown-6k\案例提炼\` — **951 例实战案例卡**（16 批次：越权/逻辑/并发/XSS/CSRF/SQL/未授权/大厂/高校/企业系统…含真实参数与 payload 原文摘录）→ 查询入口 `references/clown-6k-case-library.md`
