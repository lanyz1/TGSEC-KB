# security-kb-ingest 全文 第 2/2 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

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

