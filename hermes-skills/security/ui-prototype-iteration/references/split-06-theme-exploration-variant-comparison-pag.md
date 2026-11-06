## Theme exploration: variant comparison page (user's preferred way to choose)
- User wants FULL-PAGE renders side by side ("四组都出一下样图"), not component cards or hex swatches alone
- Build ONE comparison HTML: N variants each render the SAME complete dashboard template (sidebar + topbar + KPI + chart + todos + orders table)
- Theming: define all colors as CSS vars inline per variant frame — `<div class="frame" style="--brand:#000;--nav-bg:#F9F9F9;…">` with one shared JS template string rendered N times
- Scale down full-size mockups: `.frame{width:1100–1240px;transform:scale(.36–.55);transform-origin:top left;pointer-events:none}` inside an overflow-hidden wrapper
- Each card: name + one-line description + color swatches with hex + click-to-select highlight; user replies a letter, then roll that variant's token set out globally

