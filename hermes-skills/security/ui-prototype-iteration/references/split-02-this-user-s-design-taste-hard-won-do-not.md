## This user's design taste (hard-won — do NOT re-litigate the palette)
Rejection history: ① generic SaaS palettes (gold/indigo/teal/black) → "太老套" ② tech/neon (glow, gradients, grid lines, glass) → "AI 味道太重" ③ TikTok style (black sidebar + pink) → "还是不满意". **Approved: Apple HIG style, variant "A2 纯白极简"** (full token set in `references/seller-center-design-iteration.md`).

Approved direction (Apple HIG: 清晰 / 遵从 / 深度):
- Light theme: white/near-white bg, white surfaces. NO gradients, glow, grid lines, glassmorphism
- Sidebar: light gray `#F9F9F9`, gray text `#6E6E73`; active item = subtle dark bg + black bold text, NO left color rail
- Primary buttons: **black** (`#000`, hover `#2E2E30`), capsule `border-radius:999px`; secondary = thin-border outline capsule
- Accent blue `#0071E3` only for links / login slogan emphasis; KPI & balance numbers plain black
- Status badges: Apple system colors as capsule pills on 12% alpha tints — green `#34C759` / blue `#007AFF` / orange `#FF9500` / red `#FF3B30` / gray `#8E8E93`; text uses deep variants for contrast (`#248A3D`, `#0A60C0`, `#B25A00`, `#D70015`)
- Type: system font stack (SF Pro / PingFang), big page titles (26–28px bold), `tabular-nums` for figures, mono for order/ID numbers
- Radii: cards 16px, controls 10px, badges/buttons capsule; hairline borders `rgba(0,0,0,.07–.09)`, near-zero shadow; generous whitespace; table header bg `#FAFAFC`
- Login page: black brand panel + white form panel, white logo block on black, blue accent
- Single accent hue; semantic colors only for status/abnormal states

