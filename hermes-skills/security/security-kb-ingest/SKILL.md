---
name: security-kb-ingest
description: "Use when absorbing security repos into skills."
version: 1.0.0
---

# Security Knowledge-Base Ingestion & Archiving

How to absorb external security/red-team repos (GitHub or local dirs) into the Hermes skill
library, audit for conflicts, and (optionally) archive them to a git repo.

## Standard workflow (repeatable)

### 0. 「先告诉我」决策门（用户硬规则）

吸收 / 归集 / 融合仓库评估：**禁止直接 clone 开融**。先输出可吸收清单（已融/跳过/可疑投毒/真缺口 + 建议动作），**等用户明确指令**再动手。用户原话量级：「先告诉我 让我做决定」。**仓库 push 同样算「动手」**：决策表/triage 索引等任何 git push 也必须先汇报、经同意再推（2026-10-06 擅自推决策表被用户纠正）。用户点头短语常为「一起推送到仓库啊」= 把当时**全部待推 commit 一次性推**（勘误/整理/归档别分开等），推后 `git ls-remote` == 本地 HEAD、工作树 0 残留（**一键验收 `scripts/push_verify_live.sh [repo]`**：本地 HEAD＋工作树＋live ls-remote 一屏对账，远端 `HEAD` 与 `refs/heads/master` 双 ref 均须齐平；守卫/豁免/验收细则见 `references/push-guard-acceptance.md`）。用户事后重问「推送到仓库了吗」＝**现场重跑 ls-remote 回报，不凭记忆复述**。

批量 GitHub/CVE/Sploitus 链接的差分 triage 见 `references/batch-cve-repo-triage.md`。

t.me 频道（cvebird）增量批处理管道见 `references/cvebird-batch-pipeline.md`（抓取 → 增量窗口 → 轻探 → 四桶决策表 → 等拍板）；抓取脚本 `scripts/fetch_tme_channel.py`。

1. **Clone/verify** — only AFTER user approval: `git clone --depth 1 <url>` to `/root/<repo>`, or accept local paths directly.
2. **Inventory** — one terminal pass: `du -sh`, top-level dirs, counts (`find . -name SKILL.md | wc -l`, `*.py` counts, total files). Read README + one representative content file to learn the format (SKILL.md frontmatter vs YAML cards vs markdown docs).
3. **Register a router skill** — create a Hermes skill entry (category `security`) that is a ROUTER ONLY: path pointers, content inventory table, lookup order, on-demand reading. Never copy the whole knowledge base into the skill body — context budget.
4. **Verify** — `skill_view` the new entry; spot-check that the repo paths exist and representative scripts parse/run.
5. **Register in the arsenal** — every absorbed card must be retrievable in real engagements:
   ```bash
   python3 /root/.hermes/arsenal/arsenal_build.py
   python3 /root/.hermes/arsenal/vuln_build.py
   python3 /root/.hermes/arsenal/selftest.py
   ```
   `arsenal_build.py` reindexes all enabled + archived cards; `selftest.py` must stay `route-hit 30/30`. New cards without an arsenal entry are "absorbed but unusable" — do not close the ingest without this.

6. **Path audit (mandatory)** — every literal path in an absorbed `SKILL.md` or reference is a promise. Resolve it against the real repo root; dead paths make the card unusable even when the technique is good. Audit procedure and the `/root/security-suite` → `/root/TGSEC-Qtzuu` case: `references/path-audit-after-ingest.md`.

## Pitfalls (learned the hard way)

- **updatePwd userId red herring**: RuoYi's `PUT /system/user/profile/updatePwd` accepts
  a `userId` param but IGNORES it — always validates/changes the CURRENT token user's password.
  Initial testing made it look like horizontal privesc (200 response), but the 200 meant
  YOUR password was changed. Always re-login to verify which account was affected.
  The endpoint IS useful for user-existence enumeration (no rate limiting, 5000+ IDs tested).
- **Captcha single-use**: RuoYi kaptcha UUIDs are one-shot — one wrong answer invalidates
  the UUID entirely (not just "expired"). Must OCR correctly on first try. Vision API has
  ~70% operator accuracy (`*` vs `/` confusion); answer range 0-81.
- **WAF cookie alongside JWT**: When TencentEdgeOne is in play, ALL requests need BOTH
  the WAF bypass cookie AND the JWT Bearer token, or API returns HTML instead of JSON.
  WAF cookie values rotate periodically — re-solve the JS challenge when responses go HTML.
- **Description length limit**: skill_manage refuses descriptions longer than 60 chars
  ("Description is N chars — new skills must fit the 60-char system-prompt budget").
  Keep it: trigger first, ≤60 chars, ends with period. Count characters mentally —
  shortening by 1-2 chars often still fails; trim the trigger wording.
- **Batch atomicity**: skill_manage operations apply atomically — one failing op rolls back
  ALL touched skills. Validate every op's constraints (esp. description length) before the batch.
- **Do NOT symlink knowledge bases into a git archive**: git stores symlinks as links, not
  content. Use `cp -rL <src> <dest>` (dereference) when building a publishable copy.
- **WeChat articles**: `web_extract` returns only title; use `curl -A <browser UA>` and strip
  tags with regex to get full body; browser tool needs Chrome running.
- **Do not delete user directories while archiving** — only ever read them; content changes are
  usually the user's own doing (verified via stat mtime, not assumed).

- **署名/来源清理（硬口径，2026-10-12 起）**：吸收任何外部材料入库前，剥离全部上游署名痕迹（横幅 / ASCII art / figlet / 联系方式块 / 图章图 / 文件名后缀 / 目录名 / 代码内 dunder 作者字段）。流水线：token 全库扫描 → surgical（变量置空、横幅函数整删、box 替换）→ line-drop（含 token 行）→ inline 正则（链接→文本、裸 URL/句柄删除）→ 图片删除或 **SVG 源重渲染** → 文件名/目录改名 → `grep -rilE` 复扫归零 → `py_compile` 全量复核。**整行删除三坑**：docstring 开行 / f-string 闭行（`"""` 同行）/ 常量行被删会打断字符串——这些必须先用"内容置空"的针对性替换。**ASCII art 不含 token 字符串**（d8888 艺术、mm-art、figlet 均抓不到），须按字符集识别：d8888 系 `^[\s#/*"\\dDYy8bBpPkKtT0-9.\-]*$` 且含 marker（d8888/888888b/T88b）；mm-art 系 `**` 后仅 `[m#"'空格]` 且含 `mm|##|""`。批量文本清洗后务必抽查 2-3 个文件的头部视觉效果（避免"删干净但结构破相"）。

## Conflict auditing (run after multi-repo ingest)

Run `scripts/audit-skill-conflicts.py` — parses ONLY the first YAML frontmatter block of each
SKILL.md (a whole-file grep produces false positives from example snippets inside the body:
names like `Heritage`, `my-skill-name`, `security-reviewer`), detects cross-repo duplicate
skill names, and reports repo-by-repo counts. Overlapping names across repos are NOT
collisions as long as each is accessed by full absolute path — document which repo wins in
the router entry; 8 known cross-repo duplicate names exist among the absorbed repos.


## 全文导航（已拆分）

主卡保留前 3 节；其余 13 节在 `references/full.md`：

- Archived repos (as of 2026-09)
- Integration vs stacking (critical user correction)
- SRC Knowledge Fusion (clown-src-6k-skill pattern)
- Multi-AI Tool Config Distribution
- Branding & upstream stripping
- GitHub archive push
- Renaming repos on GitHub
- Multi-AI Tool Configuration Distribution
- SRC Knowledge-Base Fusion Pattern
- Bulk skill install from local directories (xishou pattern, 2026-09-28)
- HIT check / 对账 pitfalls (batch triage)
- Playbook references
- Report absorb: 未覆盖栈 → 新 Skill（第四步硬门）

加载：`skill_view(name='security-kb-ingest', file_path='references/full.md')`

> 全文较大（21823 字符），已分 2 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
