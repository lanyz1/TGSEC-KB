# Apple-Minimal (A2) token set — instant re-application

Exact `:root` block + component values approved by the user for the Qavlixor seller center (2026-07-31). Copy into a new prototype's CSS when the user wants "Apple 风 / 纯白极简 / 黑白" style.

## :root tokens

```css
:root{
  --nav-bg:#F9F9F9; --nav-ink:#6E6E73; --nav-ink-active:#1D1D1F;
  --nav-item-hover:rgba(0,0,0,.05); --nav-item-active:rgba(0,0,0,.07); --nav-border:rgba(0,0,0,.08);
  --bg:#FFFFFF; --surface:#FFFFFF;
  --border:#E8E8ED; --border-strong:#D4D4D9;
  --ink:#1D1D1F; --muted:#6E6E73; --faint:#98989F;
  --brand:#000000; --brand-ink:#1D1D1F; --brand-soft:rgba(0,0,0,.05);
  --link:#0071E3;
  --g:#34C759; --gs:rgba(52,199,89,.12);
  --blue:#007AFF; --blue-soft:rgba(0,122,255,.1);
  --orange:#FF9500; --orange-soft:rgba(255,149,0,.12);
  --amber:#FF9500; --amber-soft:rgba(255,149,0,.12);
  --red:#FF3B30; --red-soft:rgba(255,59,48,.1);
  --gray-soft:#F2F2F4; --gray-ink:#6E6E73;
  --mono:ui-monospace,SFMono-Regular,"Cascadia Mono",Consolas,monospace;
  --r-lg:16px; --r-md:10px; --r-sm:8px;
  --shadow:0 1px 2px rgba(29,29,31,.03);
}
```

## Component values (Apple HIG application)

- **Buttons**: pill `border-radius:999px`; primary black bg + white text, hover `#2E2E30`; secondary = white + `--border-strong` border
- **Status pills** (`.st`): pill radius, light tint bg (~10-12% alpha) + darker text:
  `.st.green{background:var(--gs);color:#248A3D}`
  `.st.blue{background:var(--blue-soft);color:#0A60C0}`
  `.st.orange{background:var(--os);color:#B25A00}`
  `.st.red{background:var(--rs);color:#D70015}`
  `.st.gray{background:var(--gray-soft);color:#6E6E73}`
  `.st.amber{background:var(--os);color:#B25A00}`
- **Nav (light sidebar)**: selected item = `rgba(0,0,0,.07)` bg + bold `#1D1D1F` text, NO left color bar; avatar bg `rgba(0,0,0,.07)`; logo mark black bg white "Q"
- **Page head**: h2 `24px / 700 / letter-spacing:-.4px`; sub line `12.5px --faint`, margin-top 6px
- **Topbar**: 52px, `--surface`, bottom border `--border`; only a small crumb label left (no duplicate big title)
- **KPI cards**: label `12px --muted` plain text (NO colored dots), value `23px/700` tabular, trend `11px` with `--g` (up) / `--r` (down)
- **Charts**: line `#1D1D1F` 2px, area gradient `rgba(29,29,31,.14) → 0`, previous-period dashed `#C9C9CE` `1.5px` `stroke-dasharray:4 4`, grid `#F0F0F2` (3 lines), y-labels `#98989F` 10px OUTSIDE plot (`PAD.l ≈ 44`), x-labels sparse (step 7 for 30d / 2 for 7d), end-point: white dot + black ring + bold value label above, tooltip = dark pill
- **Login brand panel**: black `#000` bg, white logo mark (black glyph), slogan accent `#0071E3`, feature icons stroke `#0071E3`
- **Dates**: `2026年7月31日 · 周五` (Chinese format, not ISO)

## Stale-hex grep list (old palettes to purge after a switch)
`#26A17B` `#1E8D6C` `#0E7A5F` `#0E1526` `#8B97AD` `#E4E9F0` `#D5DCE6` `#101828` `#667085` `#98A2B3` `#2563EB` `#1D4ED8` `#D97706` `#B45309` `#E5484D` `#C3363B` `#F1F3F7` `#FBFCFE` `#EEF2F7` `#FBFBFD`
