## Theme roll-out procedure (palette/light↔dark swap)
1. Patch the `:root` token block wholesale (colors, radii, shadow)
2. Sweep hardcoded colors that no longer fit: nav `color:#fff` text, avatar backgrounds, `#FBFCFE` table/chat headers, SVG chart stroke/fill hex + grid + hover-line colors, login brand panel, leftover old-hue hovers (e.g. green hover on buttons)
3. Re-point semantic classes (`.st.green` etc.) to the new tokens — don't let badges keep referencing brand vars after the accent changed
4. Re-verify: route sweep + computed-style spot check (`getComputedStyle` on nav bg and primary button bg) via browser_console

