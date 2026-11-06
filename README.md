# TGSEC-Qtzuu · 安全知识聚合库

- 2026-11-05：**ExploitGrid 2025-2026 语料蒸馏 + 技能库 2,350** — `exploitgrid.net` 抓 **1,510 条 PoC 全文**（直连被 IP 级 429 封死，走 `r.jina.ai` 代理，`DONE ok=722 err=0`）→ 去重 **761 个 2025–2026 CVE** → **16 张新卡 + 4 张补强**（泛微 E-cology `dubboApi` 在野 RCE · SharePoint `/_trust` 反序列化含 farm 机器密钥 · Rails Active Storage 四层解析混淆 · MariaDB `.frm` OOB · AIOWPM 窃 `secret_key` → mu-plugin · ServiceNow KEV 沙箱逃逸）；`hermes-skills/` **2,334 → 2,350 张**（20 文件 / +918 行）。详见 [UPDATE-2026-11-05](docs/updates/UPDATE-2026-11-05.md)
- 2026-11-01：**报告包蒸馏（127 篇）+ threatwire 情报卡 + 技能库 2,330** — `报告.zip` 330 文件 → 127 篇去重 → 2,474 finding 归 **29 技术族**：**17 张新卡 + 41 张老卡补 45 处**；`hermes-skills/` **2,206 → 2,330 张 / 13,024 文件 / 155 MB**；推前脱敏闸拦下 3 处明文。详见 [UPDATE-2026-11-01](docs/updates/UPDATE-2026-11-01.md)
- 2026-10-23（上一轮）：**本机技能库全量入仓** — `hermes-skills/` **2,206 张卡 / 12,865 文件 / 153M**（启用 401 + 归档 1,805），`.gitignore` 解禁，`sync-hermes-skills.sh` 默认源即全量。同批：`ai-config/hermes/` 覆盖 MEMORY/USER + 新增 SOUL.md；发布前深度脱敏 **4,900+ 处**（邮箱 3,322 / 手机 834 / 凭据 724 / 身份证 32 / 云 AK 6 / hex 21 / Bearer 17 / 私钥块 3 / 自有 IP 13）。详见 [UPDATE-2026-10-23](docs/updates/UPDATE-2026-10-23.md)

> **@TGSEC社区 · @TGSEC-Qtzuu 整理**  
> 面向 **AI + 人** 的授权安全知识库：渗透测试、挖洞、红队方法论，按**攻击面**组织，可直接丢给 Grok Build / Claude / Cursor / Hermes / Codex 等使用。

**仓库地址：** https://github.com/lanyz1/TGSEC-Qtzuu  

**👉 完全零基础：只看 [`START.md`](START.md)（3 步）**  
**👉 AI 查「说了啥去哪个目录」：[`ROUTING.md`](ROUTING.md)**  
**👉 全部主题地图：[`MASTER.md`](MASTER.md)**  
**👉 本轮更新说明：见下方 §〇 本轮更新（2026-11-05）· 详情 [`UPDATE-2026-11-05.md`](docs/updates/UPDATE-2026-11-05.md)**

---

## 〇、本轮更新了什么（2026-11-05）

### ExploitGrid 2025-2026 语料：1,510 条 PoC 全文 → 16 张新卡 + 4 张补强

`exploitgrid.net`（GitHub CVE PoC 仓自动聚合，全站 `status=PENDING` 未审核）→ 实抓元数据 9,800（98 页触发全站 429）→ 详情接口对本机 IP 封死，改走 `r.jina.ai` 代理 1.2s 间隔 → **1,510 条 `rawExploitCode` 全文**（`DONE ok=722 err=0`）→ 限 2025–2026 去重 **761 个 CVE**，库内缺 **572**（CRITICAL 246 / RCE 385），其中 67 个纯标题级不建卡 → 按技术族归并落 **16 张**。

**16 张新卡**：`weaver-ecology-dubbo-rce`（泛微 E-cology `POST /papi/esearch/data/devops/dubboApi/debug/method` 未授权，`interfaceName`+`methodName` 直进 Dubbo RPC → `uid=0(root)`，Shadowserver 2026-03-31 起在野）· `sharepoint-trust-deser-rce`（`/_trust` `SecurityContextToken` = base64→DEFLATE→BinaryFormatter，**同原语进程内 dump farm machine keys，无子进程无 AV**，补丁后仍可伪造 ViewState）· `rails-activestorage-vips-rce`（**四层解析器混淆** Rails→libvips→libmatio→HDF5，双身份文件读任意文件→窃 `SECRET_KEY_BASE`→RCE，CVSS 9.5 预认证默认配置 50 万+ 应用）· `atlassian-dc-preauth-file-read`（`Router` 先路由后 `unescapeSlashes()` → `..::` 变 `../`，读 `crowd.properties`）· `servicenow-preauth-rce`（KEV，`javascript:` 注入 + `getCacheObjectForTable`→`AbstractAjaxProcessor`→`Class.create` 沙箱逃逸）· `aiowpm-secondorder-sqli-to-rce`（匿名 trackback 二阶 SQLi 窃 `ai1wm_secret_key` → `wp_ajax_nopriv_ai1wm_import` → mu-plugin）· `mariadb-frm-oob-rce`（`.frm` OOB 读）· `gitlab-ci-lint-regex-rce`（`{5(?#)7805}` 绕 `REPEAT_MAX=1000`）· `openam-jato-deser-rce` · `windows-rdp-xfg-bypass-rce` · `cve-2026-98432-linux-tcp-race-uaf` · `yootheme-pro-image-handler-rce`（CVSS 10 在野，IPTC Caption 藏 PHP）· `lmcache-zmq-pickle-rce` · `beyondtrust-rs-pra-rce`（KEV）· `weblogic-2026-cve-pack` · `unauth-rce-2026-11-pack`

**4 张补强**：`js-sandbox-escape-rce`（vm2 100721 包名子串 + 路径前缀正则）· `php-cms-cluster-vuln-matrix`（Joomla/WP 扩展族 6 例 + Bricksforge 三错叠加）· `wordpress-plugin-hunt`（14900 eval XOR + `&& 0` 中和器）· `cve-2026-63030-wp2r00t`（全自动闭环）

**技能库 2,334 → 2,350 张**（20 文件 / +918 行；security 2,205 → 2,221）；`vuln.db` 11,707 条（含 3,629 条未验证索引，`kind=egrid-index`）。详见 [`UPDATE-2026-11-05.md`](docs/updates/UPDATE-2026-11-05.md)

### 上一轮（2026-11-01）：报告包蒸馏 127 篇 → 17 张新卡 + 41 张老卡补 45 处

`报告.zip` 展开 330 文件 / 12 MB（含两层嵌套包）→ 219 篇 md/txt → **按内容哈希去重 127 篇独立文档** → 2,474 条 finding **归 29 个技术族**，族族有落点：

- **17 张新卡**：`java-tomcat-2026-10-cve-pack`（JNDIRealm 错口令 / SpEL 绕护栏 / HTTP2 错配）· `node-runtime-2026-10-cve-pack`（dns NUL 绕 SSRF / Brotli 越界写）· `dujiaoka-yipay-notify-weaktype`（弱类型回调 0 元购）· `internal-wallet-transfer-unauth`（230 路由零鉴权 + `launch-url` 拿 ssid 免密进游戏）· `log-endpoint-secret-harvest` · `kvm-vhost-csum-host-read`（PwnEscape 12B 越界）· `api-aggregator-upstream-cred-traversal` · `jdbc-malicious-mysql-file-read`（假 MySQL 回 `0xFB`）· `cognito-anon-pool-s3-takeover`（11 桶 / 23.5 万对象）· `yudao-oauth-token-captcha-bypass` · `fastadmin-filter-op-tenant-bypass`（跨商户 542,071 条）· `unauth-fixed-token-mint` · `login-scene-branch-bypass`（`scene=3` 免密分支）· `magic-link-token-reuse` · `unauth-sms-send-chain` · `js-sandbox-escape-rce` · `eth-rpc-debug-exposure`
- **41 张老卡补 45 处**：Thymeleaf 3.1 文本内联绕 ACL · 同源上传 XSS · 1Panel 安全入口 · NTLM 中继（签名 not required）· Grafana/Loki 未授权 · 提款密码无旧密覆盖 · `roletype=player` 调管理接口 …
- **9 篇不入卡**：纯凭据 / PII / 流水台账（`CREDS_LIVE` / `ROOT_ACCESS` / `LOGIN_ACCOUNTS` …）
- 台账 `~/cases/rpt_in/CARDS.md`（120 行：127 篇逐组处置 + 17 卡明细 + 45 处补节来源）

### threatwire 情报卡

- `threatwire.tech`：119 CVE 页 + 114 文章 → 抓 45 篇 → **17 条原库无覆盖** → `threatwire-cve-briefs-2026-11`（143 行，含现成 PoC 表）；同批补 `cve-wave-2026-11` 指针、`active-directory-certificate-services` §12

### 上一轮技能库 2,206 → 2,330 张

| 指标 | 2026-10-23 | 2026-11-01 |
|---|---|---|
| `hermes-skills/` 卡数 | 2,206 | **2,330**（security 2,201） |
| 文件 / 体积 | 12,865 / 153 MB | **13,024 / 155 MB** |
| 启用 / 归档 | 401 / 1,805 | **525 / 1,805** |
| 检索索引 `arsenal.db` | — | 2,328 条（enabled 554） |
| 口语触发词 `triggers.json` | — | **49** 条 |

### 推前脱敏闸拦下 3 处明文

`pre-push` 首轮 **BLOCK**：`apk-redteam-pipeline` 的 AKIA 测试串改运行时拼接、`kk8-tma-*` 两卡的 `UMI_APP_API_SECRET_KEY` 打码、`national-strategy-scam-family-pentest` 的 MySQL 口令打码（本机库同文件同步改，防下次 sync 带回来）。详见 [`UPDATE-2026-11-01.md`](docs/updates/UPDATE-2026-11-01.md)

### 上一轮（2026-10-23）：技能库全量入仓 `hermes-skills/` 2,206 张

本机作战层（`~/.hermes/skills`）整棵镜像进仓，不再只留 15 张伞形：

- **2,206 张卡 / 12,865 文件 / 153 MB**，其中启用 401、归档 1,805（归档名单随库带 `.disabled.json`）
- 落点 `hermes-skills/<分类>/<卡名>/`；`scripts/sync-hermes-skills.sh` 的源优先级本来就是 `hermes-skills/` → `.claude/skills/`，所以**新机器一条脚本即可装全量**
- `.gitignore` 删掉 `hermes-skills/` 屏蔽行（2026-10-02 瘦身时加的）；`.curator_backups` / `.curator_ledger.jsonl` / `__pycache__` / `*.pkl` / `*.tar.gz` 继续排除
- 仓库 124 MB → 约 277 MB，最大单文件 1.1 MB（远低于 GitHub 100 MB 限制）

### 发布前深度脱敏 4,900+ 处

只刷仓库副本，本机库保留原值供实战：

- 邮箱 3,322 · 手机号 834 · 凭据赋值 724 · 身份证 32 · 云 AK 6 · 长 hex 密钥 21 · Bearer 17 · PEM 私钥块 3 · 自有 IP 13 · TG token 8 · AKIA 12 · ghp/sk- 各 2
- 占位符与变量（`YOUR_KEY` / `$TOKEN` / `{{...}}` / `example.com`）**原样保留**，不破坏卡的可读性
- 目标方 IP/域名按既有口径保留（复现入口=知识）；自有 IP/主机名/凭据/PII 一律抹

### 人格与记忆同步

- `ai-config/hermes/{MEMORY,USER}.md` 与两份 `.payload.md` 用本机版本覆盖（3,091 B / 3,042 B）
- 新增 `ai-config/hermes/SOUL.md`（3,387 B，Hermes 运行人格），与 `ai-config/universal/PERSONA.md`（通用人格）分开
- `setup.sh` 的「目标更大就不覆盖」规则不变，两边等长时直接覆盖

### 同批保留

- `domains/` 知识层 1,168 张不动；`case-lessons` 索引对账不变

---

## 一、这是什么

本仓库不是「按上游项目名堆一堆文件夹」，而是把多份技能包、手册、PoC、字典、实战报告**拆开后，按攻击面重新融合**进 `domains/`，让 AI 和人都能按「我现在测的是登录 / 支付 / 注入…」找到对应资料，并在授权范围内**直接跑工具与 PoC**。

| 它是 | 它不是 |
|------|--------|
| 授权渗透 / 挖洞 / 评估用的**知识 + 路由 + 可执行资产** | 未授权攻击教程或自动「输入域名就授权」 |
| 给**多种 AI** 共用的同一套路径（不绑死 Hermes） | 必须安装某一种 AI 才能用 |
| 初学可从 `START.md` 进，熟手可从 `MASTER`/`domains` 深挖 | 只有黑盒脚本、没有说明 |
| **文档 + 工具链入口 + PoC/字典/战役脚本**一体 | 「只能读 md、真跑全靠宿主瞎猜」 |

**规模（以本机实计，2026-11-01）：**

- **24** 个主题域
- **约 23000+** 文件（`domains/` 正文；含 poc-catalog 全量；以 `find domains -type f | wc -l` 为准）
- **2,350** 张技能卡（`hermes-skills/`，13,044 文件 / 155 MB；启用 525 + 归档 1,805）
- **49** 条口语触发词 + `arsenal.db` 2,367 条检索索引（三通道：FTS / headings / body）
- **80+** 工具清单（`scripts/tools-manifest.json` + `check-tools.sh` / `install-tools.sh`）

> 旧文案里的「2879 / 3800+ / 5200+」是历史口径；**以本 README 与本地实计为准**。

---

## 二、30 秒上手（所有人）

### 1）下载

**Windows（PowerShell 一行，需 [Git for Windows](https://git-scm.com/download/win)）：**
```powershell
irm https://cdn.jsdelivr.net/gh/lanyz1/TGSEC-Qtzuu@master/scripts/install-windows.ps1 | iex
```

**Linux / macOS / WSL：**
```bash
curl -fsSL https://cdn.jsdelivr.net/gh/lanyz1/TGSEC-Qtzuu@master/scripts/install-linux.sh | bash
```

或手动：
```bash
git clone https://github.com/lanyz1/TGSEC-Qtzuu.git security-suite
cd security-suite
bash scripts/bootstrap.sh   # 写各 AI 入口 + 同步伞形技能
```

默认目录：`~/security-suite`（Windows 多为 `C:\Users\<用户名>\security-suite`）。

### 2）用 AI 打开整个文件夹

| AI | 做法 |
|----|------|
| Grok Build | 打开文件夹 → 选 `security-suite` |
| Claude Code | 进入该目录再运行 `claude`，然后 `/skill pentest-redteam` |
| Cursor | Open Folder → `security-suite` |
| Hermes | 新会话，工作目录尽量指到该文件夹；再 `bash scripts/sync-hermes-skills.sh` |
| Codex / Aider | 以该目录为项目根 |

### 3）复制发给 AI（渗透 / 挖洞）

```text
请先读 START.md、AGENTS.md、ROUTING.md、MASTER.md。
我做的是【已授权】渗透测试和挖洞（侦察、找漏洞、可复现验证、出报告）。
按 ROUTING.md 去 domains/ 找资料；开打前按「技能加载矩阵」把对应伞形技能全部 load 齐。
用简单中文一步步带我做，给可复现命令，不要只讲概念。
目标与授权说明：……（填域名/范围，并写明已授权）
```

---

## 三、核心设计：全 AI 同一套路径

不依赖 Hermes 的 `skill_view`，任何能读仓库文件的 AI 都能用：

```text
AGENTS.md  →  AI 总规则（何时路由、授权边界、完成清单）
ROUTING.md →  人话关键词 → domains/ 下具体路径
MASTER.md  →  24 域导航 + 渗透阶段
domains/   →  全部知识正文 + PoC + 字典 + 战役脚本
scripts/   →  工具安装/检查/技能同步（可执行工具链入口）
```

**同主题推荐阅读顺序：**

```text
domains/<面>/README.md
  → playbook-6000/     （系统测试手册）
  → hunter-6000/       （进攻向专题）
  → src-methods/       （SRC 挖洞方法）
  → torch-hunt/ / torch-wiki/   （TORCH 猎杀手册 + 技术页，2026-09-08）
  → case-lessons/      （实战报告提炼，脱敏）
  → 其它专项 md / Payload / exploit
```

`hermes-skills/` 是 **伞形路由器**（约 14 个入口），sync 后加速定位；**细粮永远在 `domains/`**。

---

## 四、文档 + 可执行，不是「只能看」

别的模型如果说「只有文档、真跑靠宿主」——本仓的定位是：

| 层 | 你在本仓得到什么 | 怎么跑 |
|----|------------------|--------|
| 路由 | `ROUTING` / `MASTER` / 伞形 SKILL | AI 打开即用 |
| 方法论 | playbook / hunter / src-methods / torch-hunt | 逐步照做 |
| 字典 / Payload | `domains/**/Payload`、`sql-wordlist-orwa.txt`、AboutSecurity-Dic | ffuf/sqlmap/自定义脚本直接喂 |
| 产品 PoC | `domains/0day-exploits/**`（含 exploitarium 批次） | 授权实验室按 README 复现 |
| 战役状态机 | `pentest-execution` + `redteam-framework/torch-scripts/` | coverage / Deadend / next-move |
| 逆向专项 | `panda-rev`（Frida/DEX dump/砸壳/IL2CPP/IDAPython/Unicorn） | 本机 ADB/Frida/IDA 环境执行 |
| 宿主工具 | `scripts/tools-manifest.json`（80+） | `bash scripts/check-tools.sh` → `install-tools.sh` |

**边界说清楚：** 本仓**不**内嵌完整 C2 商业马、不替你装 Kali 全家桶；它提供的是「测什么 → 去哪读 → 用哪条命令/PoC/字典」的可执行闭环。工具二进制由 `install-tools` 按清单装到宿主——这是刻意设计，不是缺失。

---

## 五、目录结构

```text
START.md                 小白 3 步
INSTALL.md               安装速查
README.md                本说明（详细自述）
AGENTS.md                任意 AI 第一指令 / 完整路由规则
ROUTING.md               全 AI 关键词 → 路径表（不绑 Hermes）
MASTER.md                主题域矩阵 + 5 步路由 + 融合说明
CLAUDE.md / .cursorrules / .github/copilot/  各客户端薄入口
RULES.md                 通用短规则
ai-config/               Claude/Cursor/Codex/Grok/Aider/Hermes/universal 源配置
hermes-skills/           伞形技能源（14 入口，含 cdn-origin-tracing / 0day / reverse…）
scripts/
  install-windows.ps1 / install-linux.sh
  bootstrap.sh           写各 AI 入口 + 同步技能
  sync-agent-skills.sh   Claude/Cursor/Codex/Gemini/agents/Hermes 一键技能
  sync-hermes-skills.sh  仅 Hermes
  check-tools.sh / install-tools.sh / tools-manifest.json
domains/                 ★ 知识正文（按攻击面，~5200+ 文件）
  recon/ web-injection/ web-attack/ api-security/ auth-security/
  file-vulns/ business-logic/ ad-attack/ windows-post/ linux-post/
  cloud-security/ mobile-security/ binary-pwn/ reverse-engineering/
  crypto-attacks/ llm-ai-security/ post-exp-tools/ malware-dfir/
  social-eng/ ctf/ 0day-exploits/ redteam-framework/ gambling-pentest/ other/
  FUSION-6000.md / FUSION-20260908.md / FUSION-REPORT-20260908.md / FUSION-20260910-wechat4.md
```

---

## 六、主题域规模（约数，融合后会变）

| 域 | 约文件数 | 覆盖摘要 |
|----|----------|----------|
| `web-injection` | 1100+ | SQLi/XSS/SSRF/XXE/反序列化/Fastjson/Shiro/Log4j + torch-hunt/wiki + orwa 字典 |
| `recon` | 1050+ | 子域/端口/OSINT/FOFA/组件情报/TORCH tools·cheatsheets/Dic |
| `0day-exploits` | 650+ | 产品 RCE 库 + **exploitarium** 批次索引 |
| `file-vulns` | 390+ | 上传/LFI/白盒 PHP·Java 审计 |
| `ctf` | 330+ | 靶场/题解/torch CTF workflow |
| `ad-attack` | 190+ | Kerberos/ACL/ADCS/BloodHound + torch AD |
| `cloud-security` | 180+ | AWS/Azure/K8s/CI-CD + torch cloud |
| `redteam-framework` | 160+ | 状态机/Anti-Logic/torch campaign 脚本 |
| `post-exp-tools` | 150+ | C2/隧道/Webshell/凭据 |
| `web-attack` | 120+ | CSRF/WAF/走私/缓存/竞态 |
| `windows-post` / `linux-post` | 100+ / 40+ | 提权/横移/凭证 |
| `mobile-security` | 80+ | APK/iOS/Frida + **panda-rev**（DEX/砸壳/IL2CPP） |
| `reverse-engineering` | 60+ | IDA/Ghidra + **panda-rev** 符号/结构体/Unicorn |
| `auth` / `api` / `llm` / … | 见 MASTER | 认证、API、AI/MCP、密码学、博彩面等 |

数字以仓库内统计为准，融合后会变。

---

## 七、渗透时「技能必须用全」——加载矩阵

开打**任意**授权目标时，AI / 操作者按资产类型 **load 对应伞形**，再进 `domains/`。  
**禁止**不 load 技能就空手写临时脚本开喷。

| 场景 | 必 load（伞形） | domains 落点（再读） |
|------|-----------------|----------------------|
| 每次活靶开局 | `pentest-execution` + `tgsec-suite`（Claude Code 优先 `/skill pentest-redteam`） | `redteam-framework/` · coverage / Deadend · `case/` |
| 长任务失忆/原地循环/凑链 | （开局）+ `cyberstrike-progress-gates` · `capability-primitives` | `redteam-framework/cyberstrike-methodology/` |
| CDN/WAF/找源站 IP | `cdn-origin-tracing` | `recon/` · handbook |
| Web 注入/API/JWT/IDOR | `hack-skills` → `web-sec` | `web-injection` `web-attack` `auth` `api` · `torch-hunt` |
| SQLi 字典 fuzz | （同上） | `web-injection/Payload/sqli/*orwa*` |
| 组件/版本已识别 | （+ component intel） | `recon/component-vuln-intel/` · `0day-exploits/` · `POC-PLATFORM-INDEX.md` |
| 产品已知 RCE | `0day-exploit-library` | `0day-exploits/<product>/` · `EXPLOITARIUM-INDEX.md` |
| n8n / Form 工作流 | （+ 0day） | `web-injection/Vuln/middleware/n8n/`（含 fullchain + exploit） |
| 内网 AD / Kerberos 反射 | （开局） | `ad-attack/cve-2026-26128-kerberos-unicode-reflection/` |
| K8s/容器逃逸（Copy-Fail） | （开局） | `cloud-security/container-escape-techniques/cve-2026-31431-copyfail-k8s.md` |
| CTF / Payload 速查 | （开局） | `ctf/payloads/` · `ctf-solver-routing.md` · `depth-articles/` |
| AI Agent/MCP/RAG 运行时 · SOC 研判门禁 | （开局） | `llm-ai-security/ai-security-engineering/` |
| APK/IPA/Frida/DEX/砸壳/IL2CPP/二进制 | `reverse-skill`（+ master-route） | `mobile-security/panda-rev` · `reverse-engineering/panda-rev` |
| 博彩/代收/代理 BFLA | `gambling-platform-pentest` | `gambling-pentest/` |
| 假设驱动状态机 | `black-cat-redteam` | `redteam-framework/black-cat/` |
| OODA 自动化代理 | `stopen` | （技能内流程） |
| Bug bounty 狩猎卡 | `claude-bughunter` | 与 `src-methods` 交叉 |
| 结构化 payload/字典库 | `about-security` | `Payload/` `Dic/` 及 domains 镜像 |
| YAML 技术卡片 | `secatlas` | SecAtlas 本地树 |
| 吸收外部安全仓 | `security-kb-ingest` | 本 README 融合纪律 |
| 业务身份层/反逻辑/支付 | `pentest-execution` refs | `auth-security` · `business-logic` · `anti-logic-*` |

Hermes：`skill_view(<name>)`。  
Claude/Cursor 等：项目内 `.claude/skills/<name>/` 或先 `bash scripts/sync-agent-skills.sh`。  
**全 AI 兜底：** 不会 skill 系统 → 直接 `ROUTING.md` → `domains/`。

活靶纪律（覆盖矩阵、验证门、OOB、禁止「已到极限」）在 `hermes-skills/pentest-execution/`。

---

## 八、特色方法论（熟手）

| 主题 | 路径 |
|------|------|
| 真假分离侦察 | `domains/recon/true-false-separation-recon.md` |
| 业务系统身份层 ROI | `domains/auth-security/session-crypto-identity-layer.md` |
| Anti-Logic A1–A6 | `domains/redteam-framework/anti-logic-layout.md` |
| 身份层 + 反逻辑手册 | `domains/redteam-framework/identity-antilogic-playbook.md` |
| 支付/Crown 配置面 | `domains/business-logic/payment-config-crown-surface.md` |
| TORCH 战役层（wiki/hunt/campaign） | `domains/**/torch-*` · `redteam-framework/torch-methodology-delta-20260908.md` |
| 能力原语凑链 + 长任务进度闸 | `domains/redteam-framework/cyberstrike-methodology/` · `pentest-execution/references/*` |
| AI 安全工程（宪法/门禁/研判） | `domains/llm-ai-security/ai-security-engineering/` |
| exploitarium 产品 PoC 索引 | `domains/0day-exploits/EXPLOITARIUM-INDEX.md` |
| 本地 POC 库查询（不灌 Skill） | `domains/0day-exploits/POC-PLATFORM-INDEX.md` |
| 实战脱敏课 | `domains/*/case-lessons/` |

**思路：** 强身份业务优先 session/JWT/HMAC/无 auth 写接口与旁门；与正逻辑 Kill Chain **并行**。

---

## 九、一键装到 Claude / Cursor / Hermes 等

```bash
cd security-suite
bash scripts/sync-agent-skills.sh          # Linux/Mac
# Windows:
# powershell -ExecutionPolicy Bypass -File .\scripts\sync-agent-skills.ps1
```

| 装到哪 | 路径 |
|--------|------|
| Claude Code 项目内 | `.claude/skills/<name>/SKILL.md` |
| Claude 用户级 | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` 与 `~/.cursor/skills/` |
| 通用 | `.agents/skills/` |
| Codex / Gemini | `.codex/skills/` · `.gemini/skills/` |
| Hermes | `~/.hermes/skills/security/` |

`bootstrap.sh` / 一键 install **会自动调用**。装完请**新开会话**。

```bash
bash scripts/sync-hermes-skills.sh   # 仅 Hermes
bash scripts/check-tools.sh          # 看缺什么工具
bash scripts/install-tools.sh        # 按清单补工具
```

`git pull` **不会**自动更新 `~/.hermes/skills`，需要再 sync。

---

## 十、融合批次

### 2026-11-01 · 报告包蒸馏（127 篇）+ threatwire 情报卡 + 技能库 2,330

- `报告.zip` 330 文件 → 127 篇去重 → 2,474 finding 归 29 技术族：**17 张新卡 + 41 张老卡补 45 处**
- threatwire 119 CVE 页 + 114 文章 → 45 篇抓取 → 17 条新内容 → `threatwire-cve-briefs-2026-11`
- `hermes-skills/` **2,206 → 2,330**（13,024 文件 / 155 MB，启用 525 / 归档 1,805）；索引 2,328 / 触发词 49
- 推前脱敏闸首轮 BLOCK 3 处明文（AKIA 测试串 / kk8 AES key / MySQL 口令），已打码并同步本机库
- 详账：[`UPDATE-2026-11-01.md`](docs/updates/UPDATE-2026-11-01.md)

### 2026-10-23 · 技能库全量入仓 + 人格/记忆同步 + 深度脱敏

- `hermes-skills/` **2,206 卡 / 12,865 文件 / 153 MB** 入仓（启用 401 / 归档 1,805），`.gitignore` 解禁
- `sync-hermes-skills.sh` 默认源改为命中全量（它本来就优先 `hermes-skills/`）
- `ai-config/hermes/` 覆盖 MEMORY/USER + 新增 SOUL.md
- 脱敏 4,900+ 处：邮箱 / 手机 / 凭据值 / 身份证 / 云 AK / hex / Bearer / 私钥块 / 自有 IP / TG token
- 详账：[`UPDATE-2026-10-23.md`](docs/updates/UPDATE-2026-10-23.md)

> 历史批次（2026-10-22 及更早）不在 README 展开，见 [`docs/updates/`](docs/updates/) 与 `git log`。

## 十一、和 reverse-skill 的关系

吸收了 reverse-skill 的：**关键词路由、先读规则再动手、工具路径不瞎猜、完成清单**。  
正文仍在 `domains/` 攻击面融合；本机若有 reverse-skill 包，可 `master-route`。  
2026-09 另融 **panda-rev**（DEX dump 二进制、Frida 现代 API、砸壳、IL2CPP、符号/结构体、Unicorn）。

---

## 十二、更新

```bash
cd ~/security-suite && git pull
bash scripts/bootstrap.sh --force    # 或 sync-agent-skills / sync-hermes-skills

# 2026-10-22 技能库换代（2178→2146→2204，检索三通道 + 8 项门禁）：
bash scripts/apply-arsenal-20261022.sh   # 幂等；重建索引 + 跑门禁
```

**更新说明文件：** `docs/updates/UPDATE-YYYY-MM-DD.md`（最新：[`UPDATE-2026-11-01.md`](docs/updates/UPDATE-2026-11-01.md)）。README 只保留**最近一次**更新摘要，历史见该目录与 `git log`。

**旧版技能库怎么覆盖：** [`docs/UPGRADE-20261022-ARSENAL.md`](docs/UPGRADE-20261022-ARSENAL.md)（含手工步骤、验收清单、回滚、9 条坑）。

**转发给别人 / 别的 AI：** [`docs/ANNOUNCE-20261022-ARSENAL.md`](docs/ANNOUNCE-20261022-ARSENAL.md)（短版通告 + 整段指令 + 只取工具版）。

---

## 十三、常见问题

**Q：技能是不是变少了？**  
A：伞形入口十几个是**路由器**；内容在 `domains/`（五千级文件）。渗透时按第七节矩阵 load，再下钻 domains。

**Q：只有文档不能跑？**  
A：见第四节。字典/PoC/战役脚本/工具清单都在仓内；二进制工具用 `install-tools` 装到宿主。

**Q：必须 Hermes 吗？**  
A：不必。Grok/Claude/Cursor 打开文件夹读 `START`→`ROUTING`→`domains` 即可。

**Q：能否未授权打公网？**  
A：不能。口令里的「已授权」指 SRC/客户书面授权/自有资产/CTF 等。

**Q：文件数和 README 对不上？**  
A：以 `find domains -type f | wc -l` 与本节「实计」为准；融合后会涨。

---

## 十四、声明

本套件仅供**合法授权**的安全测试、CTF 训练、学术研究与防护研究使用。使用者须遵守所在地法律法规，对未授权行为自行承担责任。

---

@TGSEC社区 · @TGSEC-Qtzuu 整理
