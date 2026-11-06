<!-- archived from /root/.hermes/skills/security/ui-handoff-verification/SKILL.md on 2026-10-21 -->

---
name: ui-handoff-verification
description: >-
  测绘引擎·Use when handing a UI baseline to another AI coder.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/ui-handoff-verification`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/ui-handoff-verification/…')`，不要相对 `references/legacy/` 解析。

# ui-handoff-verification（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ui-handoff-verification/`

溯源（仅标记）：`hermes/creative`

---

# UI handoff to another AI coder — 1:1 fidelity enforcement

## When to use
- User asks to hand a prototype/baseline to Claude Code or another agent to replicate, extend, or deploy, and "效果和我做的不一样" comes up
- Verifying another agent's UI output against a baseline without vision tools
- User relays agent screenshots for you to check ("你帮我看看对不对")

## Core lesson
**Token parity ≠ visual parity.** An agent can confirm "all tokens match" and still produce a page that looks different. Three pixel-level sources cause it: (1) font stack, (2) icon spec, (3) framework/global reset. Description can't replace code — export the CSS verbatim and order "copy the HTML structure, don't rewrite it".

## Deliverable package (build this when handing off)
1. `00-README` with the exact kickoff sentence the user pastes to the agent; update it every round (version the package v1→vN so the agent reads fresh instructions).
2. **Implementation directive** (agent red lines): no UI invention; baseline file wins on conflict; agent scope = backend integration + engineering, UI look decided by baseline; change flow = UI edits always happen on the baseline file, agent only syncs + backend-adapts. Template: `templates/implementation-directive.md`.
3. **Golden spec**: `:root` tokens pasted verbatim, component spec table (padding/radius/font-size/color per component), per-page specs, business rules marked "勿回退", acceptance checklist.
4. **Pixel-level supplement** (the part that fixes "感觉不一样"): global reset `*{margin:0;padding:0;box-sizing:border-box}`, `html,body{height:100%}`, body font stack `-apple-system, BlinkMacSystemFont,"Segoe UI","PingFang SC",...` + `-webkit-font-smoothing:antialiased`, `svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}`, `button`/`input`/`a` defaults, "no icon libraries / no web fonts / copy inline styles too".
5. **Verbatim baseline CSS export**: extract `<style>` to `baseline.css`; agent must diff-align its stylesheet — values identical, extra rules deleted, missing rules added, rename its classes to match baseline, never edit baseline rules.
6. **Standalone page samples**: for disputed pages, extract the `<section>` + full CSS into a standalone runnable HTML = "standard answer".
7. **Verbatim comparison tables**: baseline text vs agent text per element; command "replace the right column with the left, not one letter changed".
8. **Copy-glue inspection checklist** (for baselines that went through batch translation): a "broken → fixed" comparison table per page + a 3-minute self-check snippet the agent pastes into its own DevTools console (`document.body.innerText.split('\n').filter(l => /[a-z]{2}[A-Z][a-z]{2,}/.test(l))`) — output must be 0 lines (legal words Email/PayPal/SKU excepted). Agents that copied from an older broken baseline carry the same glue; make them self-audit instead of you re-reading every page.

## Verification loop without vision tools (OCR + pixel analysis)
- OCR (`rapidocr_onnxruntime`) extracts the agent's screenshot copy → compare against baseline strings extracted from the source file.
- PIL region sampling: average color of left/right halves; dark-pixel % (a `#000` brand panel ≈ 30–45% dark pixels; its absence ≈ <6%).
- Build a per-line evidence table (baseline vs agent vs verdict) — decisive, no "感觉". Recipe: `references/ocr-pixel-verification.md`.

## Attribution: agent's fault vs spec's fault
- Agent invented copy/elements absent from baseline (e.g. button "Log in to seller center", link "Back to marketplace") → **agent's fault**: baseline strings are verbatim in the spec; proof = exact-string diff.
- Layout frame exists but fonts/icons/reset differ → **spec's fault (missing pixel params)** → ship pixel-level supplement + verbatim CSS export.
- Page-level structure differences, copy differences, data differences (email/amounts) all mean "not copied". Require full-page screenshots per page; never accept self-reports of "改好了".

## Demo data is content too (pin it verbatim)
- Agents keep a chart's shape/colors but feed their own data — observed: the dashboard trend chart's x-axis ran to the live date (8/1–8/2) instead of the baseline's fixed anchor (7/31), and the end label changed 410→60. Grid proportions matched (same algorithm), so it looked "almost right" — the data was the only tell.
- When a spec says "same chart/table", PIN the exact data arrays + date anchors (`sales30=[210,…,410]`, anchor `new Date(2026,6,31)`, prev = current×0.87, 7-day view = last 7 points, 30-day = all + prev×0.87) and explicitly forbid `new Date()` for axes and self-generated random data. For a disputed chart, ship the baseline chart JS verbatim (a `图表-基准代码.js`-style export) and order a straight copy.
- Acceptance for the chart: fixed axis labels (no today's date), end label equals the last array value, y-grid matches baseline values.

## Language direction: prefer a runtime toggle over a second copy
- User asked for a Chinese version, then rejected both the English-only and Chinese-only directions: "你直接做成中英文可切换的不就行了吗". For a bilingual-capable prototype, deliver a runtime language switch (dict + text-node substitution; switch-back = reload; see skill `single-file-html-batch-editing` → `templates/i18n-bilingual-engine.js`) instead of maintaining two copies. Never auto-translate the baseline itself without being asked.

## Pitfalls
- Agent says "confirmed identical" and still rewrites from description — use copy-not-rewrite language.
- **Uneven spec detail = agent invents on thin pages.** If a page's spec is 2 lines while its baseline HTML is 10k chars (observed: onboarding page), the agent improvises there. Rebuild thin specs by extracting the baseline section's verbatim visible text + `value=`/`placeholder=` attributes into a full field-by-field spec (incl. data tables like country→certificate mappings).
- **Baseline bugs are contagious.** Agents copy the baseline verbatim, so run the copy-glue scan on the baseline FIRST and fix it before shipping the package — otherwise the agent reproduces your glue and you judge it against your own bug. When verifying, fix the baseline too but still judge the agent against the corrected text.
- OCR low-confidence lines (<0.8) — confirm with pixel checks or re-crop.
- Partial screenshots mislead: a 620px crop of a 2-col layout looks like the brand panel is missing. Demand full-page screenshots; pair OCR with region color sampling.
- Agents fix only the layout frame and leave invented copy (observed twice in a row) — check BOTH structure AND every string, not just the part the user flagged.
- When extracting baseline strings, you may surface baseline copy bugs (glue from prior edits) — fix baseline too, but still judge the agent against it.

## Support files
- `templates/implementation-directive.md` — red-lines directive for the receiving agent.
- `references/ocr-pixel-verification.md` — OCR + PIL verification recipe with code.
