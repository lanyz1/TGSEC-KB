# Qavlixor 卖家端 — Project State

Cross-border e-commerce seller center (like Shopify / TikTok Shop seller backend). Currency: USDT only. Status: prototype built, theme selection pending (awaiting user pick of T1/T2/T3).

## Files on Desktop
- `Qavlixor-卖家端-全部页面.html` — MASTER prototype: 15 views, hash router, single file. This is the file themes get applied to (swap `:root` vars).
- `Qavlixor-工作台-v1.html` — v1 dashboard (rejected: 太杂乱).
- `Qavlixor-工作台-v2.html` — restructured dashboard: KPI row → chart+todo → recent orders. Structure APPROVED.
- `Qavlixor-配色方案.html` — 4 traditional schemes (rejected as 老套).
- `Qavlixor-配色样图.html` — same 4 schemes as full-page mockups.
- `Qavlixor-科技风配色样图.html` — 4 cyber/neon schemes (rejected: AI味道太重).
- `Qavlixor-TikTok风样图.html` — 3 TikTok-style schemes, awaiting pick:
  - T1 黑粉经典: black #161823 + pink #FE2C55 (default selected)
  - T2 官方蓝: black + blue #0A84FF, topbar search box
  - T3 粉青双色: pink #FE2C55 + cyan #25F4EE (chart uses cyan)
- `卖家端功能模块清单.md` — stripped functional spec (source of truth for modules/fields/states).

## Routes (15 views)
- auth (no shell, `body.auth-mode`): login / register / onboarding (4-step wizard) / status (审核进度 3 段)
- app: dashboard / products / product-new (4-step form + right rail) / orders / order-detail / logistics (timeline) / aftersales / aftersales-detail (4-option form + state lock) / messages (3-pane chat + AI summary + order context) / funds (2 wallet cards + 7 tabs + cashier modal with countdown) / account

## Design decisions so far
- Structure follows Shopify/TikTok Shop: KPI row → sales chart + todo list → recent orders. Removed: shop card, 8 quick links, recent products, right-rail wallet (merged into KPI + funds page).
- Interactive pieces built: 7/30-day chart toggle with hover tooltip, SKU row add/del, param add, qty steppers, batch bar on checkbox select, delete + cashier modals, 60s code countdown, chat list select, funds tab switching (use `data-tab`), wizard steps.

## Pending
1. User picks theme letter (T1/T2/T3 or tweak). Apply = replace `:root` vars in master file with chosen scheme's vars (TikTok vars include: --nav-bg #161823, --brand #FE2C55/#0A84FF, --surface #FFFFFF, --bd #ECECEF, plus semantic g/gs/b/bs/o/os/r/rs/gy/gys pairs).
2. Then iterate page by page ("挨个页面去调整") — start wherever user points.
