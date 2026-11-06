# Full-site language conversion in single-file HTML prototypes

Scenario: user asks to flip the whole prototype from Chinese to English (or any bulk text change). The file is ONE html with inline `<style>` + `<script>` — a text-replacement pass that ignores the code regions WILL corrupt JS and CSS. Verified 2026-08 on the Qavlixor seller center (1,366 unique CJK strings, 2,373 occurrences → 0 residual, all JS/CSS repaired).

## Batch replacement workflow
1. **Scan scope**: `re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+', html)` → Counter → dedupe count + per-string frequency. Plan 3-4 batches: high-freq / common UI words first, then medium, then re-scan the CURRENT file state for low-frequency fragments (they mutate after every batch because longer strings get consumed first).
2. **Mapping table**: dict of exact Chinese string → English. **Sort keys by length DESC before replacing** — otherwise a short key (`'订单'→'Order'`) fires inside a longer string before `'订单号'→'Order No.'` is applied, leaving broken fragments.
3. After each batch, re-scan and map the new single-char leftovers (已/内/后/的/个/下/中…) — they are fragments of previously-consumed phrases.
4. **Clean CJK punctuation separately** (after all text batches): `。`→`.`, `、`→`, ``, `「」`→`"`, `—`→`-`, `…`→`...`, `（）`→`()`. Verify with the full CJK-class regex that residual is 0.
5. **Avoid single-char mappings** like `'单'→''` or `'与'→'and'` — they destroy compound words (订单→订, 键盘→Key盘). Prefer whole-phrase mappings; if a single char MUST map, re-scan and fix the fragments it creates.
6. English glue cleanup after replacement: fix `,([A-Za-z])` → `, \1`, `\.([A-Za-z])` → `. \1`, and known glued pairs (`Today's Orders` rendered as `TodayOrder`, `Total 231 products` as `Total 231 pcsProduct`, `Jul 31, 2026` as `2026year7month31day`).

## THE PITFALL: bulk text replace corrupts JS member access and CSS selectors
User symptoms (exact): "曲线图没了, 页面按钮也不能点击了" (chart gone, buttons dead, hash routing stuck — `#/funds` still shows dashboard).

Root cause: the same pass that replaced Chinese text also rewrote the code regions:
- **JS**: every `.` became `. ` (dot-space): `document. getElementById`, `sales30. slice`, `e. target`; string selectors became `'. view'`, `'. modal-mask'`. First `querySelectorAll('. view')` at init throws `SyntaxError: '. view' is not a valid selector` → **script aborts** → event binding, chart drawing, hashchange listener never run. Later `const sales30` never executes, so touching it reports `Cannot access 'sales30' before initialization` (TDZ) — a red herring that points at the wrong line.
- **CSS**: `.card` → `. card` (dot-space), `.st. green`; descendant selectors can collapse (`.tbl .ops` → `.tbl.ops`) when the repair regex is too aggressive.

Critical trap: **`node --check` PASSES on dot-space JS** (it is syntactically legal!). Syntax check alone will NOT catch this. The tell is runtime: script throws at the first `querySelectorAll` with a dotted class.

## Diagnosis (in order)
1. `browser_console` expression wrapping `show('funds')` and `drawChart()` in try/catch → surfaces the real error (invalid selector / TDZ).
2. Grep the script block: `re.findall(r'[a-zA-Z0-9_$]\. [a-zA-Z_$]', js)` — hundreds of hits = corruption.
3. Grep the style block for `\. ` residuals.

## Fix recipes
1. **JS block only**: `js.replace('. ', '.')`. BEFORE running, check JS string literals for legit English `e.g.` / `No.` phrases and restore the space afterwards (`'e.g.Tea'` → `'e.g. Tea'`). NEVER run this on the HTML body — English sentences need their dot+space.
2. **CSS rebuild** (after `\. ` → `.`):
   - Same-element multi-class stays merged — whitelist: `.btn.primary`, `.btn.danger`, `.st.green`, `.tg.on`, `.pm-item2.on`, `.tl-item.done`, `.nav-item.active`, `.pay-opt.on`, `.step.done`, `.modal-mask.show`, `.view.active`, `.field.has-err`, etc.
   - Descendant selectors that got merged (`.tbl .ops`, `.review-card .rh`, `.auth-brand .logo`, `.msg.me .mt`) get split at every dot after the first → `.tbl .ops`.
   - Watch `body.auth-mode.nav`-style cases: the element tag stays attached to the first class (`body.auth-mode`), later classes are descendants (`body.auth-mode .nav`).
3. Verify: extract `<script>` to temp `.js`, `node --check`; then browser: `show('funds')` flips views, chart container has `path`/`line` children, a button click opens its modal, console 0 errors.

## Cache-busting for file:// previews
`browser_navigate` to `file://` URLs frequently serves a STALE copy after edits — a false "still broken" report is usually cache, not your fix failing. Before asserting on new content: `location.reload()` or `location.href='file:///...html?_='+Date.now()+'#/route'`. The `?_=<ts>` cache-buster is the reliable one.
