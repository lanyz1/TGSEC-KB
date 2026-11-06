---
name: llm-selfhost-planning
description: >-
  测绘引擎·Size hardware & rent cloud GPUs to self-host open LLMs.
owned: true
tier: general
pack: survey-skill
---

# llm-selfhost-planning（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/llm-selfhost-planning/`

溯源（仅标记）：`hermes/mlops`

---

# LLM Self-Hosting Planning

Plan deployment of open-source LLMs: figure out what hardware a model needs, then where to rent it and what it costs. Covers HuggingFace model assessment (no download), VRAM math, and live GPU cloud price discovery.

## When to use
- User asks "what config/hardware do I need for model X" / "can I deploy model X"
- User asks where to rent GPUs and what it costs per day/week/month
- Comparing GPU cloud providers (Vast.ai, RunPod, AWS, etc.)

## Step 1 — Assess model from HuggingFace (no download needed)
Run `scripts/hf_model_sizing.sh <model-id>` or manually:
- Meta: `curl https://huggingface.co/api/models/<id>` — tags show license, quantization, architecture
- Config: `curl https://huggingface.co/<id>/raw/main/config.json` — architecture, hidden_size, layers, MoE experts, context length, quantization_config
- Weight size: `curl https://huggingface.co/api/models/<id>/tree/main?recursive=true` → sum `size` fields; this is the REAL disk/VRAM floor
- Some repos ship extra configs (e.g. `inference/config.json`) — check the tree listing first

## Step 2 — VRAM / disk rules of thumb
- Total weight bytes ≈ minimum VRAM to hold weights (FP8/FP4 checkpoints are already quantized)
- Add headroom for KV cache + activations: practical minimum ≈ 1.5× weights, comfortable ≈ 2×
- Long-context models (1M tokens) need massive KV cache — don't run full context unless required; official recipes often recommend a max-model-len cap (e.g. 384K for think-max modes)
- MoE = small activated params but FULL weights in memory — a "small" MoE can still need 500GB+ VRAM
- Disk: weights + conversion scratch; round up to practical NVMe tiers (1TB/2TB/3.84TB)

## Step 3 — On-prem rack feasibility check (user has own rack/机房)
When the user says "我有机柜 XXU / XXA 供电,能装吗" — power, cooling, and network gates decide BEFORE space:
- **Power ceiling math**: single-phase 220V×A → kW; three-phase 380V×A×√3 → kW. 32A: 7.0kW (single) / 21.1kW (three-phase). Compare vs target system demand (B300 SXM 1.1-1.4kW/卡; NVL4 tray ~5.5-7kW; GB300 NVL72 rack 132-155kW = needs 480V/415V three-phase at 30-60kW/rack density, NOT a 32A feed).
- **The one B300 config that FITS a 32A rack: DGX B300 / HGX B300 8-card module (10U, ~14kW DC / ~11-12kW AC).** Two racks × 三相 32A each = viable 16-card cluster. BUT check the AC/DC SKU: B300 SXM6 **AC** = 1100W air-coolable; **DC** = 1400W liquid-only. On an air-cooled rack you MUST order the AC version — this is the silent killer that makes or breaks the whole purchase. See references/b300-gb300-specs.md.
- **Cooling gate**: >~700W/卡 means liquid cooling is mandatory (cold plate + CDU + external heat rejection). A plain air-cooled rack cannot host B300/H200-8卡 class systems. Check this BEFORE quoting feasibility — it's usually the silent killer.
- **Multi-node interconnect**: two DGX-class nodes are NOT NVLink-linked across racks — cluster them via Quantum-X800 InfiniBand (800Gb/s) or Spectrum-X Ethernet switch.
- **Other gates**: NVLink-scale interconnect (800Gb/s ConnectX-8 / InfiniBand) needs matching switches; rack weight (NVL72 ~1.5-2t) needs reinforced floor; power feed tier must match density class.
- Realistic ceiling for a 32A rack: 单相 → 6-8台普通1U/2U or one ≤700W air-cooled card; 三相 → 1台 DGX B300 AC (8卡) or 2-3台 8卡风冷 H100/H200 servers. Never promise GB300 NVL72 on 32A.
- If it doesn't fit: pivot to cloud rental (Step 4) rather than forcing a rack upgrade — CDU + 63A+ feed + reinforcement costs exceed the hardware.
- **Desktop alternative to offer when the user's goal is "能跑" not "生产并发"**: DGX Spark cluster — up to 4 nodes via ConnectX-7 RoCE, 512GB unified memory, ≤700B params, ~$16-20k, plugs into a wall socket (no rack/power work). Compute is 1-2 orders of magnitude below DGX B300 though (4 vs 144 PFLOPS) — dev/test only.
- **Spec lookup when NVIDIA pages 404** (`/b300-nvl4/` is 404; `/gb300-nvl72/`, `/dgx-b300/` work): `curl -sL "https://html.duckduckgo.com/html/?q=<query>" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"` then parse `result__a`/`result__snippet`. ⚠️ DDG html endpoint rate-limits after ~2 rapid queries (returns empty) — wait or switch to lite.duckduckgo.com (may hit captcha) or Bing via curl (often 0 `b_algo` matches — structure differs). Vendor datasheets (HPE/Lenovo/Supermicro PDFs) give rack kW numbers (e.g. HPE: 132-140kW/rack; Lenovo: 135kW TDP, 155kW peak). NVIDIA resources.nvidia.com datasheets are JS-shells (widen.net blocks curl with HTML/JS stubs) — use browser_navigate + browser_console to read the rendered PDF iframe instead.

## Step 4 — Cloud GPU price discovery
### Vast.ai (cheapest; NO LOGIN REQUIRED for the search page)
- Search page: `https://cloud.vast.ai/create/` — all filters work logged-out
- Set: GPU count button (1X/2X/4X/8X), then GPU dropdown → type model name in its search box → tick the exact GPU checkbox
- **PITFALL: prices are NOT in the compact snapshot.** Click the card's inner clickable area (the spec region) to expand it, then `browser_snapshot(full=true)` — the `$X.XXX/hr` line and a full price breakdown (GPU/hr, disk/hr, day, month) appear at the card bottom. If the snapshot gets truncated, read the saved snapshot file from the truncation notice.
- **PITFALL: `vast.ai/api/v0/bundles` requires an api_key** (308 redirect without it) and `vast.ai/pricing` is JS-loaded (no data in plain snapshot) — skip both, go straight to the create page.
- Check the instance's "Max CUDA" field against the model's CUDA requirement before renting (e.g. DeepSeek-V4 needs ≥12.8).

### RunPod
- `https://www.runpod.io/pricing` — Serverless and Clusters tables show per-GPU $/hr directly in the snapshot (B300 $9.98, B200 $8.64, H200 $5.93, H100 $4.55; Cluster H200 $4.31). Pod card prices require clicking through.
- The Community Cloud radio toggle did NOT switch the list (tested 2026-08); use Vast.ai for community-cloud pricing instead.

### Spheron (second live source, especially for B300-class)
- `https://spheron.network/pricing` — live marketplace per-GPU rates render directly in snapshot: B300 spot $5.81 / on-demand $9.16; H200 $5.90; B200 spot $5.34; H100 $2.64; A100 $1.48; RTX PRO 6000 $2.39. GB300/GB200 racks and R100 are reserve-only. Useful cross-check against RunPod/Vast for the 288GB tier.

## Step 4 — Cost math
- 1 week = 168h, 1 day = 24h, 1 month ≈ 720h
- Total = per-GPU $/hr × GPU count × hours; add disk (~$0.005/hr) + bandwidth ($/TB usage-based)
- Vast on-demand typically 15-40% below RunPod for the same GPU
- Advise: rent hourly to verify deployment first, then commit to weekly/reserved once confirmed

## Pitfalls
- China-based user: HF weight downloads need a proxy or `HF_ENDPOINT=https://hf-mirror.com`
- **Mirror speed (tested 2026-08): hf-mirror.com is ~2MB/s per connection (often slower, drops with exit 18). ModelScope resolve URLs are ~20-40x faster (~39MB/s) for Chinese model families (Qwen, ZhipuAI etc).** Always try ModelScope FIRST for CN-hosted orgs:
  - URL shape: `https://modelscope.cn/models/<org>/<repo>/resolve/master/<file>` — needs `-H "User-Agent: Mozilla/5.0"`, supports `--range`/`-C -` resume, redirects to a CDN (HEAD may show 200 with no content-length)
  - Repo existence probe: `curl -sL -o /dev/null -w '%{http_code}' "https://modelscope.cn/models/<org>/<repo>/resolve/master/README.md" -H "User-Agent: Mozilla/5.0"` (404 = wrong repo name)
  - File list API: `https://modelscope.cn/api/v1/models/<org>/<repo>/repo/files?Revision=master&Root=` → JSON `Data.Files[].Name/Size`
  - ModelScope often ships raw safetensors (not GGUF) for non-Qwen orgs — check file list before committing to a download
  - When a big GGUF must come from HF, use `curl -sL -C -` inside a retry loop (hf-mirror drops connections with exit 18; `-C -` resumes seamlessly)
- **VERIFY total params from config.json before recommending a model for VRAM — model NAME is not the size.** GLM-4.5-Air sounds small ("Air") but is 110B MoE: Q4 ≈ 60GB+, far beyond 16GB. GLM-4-9B (9B, Q4 ≈ 5.8GB) is the right pick for <16GB. Always confirm: `curl https://huggingface.co/<id>/raw/main/config.json` → check `num_hidden_layers`/`hidden_size` (or MoE expert fields) — never trust the marketing name or the "activated params" figure (MoE = FULL weights in memory)
- aria2c on Windows: 16 threads (`-x 16`) gets blocked by Windows firewall ("socket in a way forbidden by its access permissions"); `-x 4` works. Prefer curl `-C -` resume loops over aria2 for flaky mirrors
- Brand-new architectures need latest vLLM/SGLang + `--trust-remote-code` (stock transformers won't have them)
- Missing Jinja chat template → repo provides an `encoding/` python helper; vLLM `--tokenizer-mode <model>` may handle it natively
- CUDA version is a hard gate — verify the instance's Max CUDA BEFORE renting

## Reference
- `references/deepseek-v4-flash-0731.md` — full worked assessment of DeepSeek-V4-Flash-0731 (arch, weights, official launch commands, live rental findings)
- `references/b300-gb300-specs.md` — verified B300/GB300 Blackwell Ultra spec bank (SXM AC/DC SKUs, DGX B300 8-card module, NVL4 tray, NVL72 rack, DGX Spark cluster, power/cooling/weight, rack power-ceiling math, RunPod + Spheron prices)
- `scripts/hf_model_sizing.sh` — one-shot HF model footprint probe (meta + config + total weight size)
