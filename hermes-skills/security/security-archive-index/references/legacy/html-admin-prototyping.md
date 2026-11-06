<!-- archived from /root/.hermes/skills/security/html-admin-prototyping/SKILL.md on 2026-10-21 -->

---
name: html-admin-prototyping
description: >-
  测绘引擎·Admin/dashboard HTML prototypes (卖家端). Minimal first.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/html-admin-prototyping`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/html-admin-prototyping/…')`，不要相对 `references/legacy/` 解析。

# html-admin-prototyping（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/html-admin-prototyping/`

溯源（仅标记）：`hermes/creative`

---

# HTML Admin / Dashboard Prototyping

Build high-fidelity, single-file HTML prototypes for admin consoles / seller backends (工作台 / 商品管理 / 订单 / 资金中心 / 后台界面), following the iteration workflow this user expects. Complements the generic `claude-design` skill (hub-installed, protected) with user-specific workflow and environment-verified techniques.

## When to use
- User asks to design/redesign a backend page or a whole seller-center UI
- User hands a functional spec (like the 卖家端功能清单) and wants a visual prototype
- Iterating on an existing HTML prototype (style tweaks, adding screens)

## Workflow (user expectation — non-negotiable)
1. **One style question max.** If the visual direction is open, ask ONE `clarify` with 3-4 concrete directions (浅色商务风 / 深色侧边栏+浅色内容 / 极简留白 / 全站深色). Never a battery of questions. User picked "深色侧边栏 + 浅色内容区 · 金融后台风" for the current project.
2. **Minimal sample FIRST.** Build ONE screen (the core page — usually 工作台) as a style sample. Do NOT build all screens upfront — user explicitly said "先做个简单的出来给我看看". Get approval, then expand.
3. **Composition > color.** If the user says 太杂乱 / 不满意构造, restructure to mainstream platform patterns (see below) — do NOT just recolor the rejected layout.
4. **Preserve versions.** Save as `Name-v1.html`, `Name-v2.html`… never overwrite an approved version.
5. **Delivery loop**: write file to Desktop → `open_preview` (user sees it instantly) → short summary (what's inside + what to confirm). No long prose; user is a 纯小白 who wants the agent to do everything.

## Dashboard structure that won this user's approval
v1 (9 modules: shop card + todo grid + 4 stats + 8 quick links + orders + products + wallet + withdrawals) was rejected as 太杂乱. Approved v2, matching Shopify / TikTok Shop seller centers:
1. **KPI row** — 4 cards: 今日销售额 / 今日订单 / 今日访客 / 可提现余额, each with 较昨日 trend (▲/▼)
2. **Two-column**: sales trend chart (SVG, 7/30-day toggle, hover tooltip) + 待办事项 list with per-item action buttons (去发货 / 处理 / 去审核)
3. **Recent orders** full-width table (订单号 / 买家 / 商品 / 金额 / 状态 / 操作)

Cut from the feature spec: shop card (info already in the nav identity card), quick-entry grids (duplicated by nav), recent products, sidebar wallet (folded into KPI; details live in 资金中心). Rule of thumb: every block must answer "今天卖得怎么样" or "现在要处理什么" — otherwise it doesn't belong on the dashboard.

## Technical patterns (verified in this environment)
- **Single self-contained HTML file**: embedded `<style>` + `<script>`, CSS variables for all tokens, zero external dependencies.
- **NO web fonts** — GFW blocks Google Fonts. System stack: `-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif`. Numbers get `font-variant-numeric:tabular-nums`.
- **Inline stroke SVG icons** (17-19px, `fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round`), hand-written per nav item / quick action. No emoji, no icon fonts.
- **Hand-rolled SVG chart** (no chart lib, ~50 lines JS): smooth path via midpoint cubic bézier (`C mx,y0 mx,y1 x1,y1`), linear-gradient area fill, 4-5 grid lines with y labels (scale by max*1.12), x labels at stride (1 for 7-day, 5 for 30-day), hover = transparent `<rect>` + mousemove → nearest index → dashed v-line + dot + absolutely-positioned tooltip div; range toggle re-renders via `svg.innerHTML`.
- **Verify before delivering**: `browser_navigate` the `file://` URL, `browser_console` must show 0 errors, then `open_preview`. Include `MEDIA:<path>` link in the reply.
- **Status pills**: soft bg + strong text (绿 `#E7F6F0/#0E7A5F`, 蓝 `#EAF2FE/#1D4ED8`, 橙 `#FEF3E7/#B45309`, 灰 `#F1F3F7/#475467`). Count badges: red pill, hidden at 0, `99+` cap.

## Bulk text / language conversion (中→EN or any global text pass)
When the user asks to flip the whole prototype's language (Qavlixor is now fully English), use the batch mapping-table recipe in `references/full-site-i18n-conversion.md`. The critical trap it documents: a text-replacement pass over a single-file HTML also corrupts the inline JS and CSS — every `.` becomes `. ` (dot-space), so `querySelectorAll('. view')` throws at init and the whole script dies. User-visible signature: **曲线图没了 + 按钮不能点击 + hash 路由卡在首页**. `node --check` passes on this (it's legal JS), so diagnose via browser runtime errors, fix by restoring `. ` inside the `<script>` block only, rebuild CSS selectors (descendant split vs same-element multi-class whitelist), and always cache-bust file:// previews with `?_=Date.now()`.

## Pitfalls
- Don't stack every module from the feature spec onto one dashboard screen — what you CUT is the design decision that matters most.
- Don't ask the user to do manual browser steps (F12, copying things); preview pane + MEDIA link is the entire delivery loop.
- Chinese filenames in `file://` URLs must be percent-encoded (`Qavlixor-工作台-v1.html` → `file:///C:/.../Qavlixor-%E5%B7%A5%E4%BD%9C%E5%8F%B0-v1.html`).
- After the user picks a direction, still deliver a small sample before building all screens — direction approval ≠ full-build approval.

## Project state
See `references/qavlixor-seller-design.md` for the current Qavlixor seller-center design tokens, approved workbench structure, Desktop file locations, and the ~18 screens still to build.
