# security-kb-ingest — 全文续篇

> 主卡保留前 3 节；本文件从第 4 节起。原文件：`/root/.hermes/skills/security/security-kb-ingest/SKILL.md`

## Archived repos (as of 2026-09)

| Repo | Local path | Notes |
|---|---|---|
| hack-skills (yaklang) | /root/hack-skills | 102 SKILL.md, router: `hack-skills` |
| SecAtlas (shuaiqideyu) | /root/SecAtlas | YAML technique cards, router: `secatlas` |
| reverse-skill (local) | /root/reverse-skill | routing engine; Hermes router: `reverse-skill` |
| CVE-2026-65343 iOS kernel batch | /root/TGSEC-Qtzuu/domains/mobile-security/ios-kernel-cve | ANALYSIS only; fused into mobile-security |
| 6000RMB skills.zip (2026-09-03) | fused into domains/*/playbook-6000+hunter-6000 | 145 new/83 dedup; FUSION-6000.md |
| AboutSecurity (wgpsec) | /root/AboutSecurity | 68MB, 1884 files, router: `about-security` |
| Claude-BugHunter | /root/Claude-BugHunter | 83 hunt skills, router: `claude-bughunter` |
| Stopen | /root/Stopen | OODA pentest agent, router: `stopen` |
| web-sec (ReAbout) | /root/web-sec | EXP/VUL/PEN 3-layer, router: `web-sec` |
| skill dir (local) | /www/wwwroot/skill | content churn expected; router: `skill-arsenal` |
| Black-cat (0rangec3t) | /root/Black-cat | Hypothesis-driven state-machine pentest framework; 7 technique dirs (web/recon/cloud/db/reversing/ad/evasion); router: `black-cat-redteam` |
| 0day-Rubbish (Exploit-Garbage) | /root/TGSEC-Qtzuu/domains/0day-exploits | 76 products, 90 RCE vulns, each with exploit/*.py + analysis.md + summary.md; router: `0day-exploit-library` |
| Redis CVE-2026-81934 PoC (berabuddies) | /root/TGSEC-Qtzuu/domains/0day-exploits/redis/CVE-2026-81934 | Redis TLS UAF→RCE, CVSS 9.8, exploits for 6.2/7.4/8.6/8.8; merged into 0day-exploit-library |
| RuoYi-Vue-Plus tenant_id SQLi (2026-09-02) | /root/TGSEC-Qtzuu/domains/0day-exploits/ruoyi-vue-plus/ | Pre-auth SQLi via POST /auth/register tenantId; Error-based extractvalue; merged into 0day-exploit-library |
| clown-src-6k-skill (SRC methods) | merged into 9 domains | 49 vuln test methods + 11 rules + FOFA MCP; fused into web-injection/web-attack/auth-security/file-vulns/recon/etc. src-methods/ subdirs |
| PHP-Code-Audit-Skill | domains/file-vulns/code-audit/php/ | Fine-grained PHP route-mapper/tracer + class audits; kept aggregated php-*-audit |
| java-audit-skills | domains/file-vulns/code-audit/java/audit-skills/ | Workspace convention + component YAML + evidence gate |
| code-audit (methodology) | domains/file-vulns/code-audit/methodology/ | 55+ types, dual-track, anti-hallucination |
| WinDump | domains/windows-post/windump-cred-collection/ | Client cred/host collection playbook (source+docs) |
| lpe-toolkit | domains/linux-post/lpe-toolkit/ | Multi-arch LPE orchestration; exploit binaries NOT vendored (INDEX only) |
| Payloader content | domains/recon/.../payloader/ | UI skipped; content-review-upstream + existing by-category |
| Pentest-WindFtsy | domains/redteam-framework/web-assess-pipeline/ | mitm URL dump + auth matrix + gate truth |
| recon-skills | domains/*/src-methods/ | Incremental hunt/recon skills; richer overlaps → references/upstream-* |
| BB Methodology 2026 | recon/src-methods + cdn-origin-tracing refs | Origin-IP/CDN excerpts only + full README ref |
| DroidHunter | domains/mobile-security/android-adb-assess/ | ADB/modules playbook; product shell not routed |
| ctf-skills | domains/ctf/ctf/ | Gaps + richer upstream refs for overlaps |
| claude-bug-bounty | selective src-methods | Diff vs Claude-BugHunter; only incremental skills |
| AutoCVE skill_library | domains/file-vulns/code-audit/autocve-skill-library/ | skill_library only; AGPL platform skipped |
| Anthropic-Cybersecurity-Skills | OT/ICS, phishing-IR, compliance, IAM, SIEM thin domains | Curated ≤60 skills; not full 800+ dump |
| cdn-origin-tracing handbook | hermes-skills/cdn-origin-tracing | CDN/WAF origin tracing skill + scripts |
| TORCH (Encod3d-Sec) methodology extract 2026-09-05 | fused into `pentest-execution` references | **Not full clone.** Absorbed: engagement-state, coverage-classes, campaign-loop, confirmation-gate, oob-callbacks. Skipped: Claude hooks/Obsidian/qmd/wiki dump |
| pentest-pro-skills (manbamax) gates extract 2026-09-05 | fused into `pentest-execution` + anti-logic | **Not 13-skill dump.** Absorbed: validation-gates (6-door), 判定优先/版本≠漏洞, dual-session BOLA notes. Skills4RedTeam index-only skipped |


| TORCH full absorb 2026-09-08 | domains/*/torch-wiki|torch-hunt|torch-workflow + redteam-framework/torch-scripts | Full wiki+hunt; still skip Claude hooks/Obsidian/qmd bootstrap |
| P4nda0s reverse-skills 2026-09-08 | domains/reverse-engineering|mobile-security/panda-rev + reverse-skill/skills/rev-* | 8 RE skills + dex dumper binary |
| SQL-Wordlist (orwa) 2026-09-08 | web-injection/Payload/sqli/*orwa* ; /root/SQL-Wordlist | sql.txt fused; everything.txt path-only |
| bikini/exploitarium 2026-09-08 | 0day-exploits/<product>/exploitarium/ + EXPLOITARIUM-INDEX.md | ~40 public PoCs by product |
| AboutSecurity / hack-skills re-verify 2026-09-08 | /root/AboutSecurity · /root/hack-skills | origin already current; Payload/Dic/Vuln delta sync |

| WeChat4+AI安全工程+CVE/CTF 2026-09-10 | domains/redteam-framework/cyberstrike-methodology · llm-ai-security/ai-security-engineering · ctf/* · web-injection/.../n8n fullchain · ad-attack/cve-2026-26128-* · cloud-security/.../copyfail-k8s · 0day-exploits/POC-PLATFORM-INDEX | **Not full dump.** Methodology+selective PoC/CTF; skip Awesome-POC 1.7G & platform UI |
| FUCK-CDN (0xShe) 2026-09-12 | /root/FUCK-CDN | Single-file CDN origin-IP playbook (P0–P4 tiers + 15-vendor bypass + cert-serial decision table); absorbed → `../cdn-origin-tracing/references/p0-p4-priority-playbook.md` |
| CVE-2026 KEV batch 2026-09-23 | domains/0day-exploits + INGEST-20260923-INDEX.md | V8 85046/87491 JS harness fused; PaperCut 81578/82078 + Cisco 76461 + Win 85880/81963 ANALYSIS_ONLY_KEV. Skip mock ISE/SEG labs + aggregators |
| CVE-2026 独立仓 09-23b/c | domains/0day-exploits + INGEST-20260923{B,C}-INDEX.md | HIT≠完整吸收：USBPrint 从 ghost-cms 搬出；Copy-Fail 补 K8s Go；Tomcat 补 lab sh；RustyTux/FMC/Zabbix/SGLang 等 MISS harness。SecureWithUmer stub 整仓 SKIP |
| CVE-2026 独立仓 09-23d/e | INGEST-20260923{D,E}-INDEX.md | Forminator 92229；macOS DesktopServicesHelper 43783；copyfail-rs PAM；sergiointel 建超管；vCenter 59309 checker。用户再问整仓：再抽≥8 仍 stub 则仍 SKIP；Dullpurple=Win exe 投毒页 |
| murrez 独立仓 7 CVE (2026-09-28) | domains/0day-exploits/ + INGEST-20260928-INDEX.md | 本地全库 MISS → 7/7 POC_FUSED。NetScaler DTLS 88772 · Joomla UP 97163/97160/97161 · AcyMailing 94132 · WP Ultra Addons 82901 · WP Bookly 93399。**Joomla 产品线全新**；Citrix 补 DTLS/UDP 面。harness 413–659 行无 stub |
| 最优吸收 B 批 (2026-09-28B) | domains/0day-exploits/ + INGEST-20260928B-INDEX.md | 60 URL → 17 目标全 MISS。网络设备/容器逃逸/MikroTrick 等 |
| xishou 全量技能蒸馏 C 批 (2026-09-28C) | .hermes/skills/security/ + INGEST-20260928C-INDEX.md | **908 新 skill → 技能库 113→1022**。Wave1 测绘引擎(673) + Wave2 PSM差量(235) + Wave3 72stack-sec(45MB/2836 H1/88636 WooYun)。hunt-*(70+) · offensive-*(60+) · 专项渗透(200+) · 基础能力(150+) |
| gpu-root-persistence-pack v1.1 (2026-09-28) | 5 skills installed to .hermes/skills/security/ (pending) | GPU 猎杀全链：venom-root(投毒+CVE+免杀+扎根) · venom-hydra(九头蛇不灭) · immortal-pact(七层重生) · undying-persist(11路触发) · gpu-hunter(FOFA测绘+多路径root)。载荷13个。ComfyUI/Docker/GPUStack/Ray/Jupyter/Ollama/K8s 服务面RCE |
| EQSTLab 46仓 triage (2026-09-30) | `/tmp/eqst/` (22 cloned, pending fusion) | 46 CVE PoC 仓批量评估：15 HIT（Next.js/GitLab/Langflow/Fastjson/Kestra/Gitea/Tomcat/Struts2/XXE）、9 高价值 MISS（Metabase 72898 SQLi CVSS10/Keycloak 18963 ATO/HTTP2 Bomb 49975/GiveWP 5932 RCE/pfSense 46538 XSS→RCE/Math.js 40897 沙箱逃/simple-git 6951 RCE/Handlebars 33937 AST注/Ghost 26980 SQLi）、13 中等 MISS。用户已确认“需要看 poc”，待融合 |
| 报告.zip+微信三篇 2026-09-23 | 2 新 Skill + 6 课 + CASE-INDEX 62 | 82vip ll-center；Kylin/ucard；DarkSword JackApple 指纹；aqlm/xmnyme 课。2FA/glob 译文不开 Skill。GitLab 85706 已在库。pack 内账密 SKIP |
| cvebird 增量批 2026-10-08 | /root/cvebird-20261008-triage.md（triage 已交付，待拍板） | 窗口 #16999→#17100=102 帖。P0：corunalab/coruna（iOS 收割 C2 框架本体）、wobushilixi/lixi-nixiang-skill（卡密逆向完整包）、daniel875147-crypto/Darksword；P1×4（CipherBridge/PrivHunterAI/AgentSuite/code-audit-playbook）；P2：ARTEX 镜像×16 仅提炼 api-recon 一页；可疑投毒 1（dirbuster 勿运行）。待用户「按最优吸收」 |
| abraxas 158仓 triage 2026-10-12 | `references/abraxas-158repo-triage.md`（✅ 已全量吸收 2026-10-12；账本 `INGEST-20261012-INDEX.md`） | 158 仓全对账：~120 真缺口（SQLite×14 / phpMyAdmin×11 / CakePHP×7 / MySQL×6 / VFS×6 / CVE类×26+ / Moodle·Drupal·Joomla·Forgejo 各×4）+ 工具类（veneficus / ShieldCrash / Chrome ABE / Fortigate kit）。P0=全量收 + AnyDesk AnyPwn 补 v12-security-pocs |
| lanyz1/TGSEC-Qtzuu 全量回流 2026-11-05（Windows / DSH 主机） | `tgsec-kb/` + `INGEST-2026-11-05-WINDOWS-INDEX.md` | 源 = GitHub master tar 快照（README 2026-11-05，2,350 卡）。`robocopy /E /XO` 增量镜像：**+43,399 文件 / 453 MB**，本地独有 **2,909 文件 / 75 MB** 保留未删（0day-exploits 14,591 / recon 1,924 等本地富集面）。技能层 30 张伞形更新（pentest-execution 28→153、web-sec 1→44、security-kb-ingest 8→19、0day 1→12、cdn 8→23、reverse 2→8）；新建 `tgsec-arsenal-router`（Windows 检索入口 `tools/cardfind.cmd`）。arsenal.db **2,348 卡**（enabled 574 / disabled 1,774 / legacy 1,856 / 354 MB），新卡实测 Top1 命中 6/6 |

## Integration vs stacking (critical user correction)

User explicitly rejected repo-stacking (`knowledge/<repo-name>/` per source) as "not integrated".
Correct approach: **domain-based reorganization** — flatten ALL repos into `domains/<attack-surface>/`
where each theme (recon, web-injection, api-security, ad-attack, etc.) aggregates content from
every source. Each domain gets a README.md index. A `MASTER.md` at root provides the 21-theme
navigation matrix.

Workflow: write a Python script that maps every source directory to a target theme, then
`shutil.copytree` (skip `.git/`) into `domains/<theme>/<original-dir-name>/`. Generate per-theme
README + MASTER.md via a second script. Delete the `knowledge/` stacking structure entirely.

## SRC Knowledge Fusion (clown-src-6k-skill pattern)

When absorbing SRC/bug-bounty methodology repos (e.g. clown-src-6k-skill, 49 vuln test methods + 11 rules):

1. **Map each file to existing domain** — don't create a new standalone domain:
   - injection-test/xss/xxe/ssrf/deserialization/el-injection/jndi → `web-injection/src-methods/`
   - http-smuggling/csrf/cors/waf-bypass/cache-poisoning/race-condition → `web-attack/src-methods/`
   - authbypass/idor/oauth-jwt/401-403-bypass → `auth-security/src-methods/`
   - file-upload/path-traversal/insecure-scm → `file-vulns/src-methods/`
   - recon-methodology/info-leak/subdomain-takeover/js-reverse → `recon/src-methods/`
   - Rules/workflows → `recon/src-rules/`
   - Tools (FOFA MCP, Playwright) → `recon/tools/`
   - logic-test → `business-logic/src-methods/`
   - llm-security/agent-tool-exec → `llm-ai-security/src-methods/`
   - cloud-ide-rce/dependency-confusion → `cloud-security/src-methods/`
   - api-gateway → `api-security/src-methods/`

2. **Subdirectory convention:** place merged files in `<domain>/src-methods/` to separate from original domain content
3. **Delete the staging directory** after all files are distributed — no leftover standalone domain
4. **User will reject stacking:** creating `domains/src-hunting/` as a standalone dump was explicitly rejected ("都融合了还是单独的啊"). Always merge by attack surface.

## Multi-AI Tool Config Distribution

When the repo needs to support multiple AI CLI tools (not just Hermes):

```
ai-config/
├── universal/          # Core configs (any AI tool)
│   ├── PERSONA.md      # Red team persona + rules + pentest flow
│   ├── MEMORY.md       # Attack surface priorities + platform signatures
│   └── RULES.md        # Execution rules + output style
├── hermes/             # ~/.hermes/memories/ (setup.sh extracts code blocks)
├── claude/             # CLAUDE.md (project root) — Claude Code auto-reads
├── codex/              # instructions.md → .github/copilot/
├── grok/               # system.txt → ~/.grok/
├── cursor/             # .cursorrules (project root)
└── aider/              # .aider.conf.yml (project root)
```

**Key patterns:**
- `universal/` holds the canonical content; tool-specific files are condensed derivatives
- Hermes uses `setup.sh` that extracts last ``` code block from USER.md/MEMORY.md
- Claude Code reads `CLAUDE.md` from project root automatically
- Cursor reads `.cursorrules` from project root automatically
- When updating vuln signatures (e.g. new RuoYi SQLi), update ALL tool configs in one commit
- AGENTS.md at repo root guides any AI to auto-install the right config for its tool type

## Branding & upstream stripping

User requires ALL upstream author names, repo references, and agent identifiers be removed:
- Git history rewrite: `git filter-branch --env-filter` to replace author/committer with user's identity
- File content: `sed -i` to replace mule/BlackMule/Hermes/upstream-repo-names with user's brand
- Script filenames: rename `mule-*.sh` → `tgsec-*.sh` (or user's chosen prefix)
- YAML fields: replace agent IDs inside case/technique YAML files
- Skills SKILL.md: strip `(yaklang/hack-skills, depth-1)` style parenthetical source attributions
- Final grep sweep: `grep -ri` for ALL known upstream identifiers, fix any remnants
- User's brand format: `@TGSEC社区 · @TGSEC-Qtzuu 整理` (bottom of README/AGENTS/MASTER)

## GitHub archive push

To archive the suite to the user's repo, see `references/github-token-push.md` — token
capability probing sequence, fine-grained-PAT limits, and the push recipe.

## Renaming repos on GitHub

Use GitHub API: `POST /user/repos` to create new name, push to it, then
`DELETE /repos/:owner/:old-name` to remove the old one. Avoid `PATCH` rename
if commit history needs rewriting (author change) — a fresh repo is cleaner.

## Multi-AI Tool Configuration Distribution

When building a security knowledge repo intended for AI consumption, create `ai-config/` with per-tool configs:

```
ai-config/
  universal/          — PERSONA.md + MEMORY.md + RULES.md (any AI tool)
  hermes/             — USER.md + MEMORY.md + setup.sh (writes to ~/.hermes/memories/)
  claude/             — CLAUDE.md (project-root, auto-read by Claude Code)
  codex/              — instructions.md (.github/copilot/ or env var)
  grok/               — system.txt (~/.grok/)
  cursor/             — .cursorrules (project-root)
  aider/              — .aider.conf.yml (project-root)
```

**Key lessons:**
- Hermes uses `~/.hermes/memories/USER.md` + `MEMORY.md` — extract code blocks from wrapper docs via `re.findall(r'\x60\x60\x60\n(.*?)\x60\x60\x60', content, re.DOTALL)`
- Claude Code reads `CLAUDE.md` from project root automatically
- Cursor reads `.cursorrules` from project root
- Codex: `instructions.md` in `.github/copilot/` or `COPILOT_INSTRUCTIONS` env var
- aider `.aider.conf.yml` must be valid YAML — don't put freeform prose in value fields
- `AGENTS.md` in repo root should detect which AI tool is running and route to correct config
- Always include `universal/PERSONA.md` as fallback for unsupported tools

## SRC Knowledge-Base Fusion Pattern

When absorbing a vulnerability methodology knowledge base (e.g. clown-src-6k-skill with 49 test methods):

1. **Never stack as a separate domain** — user rejects堆叠("你没有帮我整合起来好吗")
2. **Map each file to an existing attack-surface domain** using a Python dict:
   - injection tests → `web-injection/src-methods/`
   - auth bypass → `auth-security/src-methods/`
   - HTTP smuggling/CSRF/cache → `web-attack/src-methods/`
   - file upload/traversal → `file-vulns/src-methods/`
   - recon/OSINT → `recon/src-methods/`
   - rules/workflow docs → `recon/src-rules/`
3. **Use `src-methods/` subdirectory** in each domain to keep SRC methodology separate from existing content
4. **Delete the temporary standalone domain** after fusion
5. **Tools (FOFA MCP, scripts)** go to `recon/tools/`

## Bulk skill install from local directories (xishou pattern, 2026-09-28)

When a local directory contains hundreds of pre-built SKILL.md files (e.g. `/www/wwwroot/xishou/`):

1. **Scan sources**: identify all directories containing `SKILL.md` files, count total.
2. **Dedup against local**: normalize names (`lower().replace('-','').replace('_','')`) and compare against `~/.hermes/skills/*/SKILL.md`. Protect existing skills — never overwrite.
3. **Quality triage**: classify MISS skills into A(security/pentest), B(report/doc), C(dev/code), D(other) using keyword regex on name + content[:1500]. Report counts per tier.
4. **Wave-based install**: split by source to track provenance. Use `shutil.copytree(src, dst, ignore=ignore_patterns('.git','__pycache__'))`. Verify `SKILL.md` exists post-copy.
5. **Giant skills** (>10MB, e.g. 72stack-sec with 3192 files/45MB): install as-is but call out separately — these contain reference databases (H1 reports, WooYun, payloads) not just methodology.
6. **State files**: save `{wave_installed, skipped_exists, errors, local_norm}` as JSON between waves so Wave 2 knows what Wave 1 added.
7. **INGEST index**: write `INGEST-YYYYMMDDC-INDEX.md` covering wave breakdown, counts, representative skills, and coverage categories.

**Key pitfall**: 1000+ skills makes the Hermes `available_skills` list very long in system prompt. Description matching is O(n) but acceptable if descriptions are short (<200 chars each). The tradeoff is worth it — every attack type gets a matching playbook.

## HIT check / 对账 pitfalls (batch triage)

**glob vs find**: When checking if a CVE exists locally, `glob.glob(f'{LIB}/*/{cve}')` misses paths where the CVE string is embedded in a longer directory name (e.g. `kvm/CVE-2026-53359-Januscape/`). **Use `find -path '*{cve}*'` or Python `os.walk` substring match, not exact glob.** (B-batch 2026-09-28 — Januscape reported MISS, actually HIT.)

**对账池别用 terminal stdout（截断→假 MISS，2026-10-12 abraxas 批）**: 把 `find`/`ls` 经 terminal 工具抓回的 stdout 当匹配池时，大输出（~50KB+）会被静默截断，被截掉的条目全判假 MISS（proftpd/drupal 明明在库却被判 MISS；两次抓取的 pool 还互不一致）。**池子用 execute_code 里 `os.walk(LIB)` 直扫文件系统**，或先落盘再 read_file；对账跑两遍交叉验证，不一致处 = 手工复核点。

**token 噪声（批量 repo 名 → 本地目录）**: 首-token 匹配批量假 HIT —— `cve-*` 仓 token='cve' 命中一切 CVE 目录；'element'→elementor、'sonic'→sonicwall、纯数字 token('2026')→全命中。规则：CVE 仓只搜**完整 CVE 号**；可疑 HIT 翻目录内容复核（sploitus-index 文件名 = 弱命中 ≠ PoC 已收）；**"产品目录存在" ≠ "该漏洞包已收"**（gitea 目录只收了 act-runner，gitea 全系其余仍是缺口）。

## Playbook references

- `references/batch-cve-repo-triage.md` — 批量 CVE/GitHub/Sploitus 吸收前差分：本地 HIT、投毒筛、真缺口 vs 第二 PoC（先告诉我）。**HIT 还要验产品目录/是否错放/是否缺 harness**；聚合仓 stub 农场整仓 SKIP（SecureWithUmer 2026-09-23）。用户「继续吸收」=点名独立仓文件级，不是整仓吸聚合仓。
- `references/cvebird-batch-pipeline.md` — t.me 频道（如 cvebird）增量批处理：t.me/s 免登录抓取解析、增量窗口=上批 INGEST 边界 id+1、轻探三板斧（API 配额检查 / raw.githubusercontent 免配额 / git tree 判型）、四桶分类+决策表格式、镜像洪水与「压缩存根幻觉」坑。配套 `scripts/fetch_tme_channel.py`。
- `references/ruoyi-pentest-playbook.md` — RuoYi-Vue pentest chain (JS extraction → API map → captcha OCR → register → JWT → updatePwd IDOR → user enumeration)
- `references/teo-waf-bypass.md` — TencentEdgeOne WAF JS Challenge static solver (array rotation + integer sum → cookie)
- `references/wordpress-pentest-playbook.md` — WordPress pentest chain (xmlrpc multicall bruteforce, wp-json IP+Host bypass, plugin CVEs, vhost discovery, SPA backend pivot)
- `references/github-token-push.md` — GitHub token capability probing + push recipe
- `references/push-guard-acceptance.md` — 推前守卫（scan_push/verify_final v3 双器）+ 示例级豁免 EXSPEC 标记集 + 推后三件验收（2026-10-12）
- `references/deep-audit-workflow.md` — persistent audit workflow (when to continue vs when to stop)
- `references/abraxas-158repo-triage.md` — abraxas 158仓 triage（2026-10-12）：SKIP/差量/真缺口/工具四桶 + 同批五源决策表，吸收待拍板

## Report absorb: 未覆盖栈 → 新 Skill（第四步硬门）

Absorbing a report pack is **not done** after case-lesson only. Gap gate:

1. Extract stack fingerprints (framework/product/ports/title) from **new** reports only (dedupe by sha).
2. Cross-check `~/.hermes/skills/security/*/SKILL.md` + `domains/*/case-lessons/` + relevant references.
3. **If stack has no dedicated skill AND chain is reusable** → create Skill under `security/` (user/curator absorb request counts as adopt for that batch): fingerprint → ROI chain → pitfalls → checklist. Mirror a short `case-lessons/<slug>.md` + CASE-INDEX row + `tgsec-suite` 实战课表一行.
4. If stack already covered → patch references / case-lesson only (do not clone skill).
5. Skip pure credential dumps / duplicate packs / already-stopped cases.

2026-09-22 batch created: `darksword-coruna-c2-pentest`, `bms-pc28-console-pentest`, `chatnet-lsky-cloudreve-ugc` (+ auth lesson `ruoyi-plus-anonymous-gettoken`).

**大报告包批量流水线（2026-10-12 B 批沉淀）**: 解包 → sha 对账剔重 → 技能包按 Wave 批量入库（先名后义、零覆盖、随装随扫署名）→ 报告体委托 **3 路子代理并行 digest**（每条结论注来源文件；敏感物仅记类别+数量；**digest 落盘先做值泄漏扫描再使用**）→ case-lessons 批量落库 + INGEST-INDEX/UPDATE/CASE-INDEX/总册/自述三件 同一轮收口。

### Pack triage (Telegram Desktop / sinian / loot)

User: 「有重复的报告就掠过」. Before gap-mapping a zip:

1. SHA top-level members vs `/root/cases/_absorb/report_zip_*` and prior packs.
2. **Telegram Desktop / aimy / claude-red / sinian-paidaxing** — already fused 2026-09-20
   (`FUSION-20260920-absorb.json`, sinian 114 under `domains/*/src-methods/_vendor/sinian/`,
   README + `UPDATE-2026-09-20`). Re-drop → skill-name diff only; 0 new skills ⇒ skip.
3. Larger `*_REPORT_PACK.zip` that only adds dumps/CSV/session loot while `*_REPORT.md`
   sha matches → **credential pack, do not ingest** (hard gate §5).
4. Technique already covered (e.g. 162 DarkSword/Coruna) → no second Skill; lesson may
   already exist from the same campaign batch.

### Suite publish after absorb

- Private new Skills stay in `~/.hermes/skills/security/` (not forced into git).
- Publish: suite `domains/` lessons + CASE-INDEX + 总册 + umbrella patches + **自述全套**
  (见 `references/github-token-push.md` 自述清单). Tor selective push.
- Sync touched umbrellas Hermes → `hermes-skills/` + AI mirrors before commit.
- **PoC commit 不算完成。** 用户 2026-09-23：「自述 还有简介那些呢  还有十、聚合群」 → README **§十 融合批次** + START 「本轮更新」/「最近融了啥」 + MASTER 文首 + GitHub About `PATCH` description 必须同一轮。补 commit `12e76197` 才算自述跟上 `1d12151c`。
- **UPDATE-*.md 不进仓库根目录（2026-10-06）**：用户「这些就不用在仓库显示了啊」→ 日期更新文件归档 `docs/updates/UPDATE-YYYY-MM-DD.md`（今后直接生成在那里），README「更新说明文件」/START 指路语同步改指；移库引用同步配方、收口验证三件套（关键词 battery / 技能补丁持久化 / git 零漂移）、「假矛盾」裁定（一手证据先行，勘误进 `meta.md` 不改原文）见 `knowledge-repo-integration` → `references/batch-closeout-repo-presentation.md`。

