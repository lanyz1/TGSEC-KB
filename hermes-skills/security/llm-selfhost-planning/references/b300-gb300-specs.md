# NVIDIA B300 / GB300 (Blackwell Ultra) — verified specs (2026-08)

Source: nvidia.com GB300 NVL72 product page, docs.nvidia.com NVL72 AI Factory ERA components page, HPE/Lenovo datasheets, TechPowerUp. All figures verified during a live rack-feasibility consultation.

## B300 GPU (SXM module)
- Architecture: Blackwell Ultra (TSMC 4NP)
- Memory: **288GB HBM3e** per GPU, 8192-bit bus (TechPowerUp lists 4096-bit per-GPU interface for the 2-GPU-pack variant; single SXM = 288GB)
- Memory bandwidth: ~8TB/s per GPU
- TDP: **1100W rated (SXM6 AC), up to 1400W peak**
- **CRITICAL: two SKUs exist — AC vs DC.** B300 SXM6 **AC** = 1100W, deployable AIR-COOLED in a normal datacenter rack. B300 SXM6 **DC** = 1400W, requires liquid cooling (cold plate + CDU). NVIDIA's "AC and DC power options" wording on the DGX B300 page refers to exactly this split. **When a user with an air-cooled rack wants B300, the purchase MUST be the AC version — buying DC means the system cannot run in their room.**
- FP4 ~20 PFLOPS dense-class (sparse spec from GB300 NVL72: 1440 PFLOPS FP4 / 72 GPUs = 20/GPU; FP8/FP6 720 PFLOPS / 72 = 10/GPU)
- Cooling: **liquid cold-plate mandatory above 1100W/卡** — >700W/卡 cannot be air cooled
- Interconnect: NVLink 5, 18 links/GPU, 1.8TB/s per GPU

## DGX B300 / HGX B300 (8-card module — the B300 form factor that FITS a 32A rack)
Verified from nvidia.com DGX B300 product page (2026-08).
- **8× B300 SXM** (each 288GB) = **2.1TB total GPU memory**; 2× Intel Xeon 6776P
- Compute: FP4 144 PFLOPS (sparse) / 108 (dense); FP8 72 PFLOPS
- NVLink: 2× NVLink Switch system, **14.4TB/s aggregate** (intra-node only)
- Network: 8× OSFP ConnectX-8 (800Gb/s each) + 2× BlueField-3 DPU (400Gb/s)
- Storage: 2×1.9TB M.2 OS + 8×3.84TB NVMe E1.S
- **Power: ~14kW (DC/liquid version); AC (air-cooled) version ≈ 11-12kW** (8×1100W + CPUs)
- **10U** rack units; AC/DC power options; fits MGX and traditional enterprise racks
- **Rack verdict (48U, 三相 32A = 21.1kW/rack): 1× DGX B300 AC + switch + storage ≈ 14kW → FITS with ~7kW headroom. This is the ONLY B300-class config a 32A rack can host.** Single-phase 32A (7kW) cannot even run one unit.
- **Multi-node (16-card / two racks):** two DGX B300 are NOT NVLink-linked across nodes — cluster them via **Quantum-X800 InfiniBand switch (800Gb/s)** or Spectrum-X Ethernet. Two racks × 三相 32A each: 1 unit per rack ≈ 14kW of 21.1kW → viable, but each unit needs its own breaker and no other high-draw gear in the rack.
- Budget: 2× DGX B300 + IB switch ≈ ¥150-250万 total; vs renting 16× B300 ≈ $6.7-11万/month — self-host only pays off for 24/7 heavy use ≥1-2 years.

## GB300 NVL Compute Tray ("NVL4", single-node building block)
- 4× B300 + 2× Grace CPU (72 Arm Neoverse V2 cores each, NVLink C2C, 1TB LPDDR5X aggregated CPU memory)
- GPU memory: 1,152GB HBM3e aggregated (4×288)
- Per-tray power: **~5.5-7kW** (derived: rack has 8 power shelves × 33kW, 6×5.5kW PSUs per shelf; 18 trays/rack)
- Storage: 1× M.2 OS + 4× E1.S NVMe cache; BlueField-3 DPU; 4× ConnectX-8 (800Gb/s each)

## GB300 NVL72 (rack-scale)
- 72× B300 + 36× Grace CPU (2,592 cores), 9× NVSwitch trays, 18 compute trays
- Memory: 20TB GPU HBM3e + 17TB LPDDR5X = 37TB; 576TB/s GPU bandwidth
- NVLink domain: 130TB/s aggregated, all 72 GPUs in one L1 domain (fully non-blocking P2P)
- Power: **132-155kW per rack** (8× 33kW shelves; 142kW per NVIDIA docs; 155kW peak per Lenovo)
- Cooling: full direct liquid cooling (GPU/CPU/NVSwitch/power cold plates) + supplemental air
- Weight: ~1.5-2t per rack (reinforced floor required)
- Network: ConnectX-8 SuperNIC 800Gb/s east-west; BlueField-3 400Gb/s north-south
- Feeds: DC busbar inside rack; facility side needs 480V/415V three-phase, 30-60kW/rack density class

## Rack power ceiling math (China standard)
- Single-phase 220V × A = kW → 32A = **7.0kW**
- Three-phase 380V × A × √3 = kW → 32A = **21.1kW**
- 48U/32A rack verdict for B300: 整柜 NVL72 差 6-22x 电 → impossible; single NVL4 tray 电勉强(三相) but liquid cooling/CDU/network all missing → still no
- Realistic 32A ceiling: 单相 6-8× 普通 1U/2U 或 1× ≤700W 风冷卡;三相 2-3× 8卡风冷 H100/H200 服务器

## DGX Spark (desktop alternative — no rack needed)
Verified from NVIDIA official product page + developer blog "Scaling Autonomous AI Agents and Workloads with NVIDIA DGX Spark" (2026-03).
- 1× GB10 Grace Blackwell superchip (Blackwell GPU + Grace CPU), **128GB coherent unified memory**, ~1 PFLOPS FP4, ~140W, Mac-mini form factor
- Inference ≤200B params single unit; fine-tune ≤120B; FP4 support
- **Cluster limit: officially "up to four DGX Spark nodes"** via ConnectX-7 RoCE (800Gb/s-class, low latency, standard ethernet switch — NOT NVLink). 4-node = 512GB unified memory, fine-tune/inference **≤700B params**, near-linear scaling (1→2→4 nodes: Isaac Lab collection 12.1s→11.4s→10.4s)
- Cost: ~$4-5k/unit → 4-unit cluster ≈ $16-20k. Runs 167GB-class weights (e.g. DeepSeek-V4-Flash) across 512GB. Compute is an order of magnitude below DGX B300 (4 PFLOPS vs 144 PFLOPS) — dev/test class, not production concurrency
- Use case split: "能跑/开发" → Spark cluster; "能商用/高并发" → DGX B300
- Pricing context: NVIDIA marketplace + retail (Amazon/Micro Center/PNY/Arrow/TD Synnex)

## Pricing context (2026-08, per GPU/hr)
### RunPod
- B300 $9.98 (serverless) — 288GB class; B200 $8.64; H200 $5.93 / cluster $4.31; H100 $4.55; RTX 6000 Pro $3.49; A100 $2.72; L40S $1.75; 5090 $1.58
- Vast.ai on-demand typically 15-40% cheaper; B300-class availability on Vast is thin — treat as "effectively unavailable" if not in top offers

### Spheron (live marketplace, 2026-08-03)
- **B300: spot $5.81/hr, on-demand $9.16/hr** (262GB listing, 2768GB RAM, 192 vCPUs); managed DGX B300 tier $12-18/hr
- H200 $5.90 / spot $3.31; B200 spot $5.34; H100 $2.64 / spot $1.46; A100 $1.48 / spot $0.82; RTX PRO 6000 $2.39 / spot $1.29; L40S $0.96; RTX 4090 $0.53
- GB300/GB200 NVL72 and R100 (Rubin, ships H2 2026) are reserve-only (no on-demand)
- 16× B300 spot 24/7 ≈ $6.7万/月; on-demand ≈ $10.6万/月; managed ≈ $14-21万/月
