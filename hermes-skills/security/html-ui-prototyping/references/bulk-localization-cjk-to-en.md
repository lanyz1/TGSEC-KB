# Bulk CJK→English localization of a large single-file HTML prototype

Learned 2026-08 on Qavlixor seller center (~2700 lines, 1366 unique CJK strings /
2373 occurrences) — full-site Chinese→English conversion in one file. Reuse whenever
the user asks to flip a prototype's default language wholesale.

## Procedure

1. **Scan first**: `re.findall(r'[\u4e00-\u9fff...]+', html)` with counts, dump
   high-frequency strings first. You need the ORIGINAL full-string list — after the
   first replacement pass you'll be chasing fragments and need the source text to
   recover context.
2. **Batch replace with a mapping dict, LONGEST-FIRST**: `for k in sorted(M, key=len,
   reverse=True): html = html.replace(k, M[k])`. Compound strings MUST run before
   their parts (导入任务 before 导入; 订单入账 before 订单).
3. **Repeat 3–4 times**: each pass leaves fragments; re-scan residual CJK, map the
   fragments by their known source strings, run again until count → 0.
4. **Punctuation in a final pass**: 。→. 、→, 「」→" …→... —→- （）→().
5. **Zero-residue check**: `[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]` count == 0.
6. **Verify in browser**: navigate key routes (#/dashboard #/funds #/orders
   #/products #/aftersales #/messages #/account #/onboarding #/login) → check
   `browser_console` js_errors → scan the rendered snapshot for glue words →
   force `location.reload()` (file:// caches the old file aggressively; navigate
   alone often shows stale content).
7. **Clean glue**: regex over text nodes `[a-z]+[A-Z][a-z]+`, filter out JS function
   names / ids (viewBox, openModal, getElementById, pmSel...), fix the rest with
   targeted replaces (TodayOrder→Today's Orders, ViewAll→View All,
   hoursinShip→h to ship, 1Basic Info→1. Basic Info).

## Pitfalls (each one bit us)

- **NEVER map single CJK characters to '' or English words** (单 个 位 件 条 笔 键 天
  月 年 共 如 与 在 后 中 工 运 订...). They destroy compounds: 订单→订, 键盘→Key盘,
  单笔→orders, 工作→Ticketday, and corrupt CSS selectors + emails. Only map full
  compound strings; single-character leftovers must be resolved via the original
  string list, one context at a time.
- **Blanket punctuation → space replacements break emails/URLs**:  。→'. ' turned
  `<EMAIL-REDACTED>` into `ops@qavlixor. com`. Re-join known tokens after.
- **CSS selector corruption** (worst failure): blank space/punctuation normalizations
  turned `.card{` into `. card{` and `.st.green` into `.st. green` (space after the
  dot), and descendant selectors got merged (`.tbl .ops` → `.tbl.ops`). Symptom:
  layout collapses / element spacing vanishes even though the accessibility tree
  looks fine. Repair inside the `<style>` block ONLY:
  1. delete "dot+space": `\. ` → `.` and `\. ([a-zA-Z])` → `.\1`
  2. split merged descendant selectors: `.tbl.ops` → `.tbl .ops`,
     `.field.has-err.err-msg` → `.field.has-err .err-msg`
  3. PRESERVE same-element multi-class via whitelist: `.btn.primary`, `.st.green`,
     `.tg.on`, `.pm-item2.on`, `.msg.me`, `.sf-step.done`, `.tl-item.done`,
     `.nav-item.active`, `.modal-mask.show`, `.view.active`, `.pm-logo.*`, `.inp.err`,
     `.field.has-err` — these are NOT descendants.
  4. also check `body.auth-mode .nav` style combinations that merge to
     `body.auth-mode.nav`.
- **Glue words after replace**: English fragments join with no space. The
  lowercase-uppercase scan catches most; some need context (`AllAmountare all USDT`
  → "All amounts in USDT"; `This PeriodLast Period`).
- **JS `toast('中文')` strings are safe to replace** (they live inside JS string
  literals) — as long as mapping keys never collide with identifiers. But translate
  JS comments too, or the file still reads half-Chinese.
- **Watch punctuation-only stragglers**: 。 「 」 、 （ ） each appeared as residuals
  after the main passes — handle them in the dedicated punctuation pass, not in
  string mapping.

## Workflow pattern that worked

Scan (full list) → batch 1: punctuation + high-frequency UI words (longest-first)
→ scan residuals → batch 2: fragments + mid-frequency → scan → batch 3: remaining
fragments → punctuation pass → zero-check → browser render + glue scan → CSS repair
(if broken) → targeted glue fixes → final zero-check + reload + preview.
