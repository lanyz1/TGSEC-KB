---
name: html-admin-prototype
description: >-
  测绘引擎·Build clickable admin prototypes as one HTML file.
owned: true
tier: general
pack: survey-skill
---

# html-admin-prototype（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/html-admin-prototype/`

溯源（仅标记）：`hermes/creative`

---

# HTML Admin Prototype Builder

Use when the user wants a *clickable, multi-page* admin/backend/dashboard prototype (seller centers, SaaS consoles, marketplace backends) delivered as a single self-contained HTML file they can open in a browser and click through. Complements `claude-design` (design process/taste — load both; this skill is the execution playbook for big admin prototypes).

Known application: **Qavlixor 卖家端** (cross-border seller admin, USDT currency) — see `references/qavlixor-seller-center.md` for its locked design system, page inventory, and domain rules.

## Architecture: single-file hash-routed SPA

- Every page is a `<section class="view" id="view-<route>">` inside one `<main class="content">`.
- Router: `ROUTES` map with an auth flag (`{login:1, register:1, ... dashboard:0}`), `show(route)` toggles `.active` on views + nav items, sets `location.hash = '#/'+route` via `history.replaceState`, and listens to `hashchange`.
- **Auth pages share the shell** (login/register/onboarding/status have no sidebar): add `body.auth-mode` class — CSS `body.auth-mode .nav, body.auth-mode .topbar{display:none}` — instead of duplicating layout. Onboarding/status pages get their own mini-header bar.
- Nav items carry `data-route` (+ optional `data-tab` for deep links like 资金中心→冻结明细). Click handler calls `show(route)` then the tab function.
- In-page tabs must NOT use `#` anchors (conflicts with the router). Use `data-tab` + a `setFundTab(tab)`-style function; keep it simple: `b.dataset.tab===tab`.

## Building large files incrementally (critical)

A 15-view prototype is ~90KB+ of HTML. One giant `write_file` risks truncation. Instead:

1. `write_file` skeleton: full CSS design system + nav/topbar + first page (dashboard) + `<!-- INJECT -->` placeholder + all modals/toasts + complete JS (route table must list every route even before its HTML exists).
2. `patch` the `<!-- INJECT -->` marker, replacing it with the next batch of pages **plus the marker again** — repeat until done. ~2-4 pages per patch keeps each write manageable.
3. Add JS interaction functions in one final patch.
4. Verify the route table matches injected view IDs exactly (see Verification).

## Design tokens (Qavlixor system — user-locked)

- Dark sidebar `#0E1526` (ink `#8B97AD`, active `#FFFFFF` w/ `rgba(255,255,255,.09)` bg) + light content bg `#F5F7FA`, surface `#FFF`, border `#E4E9F0`.
- Accent = **Tether green `#26A17B`** (matches USDT money semantics: primary buttons, balances, active states).
- Radii 8/6/4px (card/control/badge) — deliberately tighter than generic 12/8 SaaS defaults for a financial feel.
- Status badges = semantic soft-bg pairs: green(正常/已退款/在售), blue(待发货/运输中/处理中), orange(售后), amber(待审核), red(超时/异常/删除), gray(草稿/已关闭/已完成).
- Money everywhere: `font-variant-numeric:tabular-nums`, mono font for order/SKU/TX ids, `USDT` as the unit.

## Dashboard composition rule (user correction — do not regress)

User rejected a 9-module cluttered dashboard. Mainstream marketplace pattern (Shopify / TikTok Shop seller center), top to bottom:

1. **KPI row** — 4 cards (今日销售额 / 今日订单 / 今日访客 / 可提现余额), each with label + big tabular number + ▲/▼ delta vs yesterday.
2. **Two-column band** — sales trend chart (7/30-day toggle + hover tooltip) + todo list with inline action buttons (去发货/处理/去审核), each item = icon tile + title + sub-line + button.
3. **Recent orders** — full-width table.

Strip from home: shop card (info lives in nav identity card), 8-tile quick-actions grid (all in nav), wallet sidebar + recent withdrawals (fold into KPI / funds page), recent products. Decision path: status → trend → action → detail.

**Layout must fill the canvas** — do NOT cap `.content` with `max-width`. The user complained a `max-width:1180px` left half the screen empty.

## Dependency-free SVG area chart

Hand-rolled, no libraries: fixed `viewBox` (760×240), `width:100%;height:auto`. Points → smooth path via mid-point quadratic (`C mx,y0 mx,y1 x1,y1`), area = line + close to baseline, gradient fill `<linearGradient>` brand-green 22%→0. Hover: transparent `<rect>` hit layer + `getBoundingClientRect` scale mapping → dashed crosshair `<g>` + absolutely-positioned HTML tooltip. Range toggle re-renders `svg.innerHTML` from two data arrays. Grid = 4 horizontal lines with y labels, x labels every 5th day (30d) or daily (7d).

## Verification checklist

1. `browser_navigate` to `file:///C:/Users/...` — **URL-encode non-ASCII in the path** (e.g. `%E5%8D%96...`).
2. `browser_console` route traversal: loop all routes calling `show(r)`, report missing `view-*` ids and thrown errors; then exercise key interactions (tab switch, modal open, step wizard) and assert `.style.display`/class state.
3. `browser_console` (no args) → confirm zero js_errors.
4. `open_preview` with the file path so the user sees it immediately.

## User workflow preferences (this user)

- **Minimal first**: when asked to redesign, build ONE representative page (dashboard) for style sign-off before building all pages ("先做个简单的出来给我看看").
- Then all pages in one pass ("把所有的页面都做出来"), then iterate page-by-page on request.
- All UI copy in Chinese; demo actions show a toast (`toast('已提交平台审核')`) instead of dead buttons; include status/empty/error states in the demo data.
- Keep hover/focus states real; inline SVG stroke icons (`stroke-width:1.8`, 24 viewBox); no emoji in chrome (product thumbnails may use glyphs like ⌁ ◈ ✳).
- When the user says "挨个页面去调整", present a page inventory table and ask which page to start with — don't dump changes.

## Pitfalls

- Inline `onclick` handlers require globally-scoped functions — define interaction helpers (`toast`, `openModal`, `qty`, `sendCode`, step/tab functions) in the final JS patch, not inside module scope.
- `delSku`/row-delete guards: keep ≥1 SKU row; check row count before removing.
- Step wizards (onboarding, product publish) share one `steps` component: `on/done` classes on step items + `display:none` on panels; update prev-button visibility and last-step button text (下一步→完成).
- Verify-code buttons: disable + 60s countdown, re-enable on 0.
- Modal: click-outside-to-close via mask listener `if(e.target===mask) close`; escape-hatch X button.
- Files: save to `C:\Users\Administrator\Desktop\`, keep prior versions (`-v1`, `-v2`) when iterating.
