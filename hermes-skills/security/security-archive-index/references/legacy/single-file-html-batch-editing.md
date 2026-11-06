<!-- archived from /root/.hermes/skills/security/single-file-html-batch-editing/SKILL.md on 2026-10-21 -->

---
name: single-file-html-batch-editing
description: >-
  测绘引擎·Use when batch-editing a single-file HTML prototype.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/single-file-html-batch-editing`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/single-file-html-batch-editing/…')`，不要相对 `references/legacy/` 解析。

# single-file-html-batch-editing（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/single-file-html-batch-editing/`

溯源（仅标记）：`hermes/creative`

---

# Single-file HTML batch editing (safe bulk replace)

## When to use
- Converting all UI copy in a single-file HTML prototype to another language (e.g. Chinese→English) via scripted find/replace
- Any scripted bulk edit over a file that mixes HTML + `<style>` + `<script>`
- Debugging a single-file prototype whose buttons stopped clicking / charts vanished / hash routing is dead after such edits

## The 4 corruption modes (all seen in production)
| Mode | Damage | Symptom |
|---|---|---|
| `a.b` → `a. b` (dot+space) in JS code | `document. getElementById`, `sales30. slice` | still parses (legal JS) but see string mode |
| selector strings `.view` → `. view` | `querySelectorAll('. view')` throws `SyntaxError: '. view' is not a valid selector` | **script aborts at init** → event binds, drawChart, hashchange listener never run → buttons dead, chart missing, every route shows the first section |
| CSS `.card` → `. card` / `.st.green` → `.st. green`; descendant `.tbl .ops` merged to `.tbl.ops` | styles silently dropped or wrong | layout density/color wrong; operations column loses its gap |
| English copy with apostrophe inside single-quoted JS string | `toast('Today's Sales')` | JS syntax error |

Chain: ONE bad selector string aborts the whole `<script>`, which is why "everything broke at once" (buttons + chart + routing).

## Safe replacement rules
1. **Longest string first** when mapping (don't let 订单 fire inside 订单入账).
2. Scope punctuation maps to text; never blanket-replace `.`, `:`, `'` globally.
3. Avoid single-char CJK→'' maps — they destroy compounds (订单→订, 键盘→Key盘). Map full phrases.
4. Whole-file regex fixes must be **scoped to `<style>`/`<script>` blocks** — HTML text contains legitimate `. ` (sentences, "e. g.") that must survive.

## CSS selector rebuild procedure (after corruption)
- Broken patterns: ` . x` (space before dot) and `. x` (space after dot). Inside `<style>`: `. ` → `.` (remove space after dot); descendant separators keep their space (`.tbl .ops`).
- Distinguish **same-element multi-class** (`.btn.primary`, `.tg.on`, `.st.green`, `.pm-item2.on`, `.tl-item.done`, `.nav-item.active`, `.pm-logo.*`, `.sf-step.done`) from **descendant** (`.tbl .ops`, `.card-h .more`, `.pm-item.on .ok`). Keep same-element merged; split descendants by inserting a space before the 2nd+ dot. Maintain a whitelist of same-element combos; every other multi-class string gets split.
- Tag selectors (`div`,`span`) and pseudo-classes (`:hover`) are not merged — leave them.

## SAFE alternative: runtime bilingual switch (don't rewrite the source)
When the goal is a language toggle (user: "你直接做成中英文可切换的不就行了吗" — they rejected both an English-only and a Chinese-only copy), do NOT create a translated copy and do NOT batch-rewrite the source. Inject a runtime i18n engine instead:
- Keep the source HTML in ONE language (English). The gold-standard file stays byte-identical; the bilingual version is a copy + injected engine.
- Inject an `I18N` dict (EN→ZH) + a TreeWalker over text nodes; replace via **word-boundary regex** `(^|[^A-Za-z])KEY([^A-Za-z]|$)`, keys sorted longest-first. Plain substring replace hits `Type` inside `Type-C` and `Ship` inside `Shipping`; put full compounds (`Type-C Fast-charge Cable 100W`, `Shipping Templates`) in the dict and let longest-first order protect them.
- Switch back to EN = `location.reload()` — source untouched, no reverse mapping, zero residue. Persist choice in localStorage; top-bar button calls `toggleLang()`; on load, if stored=zh, apply after DOMContentLoaded (small setTimeout so the SPA's own init has run).
- Cover `input[placeholder]` too; `select option` text is a text node (walker covers it); `input[value]` demo data (product names) needs explicit handling if you want it translated.
- Full engine (copy-paste ready): `templates/i18n-bilingual-engine.js`.

## Verification (mandatory before delivery)
1. `node --check` on the extracted `<script>` body (write to temp file first).
2. Browser with cache-bust: `file:///...?_=<Date.now()>#/route` — plain reload can serve a stale file.
3. Drive the app: `show('funds')` must flip `.view.active`; `drawChart()` must produce `line`/`path` inside the chart svg (query `#chart line, #chart path` — NOT `#chart svg path`); click a real button and confirm `#modal-xxx` gains `.show`.
4. Hook `window.onerror` collecting msg/line/col/stack, reload, assert empty.
5. For a completed localization: `[\u4e00-\u9fff]` + CJK-punctuation regex over the whole file must return 0 hits.

## Injecting NEW JS into a single-file HTML (safe pattern)
After corruption fixes you often must ADD functionality (e.g. a dashboard date-switcher that swaps KPI data per day). Two mistakes kill the page:
- Inserting a **bare JS blob (no `<script>` wrapper)** after the first `</script>` → browser renders it as HTML text, never executes (symptom: new globals undefined, UI visible but dead).
- Wrapping it but slicing the block with a naive `find('});')` → truncated function = syntax error → the whole new block never runs.
Safe recipe:
1. Append a COMPLETE `<script>...</script>` block just **before `</body>`** — never inside the main script nor right after its `</script>` (you may be splitting the main script's tail).
2. Guard event binding: `if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded', fn)}else{fn()}`.
3. Data-switcher pattern: a `DATA` object keyed by button `data-day` + a `setDay(key)` fn writing text via `el.childNodes[0].nodeValue` (safe when the value node is followed by `<small>` — `textContent` would nuke the `<small>`), swapping `.d` class/text for ▲/▼ arrows, toggling `.on` on seg buttons.
4. Verify the new globals exist in browser console: `window.DASH_DATA` / `typeof setDay==='function'` — undefined means the block isn't executing (wrapper or placement bug), not a data bug.
5. Edit-order trap: if you add `id=` to an element AND replace its text in the same pass, do the text replacement with pre-id markup FIRST, then add ids — otherwise `old_string` matching `<div class="v num">` fails against `<div class="v num" id="kSales">`.

## Pitfalls
- CSS-fix regexes applied to the WHOLE file corrupt JS too — scope them.
- After fixes the browser may still show old behavior: it's cache — force `?_=timestamp`.
- TDZ errors ("Cannot access 'x' before initialization") mean the script aborted BEFORE that const line; the real error is earlier (usually the selector SyntaxError). Find the first abort, not the symptom.
- `node --check` passes on `. ` corruption (it's legal JS) — the browser runtime test is the real gate.
- Apostrophes: in single-quoted JS strings escape `\'`; in HTML double-quoted attributes a plain `'` is fine.

## References
- `references/qavlixor-localization-transcript.md` — the real corruption→fix sequence (exact strings + numbers) from the Qavlixor Chinese→English pass.
