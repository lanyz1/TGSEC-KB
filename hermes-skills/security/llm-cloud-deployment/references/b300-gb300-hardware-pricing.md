# B300 / GB300 hardware family + on-prem feasibility (verified 2026-08-03)

Sources: NVIDIA official pages (GB300 NVL72, DGX B300), NVIDIA docs NVL72 AI Factory reference arch,
Spheron B300 guide + live pricing page, RunPod pricing page. All figures are what was actually
pulled on 2026-08-03; prices drift — re-verify and date-stamp.

## B300 GPU (Blackwell Ultra) — single SXM module
- 288 GB HBM3e, 8192-bit, ~8 TB/s per GPU
- TDP: **two SKUs exist** (critical for procurement):
  - **B300 SXM6 AC = air-cooled, 1100 W** ← the one that works in a traditional air-cooled rack
  - **B300 SXM6 DC = liquid-cooled, 1400 W** (what most specs quote as "B300 = 1400W")
- FP4 dense ~15 PFLOPS, FP8 dense ~7 PFLOPS, FP16 dense ~3.5 PFLOPS
- NVLink 5 (1.8 TB/s), ConnectX-8 networking (1.6T optical)

## System form factors
| Form | Composition | Power | Height | Cooling |
|---|---|---|---|---|
| GB300 NVL72 rack | 72× B300 + 36× Grace CPU (2592 Arm v2 cores) | **132–155 kW/rack** | full rack | mandatory liquid (cold plates on CPU/GPU/NVSwitch/power) |
| GB300 NVL compute tray (NVL4) | 4× B300 + 2× Grace CPU, 1152 GB HBM3e + 1 TB LPDDR5X | ~5.5–7 kW | ~4–8U | liquid |
| **DGX B300** | **8× B300 SXM + 2× Intel Xeon 6776P** | **~14 kW (DC) / ~11–12 kW (AC)** | **10U** | **AC or DC variant — pick AC for air-cooled rooms** |
| DGX B300 specs | 2.1 TB total GPU mem; 144 PFLOPS sparse FP4 / 108 dense; NVLink 14.4 TB/s (2× NVSwitch); 8× 800 Gb/s ConnectX-8 + 2× BlueField-3 DPU; 8× 3.84 TB E1.S NVMe | | | |

GB300 NVL72 rack internals (from NVIDIA docs): 18 compute trays + 9 NVSwitch trays; 8 power
shelves of 33 kW each (6× 5.5 kW PSUs per shelf); in-rack switches run DC from busbar;
tray + rack liquid-leakage detection. 72-GPU single L1 NVLink domain, 130 TB/s aggregated.

## On-prem rack feasibility — the math that decides everything
- Rack power ceiling (China mains):
  - single-phase 220 V × 32 A = **7.0 kW**
  - three-phase 380 V × 32 A × √3 = **21.1 kW**
- First question to the user: **single-phase or three-phase 32A?** Single-phase cannot run even
  ONE DGX B300 (needs ~14 kW). Three-phase 32A runs exactly one DGX + ~2–3 kW of switch/storage
  per rack with healthy headroom (~66% load).
- Cooling: B300 DC / GB300 NVL72 require liquid (CDU + plumbing + outdoor loop). Only the
  **AC SKU (1100 W/card)** is viable in a traditional air-conditioned rack room. NVL72 total
  heat ≈ 10 domestic AC units; plan ~1.4× electrical kW in cooling.
- Weight: NVL72 rack 1.5–2 t; DGX ~150–200 kg — verify rack floor/rails rating (≥250 kg/rack for DGX).
- Interconnect across multiple 8-GPU nodes: **NVLink is intra-node only** (14.4 TB/s inside one
  DGX). Cross-node = InfiniBand (Quantum-X800, 800 Gb/s per port) or Spectrum-X Ethernet;
  2× DGX B300 = 16-GPU cluster needs 1× 32-port QX800 switch. Do NOT promise NVLink across racks.

## Pricing snapshot (2026-08-03, USD)
Rental (per GPU/hr):
- Spheron B300 spot **$5.81**, on-demand **$9.16**; RunPod serverless B300 **$9.98**
- Managed DGX B300 (full stack): $12–18
- Benchmarks: H100 $2.64 (spot $1.46), H200 $5.90 (spot $3.31), B200 spot $5.34, A100 $1.48
- 16× B300 24/7 for a month: spot ≈ $6.7k, on-demand ≈ $10.6k, managed ≈ $14–21k
Buy: DGX-class 8-card system is 6-figure USD; 2× DGX B300 AC + IB switch ≈ ¥150–250 万.
Rule of thumb: buy only for ≥2 years of 24/7 heavy use; otherwise rent spot.

## Verified data-source quirks (this session)
- NVIDIA product pages render fine in browser; datasheet PDFs sit behind Widen/Pathfactory
  anti-bot (direct curl gets JS challenge or 404). Workaround: open the resources.nvidia.com
  landing page, read the iframe src via browser_console (`document.querySelector('iframe').src`)
  → real widen URL; direct PDF download still blocked, but the viewer + NVIDIA product page
  tables carry the specs.
- DuckDuckGo html endpoint rate-limits after 1–2 queries (empty output); lite.duckduckgo.com
  throws an anti-bot form; Bing search HTML has no `b_algo` parseable results via curl;
  TechPowerUp 403s bots. Fastest reliable path = go straight to vendor pages (nvidia.com,
  spheron.network/pricing, runpod.io/pricing) rather than burning time on search engines.
