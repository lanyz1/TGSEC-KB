<!-- archived from /root/.hermes/skills/security/html-ui-prototyping/SKILL.md on 2026-10-21 -->

---
name: html-ui-prototyping
description: >-
  测绘引擎·Use when building/iterating HTML admin-dashboard prototypes.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/html-ui-prototyping`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/html-ui-prototyping/…')`，不要相对 `references/legacy/` 解析。

# html-ui-prototyping（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/html-ui-prototyping/`

溯源（仅标记）：`hermes/creative`

---

# Interactive HTML UI Prototyping (dashboards / admin consoles)

## When to use
- User asks to design/redesign a web app UI (admin panel, seller center, dashboard) as a clickable prototype
- User first asks to strip a design spec to functionality-only (fields/states/actions, no colors/radii), then rebuild visuals
- User asks for style directions ("帮我做一套X风格的我看看", "出样图") before committing

## User taste profile (learned 2026-07-31, Qavlixor seller center)
Rejected directions (do NOT resurface without being asked):
- Dark-sidebar + light-content financial SaaS (老套)
- Neon/gradient/glow/grid-line "tech style" — user explicitly: "AI 味道太重"
- TikTok pink style (不满意)

**Winner: Apple HIG minimal** — user confirmed "颜色我现在基本满意了" on the A2 variant.
- Pure white bg `#FFFFFF`, card border `#E8E8ED`, ink `#1D1D1F`, muted `#6E6E73`, faint `#98989F`
- Primary buttons **black** `#000000` (white text, hover `#2E2E30`), pill radius 999px
- Sidebar light gray `#F9F9F9`; selected nav item = light gray bg `rgba(0,0,0,.07)` + bold dark text, NO left color bar
- Apple blue `#0071E3` only as rare accent (login-page slogan, links on dark surfaces)
- Status badges = Apple system colors on ~10-12% alpha tints, pill shape:
  green `#34C759`/text `#248A3D`, blue `#007AFF`/`#0A60C0`, orange `#FF9500`/`#B25A00`, red `#FF3B30`/`#D70015`, gray `#6E6E73`
- Large page titles 24px `letter-spacing:-.4px`; card radius 16px, control radius 10px, thumb radius 10px; shadow ~`rgba(29,29,31,.03)` (nearly none)
- Chinese date format `2026年7月31日 · 周五` — NOTE: as of 2026-08 (p12) the whole prototype was converted to English; dates now render `Jul 31, 2026 · Friday` and ALL new copy must be written in English. Revert format per page only if the user asks.
- Charts: black 2px line, black area gradient ≤0.14 alpha, gray dashed `#C9C9CE` previous-period comparison line + legend, y-axis labels OUTSIDE plot area (PAD.l ≈ 44), sparse x labels, bold end-point value label, pill tooltip

## Workflow (proven sequence)
1. If a design spec exists, first strip it to functionality-only (user decides visuals later)
2. Ask ONE direction question (clarify, 4 options) OR go straight to a variant board when user is undecided
3. Build a **variant board**: one HTML page rendering each candidate as a FULL scaled page mockup — component chips never convince this user, whole-page renders do
4. User picks (e.g. "A2") → apply globally by swapping `:root` CSS variable tokens
5. Iterate page-by-page on details, user drives the order; push each change with a preview refresh
6. Verify: `browser_navigate` + `browser_console` (js_errors, and exercise every route via `show(route)` in console JS)

## Techniques
### Single-file SPA prototype (all pages in one file)
- Each page = `<section class="view" id="view-{name}">`, only `.active` is shown
- Hash routing: `show(route)` toggles views + nav-item active, `history.replaceState(null,'','#/'+route)` + `hashchange` listener → refresh keeps route
- Auth pages (login/register/onboarding) live in the same section list; `body.auth-mode .nav, body.auth-mode .topbar{display:none}` + `body.auth-mode .content{padding:0}` switches to fullscreen mode
- Shared primitives: `.btn(.primary/.sm/.danger)`, `.st` status pills, `.card/.card-h`, `.tbl`, `.inp`, `.field`, `.modal-mask`, `#toast`; interactions via inline `onclick` + small global JS (`toast()`, `openModal()`, `sendCode()` 60s countdown, `qty()` stepper)
- Chart: generate SVG in JS from a data array (midpoint-bezier `smoothPath`), sparse grid (3 lines), axis labels outside plot
- Inject large sections progressively with `patch()` at a `<!-- INJECT -->` anchor — avoids one gigantic write

### Full-page variant comparison page
- Page template written once in JS; each variant rendered by inlining CSS vars: `<div class="frame" style="--brand:#...;--bg:#...;">`
- Scale trick: `.frame{width:1240px;transform:scale(.52);transform-origin:top left;pointer-events:none}` inside a clipping wrapper → real 1:1 layout at thumbnail size, 3-4 variants side by side
- Click-to-select (border highlight + ✓ tag); user replies with the variant key

### CSS-variable theming
- All colors/radii live in `:root`; swapping a theme = editing tokens only
- Keep semantic vars (`--brand`, `--brand-ink`, `--g/--gs`, `--blue/--blue-soft`, `--orange/--os`, `--red/--rs`, `--gray-soft/--gray-ink`) so component CSS never hard-codes hues
- SVG chart hex stays hard-coded — centralize it in the draw function so a restyle is one edit

### Bulk CJK→English localization (full-site language flip)
User may ask to convert the whole prototype to English as a final step (p12). See
`references/bulk-localization-cjk-to-en.md` for the full procedure. Core rules:
1. Replace longest-first via a mapping dict; NEVER map single CJK characters
   (单/个/位/件/键/天...) — they destroy compounds (订单→订, 键盘→Key盘) and corrupt CSS.
2. Run 3–4 passes: map → re-scan residual fragments → map again until
   `[\u4e00-\u9fff...]` count = 0, then a punctuation pass (。、「」…—).
3. After replacing, CHECK CSS selectors — blank normalizations turn `.card{` into
   `. card{` and merge descendants (`.tbl .ops` → `.tbl.ops`). Repair dot-space in
   `<style>` and split merged descendants, preserving same-element multi-class
   (`.btn.primary`, `.st.green`, `.pm-item2.on`) via whitelist.
4. Scan for glue words (`TodayOrder`, `ViewAll`, `hoursinShip`) in rendered pages
   and fix; emails break via  。→'. ' (`ops@qavlixor. com`) — re-join.
5. file:// caches hard — force `location.reload()` between verification passes.

## Pitfalls
- Component-only previews do NOT work for this user — always render complete pages (sidebar+topbar+KPI+chart+table)
- Slop list this user explicitly rejects ("AI 味"): gradient backgrounds, glow/shadow-heavy, grid-line overlays, colored dots on KPI labels, feature-tile grids, accent rails, emoji decorations
- After a theme switch, grep for stale hex from the old palette (e.g. `#26A17B`, `#1E8D6C` hover, `#0E1526` navy) — missed ones read as leftover branding
- `patch()` old_string must be unique: replacing `.thumb{...}` once clobbered the shared class (matched only `.prod .thumb` context) — after batch patches, verify computed styles in console
- "布局只占了一半" complaint = a `max-width` on `.content`; remove it
- KPI numbers must be internally consistent (客单价 = 销售额 ÷ 订单: 1245.80/86 ≈ 14.49)

## Support files
- `references/apple-minimal-tokens.md` — exact A2 token block + component values for instant re-application
- `references/bulk-localization-cjk-to-en.md` — full procedure + pitfalls for converting a large single-file prototype from Chinese to English (batch mapping, CSS-selector repair, glue-word scan, verification loop)
