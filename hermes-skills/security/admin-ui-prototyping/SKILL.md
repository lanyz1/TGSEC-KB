---
name: admin-ui-prototyping
description: >-
  测绘引擎·Prototype admin/seller-console UIs (后台/卖家端) in HTML.
owned: true
tier: general
pack: survey-skill
---

# admin-ui-prototyping（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/admin-ui-prototyping/`

溯源（仅标记）：`hermes/creative`

---

# Admin UI Prototyping (Single-File HTML SPA)

Build admin/seller consoles (Shopify/TikTok Shop-style seller centers, dashboards) as clickable single-file HTML prototypes. Proven on the Qavlixor 卖家端 project (15 pages, hash-routed SPA).

## Workflow

1. **Functional spec first**: when user hands over a design doc they dislike, strip it to functions/modules/fields/states only (drop colors/radii/layout descriptions) → user approves → then build.
2. **Build ALL pages in one SPA first**, then iterate page-by-page ("挨个页面去调整"). Do not over-polish one page before the others exist.
3. **Theme direction**: offer 3-4 COMPLETE schemes as full-page scaled mockups on ONE comparison page (user explicitly asked: "四组都出一下样图,做一张就行"). User picks a letter; apply globally by swapping CSS variables.
4. Verify (console errors + route walk), then `open_preview` the file — user reviews in the preview pane, not from descriptions.

## Single-file SPA architecture

- One `<section class="view" id="view-<route>">` per page; CSS `.view{display:none} .view.active{display:block}`.
- Hash router: `show(route)` toggles views + nav `.active`; `body.auth-mode` hides sidebar/topbar for login/onboarding/status pages (auth pages live inside the same `.content`).
- Shared shell: sidebar (menu groups + red badge pills, 99+ cap, store identity card at bottom) + topbar (language select + switch-account).
- Design tokens = CSS variables on `:root`; every component style references `var(--...)` so a theme is a one-line variable swap.
- Reusable component classes: `.btn(.primary/.danger/.sm/.ghost)`, `.card/.card-h/.card-b`, `.tbl` (tables), `.st` status badges (green/blue/orange/red/gray/amber), `.tabs` (with counts), `.seg` (pill toggle), `.steps` (wizard), `.field/.inp/.radio/.check/.upload/.code-btn`, `.modal-mask/.modal` + `#toast`, `.pager`, `.kv`, `.timeline`, `.chat-grid` (3-pane messaging), `.review-card` (read-only form review).

## Theme comparison page technique

- Render the SAME full-page template N times via JS (data array: `{k, name, tag, vars, sw}`).
- Each frame: fixed logical width (1100-1240px) + `transform: scale(.36-.52); transform-origin: top left` inside an `overflow:hidden` wrapper — real complete-page look, not component swatches.
- Per-theme variables injected INLINE on the frame container (`style="--nav-bg:#…;--brand:…"`); all styles reference vars, so one template × N variable sets = N full mockups.
- Mockups must include real composition: full sidebar menu, topbar, KPI row, SVG line/area chart (generate path in JS, `stroke:var(--brand)`), todo list, data table with status badges.
- Click-to-select with `--pick` border highlight + "✓ 已选" tag; user replies with the letter.
- Add a small `.shot-h` footer per frame showing name, one-line rationale, and swatch hex values.

## This user's design taste (critical — corrections from real sessions)

- **禁止 "AI味"**: no gradients on buttons, no glow/text-shadow, no neon, no grid-line backgrounds, no glassmorphism. User rejected a whole cyber/neon direction for exactly this ("ai味道太重"). Tech-flavored decoration reads as AI-generated to them.
- **Mainstream proven patterns win**: TikTok Shop style = black sidebar (#161823) + white content + BLACK primary buttons + ONE saturated accent (pink #FE2C55 or blue #0A84FF), larger young radii (~12px). Shopify style = slate-900 sidebar + indigo accent.
- Plain "dark sidebar + light content + single muted brand color" (the default SaaS look) reads as 老套/dated to this user — they asked to move away from it.
- **Full-width content**: do NOT cap `.content` with max-width; user complained "布局只占了一半多一点" and wanted the canvas filled.
- Direction choices must be full-page mockups, never just color chips/swatches.
- Numbers: tabular-nums / mono for order IDs, amounts, timestamps.

## Pitfalls

- `.content{max-width:…}` is a design decision, not a default — user explicitly wants full-bleed.
- Over-clever one-line JS (e.g. tab highlight via text-content matching) breaks silently → use `data-tab` attributes and exact matching.
- Fixed-viewBox SVG charts scale fine with `width:100%;height:auto`; don't stretch with `preserveAspectRatio="none"`.
- Keep prior versions as separate files (v1/v2, 样图-vs-正式) so user can A/B and you never destroy the working prototype mid-iteration.
- Verify every route before handing over: console script `Object.keys(ROUTES).forEach(r=>show(r))` catching errors, plus `browser_console` for JS errors.
- On Windows, preview `file:///C:/...` URLs need percent-encoding for Chinese filenames in browser_navigate.

## References

- `references/qavlixor.md` — Qavlixor seller-center project state: files, routes, rejected design directions, pending decisions.
