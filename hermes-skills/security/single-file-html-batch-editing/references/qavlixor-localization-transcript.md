# Qavlixor 中文→英文批替换事故实录(2026-08)

Context: single-file seller console prototype (~2,700 lines, hash SPA, embedded CSS+JS). Batch replaced 1,366 unique CJK strings (2,373 hits) in 3 scripted passes via a large mapping dict + fragment cleanup.

## What broke
After the passes, symptoms: buttons unclickable, sales chart empty, every hash route showed the Dashboard section.

Root-cause chain:
- Every `.` in JS had become `. ` (dot+space): `document. getElementById`, `querySelectorAll('. view')`.
- `querySelectorAll('. view')` → `SyntaxError: '. view' is not a valid selector` at init.
- Script aborted before `const sales30=[...]` → later `drawChart()` threw TDZ "Cannot access 'sales30' before initialization" (a symptom, not the cause); the hashchange listener never got bound.

CSS was also corrupted: `.card` → `. card`, `.st.green` → `.st. green`, descendant `.tbl .ops` merged to `.tbl.ops`, `.pm-item.on .ok` → `.pm-item.on.ok`, `.review-card .rh .edit` → `.review-card.rh.edit`.

## Fixes applied (in order)
1. Inside `<script>` ONLY: `. ` → `.` (955 hits). Never whole-file — HTML text has legit "e. g.", "Please wait." etc.
2. Rebuilt CSS selectors inside `<style>`: `. ` → `.`; then split merged descendants using a same-element multi-class whitelist (`.btn.primary`, `.btn.danger`, `.tg.on`, `.tg.disabled`, `.st.green/blue/gray/orange/red/amber`, `.step.on/.done`, `.sf-step.cur/.done`, `.sf-line.done`, `.nav-item.active`, `.pay-opt.on/.disabled`, `.net-opt.on`, `.ch-opt.on/.span2`, `.pm-item.on`, `.pm-item2.on`, `.pm-logo.paypal/wise/card/ap/gp`, `.pm-body.open`, `.pm-panel.open`, `.pm-row.on`, `.inp.err`, `.cl-item.on`, `.pager.pg.on`, `.st-row.total`, `.tl-item.cur/.done`, `.kpi .d.up/.down`, `.tabs button.on`, `.seg button.on`, `.stk-warn.low/.low0`, `.tt-ok.bad/.warn`). Every OTHER multi-class string (`.auth-mode .content`, `.field.has-err .err-msg`, `.msg.me .mt`, `.sf-step.done .n`, `.tl-item.done .dot`) gets split at the 2nd+ dot.
3. Apostrophe trap: no `'s` landed in JS strings this time, but the risk is real (English copy with apostrophes inside single-quoted JS strings breaks syntax) — escape `\'`.
4. Verification: `node --check` on the extracted script passed (`. ` is legal JS, so node alone would NOT have caught the selector bug — the browser runtime test was the real gate). Browser: `show('funds')` flipped view, `drawChart()` produced 5 line + 3 path inside `#chart`, a real button click opened `#modal-statement`, `window.onerror` hook empty after reload.
5. file:// cache: `location.href='file:///...?_='+Date.now()+'#/funds'` to bust stale copies.

## Numbers
- Residual CJK after 3 passes: 0 (then punctuation: — … 「 」 、 （ ） all cleaned).
- 20+ text glue artifacts cleaned in follow-up passes ("charactersCountcharacters", "Today's CustomersUnit Price", "ordersMin", "PaySuccess") — glue = two mapped fragments landing adjacent with no space; fix by context lookup then targeted replace.

## Related: CSS selector corruption from ANOTHER agent's edits
The same `. ` corruption can appear in CSS written by AI coders. Symptom fingerprint: `classList`-heavy UI looks fine in markup but styles are missing; `document.querySelectorAll` throws "'. x' is not a valid selector" at runtime.
