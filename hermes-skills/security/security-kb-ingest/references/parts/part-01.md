# security-kb-ingest 全文 第 1/2 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

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

