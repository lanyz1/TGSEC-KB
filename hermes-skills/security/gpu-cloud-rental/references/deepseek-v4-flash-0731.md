# DeepSeek-V4-Flash-0731 deployment (worked example, verified 2026-08-01)

HF: deepseek-ai/DeepSeek-V4-Flash-0731 · MIT license · arxiv 2606.19348 · transformers tag "deepseek_v4"

## Architecture (from config.json)
- DeepseekV4ForCausalLM, 43 layers (3 hash layers), hidden 4096, 64 heads, head_dim 512
- MoE: 256 routed experts, 6 active/token, 1 shared, expert dtype **FP4**
- Weights: **FP8** (e4m3, block 128×128) + FP4 experts — released pre-quantized
- Context: 1,048,576 tokens (YaRN 16× from 65536)
- DSpark speculative decoding module attached (3 MTP layers in same checkpoint, config keys `dspark_*`)
- Total weights: **166.9 GB** (48 safetensors, ~3.57GB each)

## Hardware (official + recipe)
- DeepSeek README: single **4×GB300** node (GB300 NVL4 tray = 4×288GB = 1152GB)
- vLLM recipe: "Fills a **GB200 NVL4 tray** exactly" (4×192GB = 768GB); also DGX Station GB300 single card (252GB, TP1) and AMD MI325X 256GB single card (TP1 eager) validated
- Practical tiers:
  - A (full): 4×GB300/B300 (~$40/hr RunPod, week ≈ $6,700)
  - B (recommended): **4×H200 141GB (564GB total)** — 167GB weights + ~400GB headroom; week ≈ $2,500-4,000 by channel
  - C (cheap): single H200 / 2×H100 with full FP4 quantization (~85GB) via SGLang `flashinfer_mxfp4`

## Software requirements (hard)
- CUDA ≥ 12.8 (Blackwell) / 12.4 (A100/H100)
- **vLLM ≥ 0.25.0** (DSpark landed 0.25.0; ROCm/MI325X support in 0.26.0) or SGLang with `--speculative-algorithm DSPARK`
- `--trust-remote-code` required; `--tokenizer-mode deepseek_v4 --tool-call-parser deepseek_v4` for OpenAI-compatible tool calling
- No Jinja chat template — repo ships `encoding/encoding_dsv4.py` (encode_messages / parse_message_from_completion_text); effort levels low/high/max via reasoning_effort
- Sampling: temperature 1.0, top_p 0.95 (agentic) / 1.0; allow up to 384K output tokens for high/max effort (`--max-model-len ≥ 393216`)

## vLLM launch (official)
```bash
vllm serve deepseek-ai/DeepSeek-V4-Flash-0731 \
  --trust-remote-code --kv-cache-dtype fp8 --block-size 256 \
  --data-parallel-size 4 --enable-expert-parallel \
  --moe-backend deep_gemm_mega_moe \
  --attention-config '{"use_fp4_indexer_cache": true}' \
  --speculative-config '{"method":"dspark","num_speculative_tokens":7,"draft_sample_method":"greedy"}'
```

## Prices checked 2026-08-01
- RunPod serverless: H200 $5.93/hr · B200 $8.64/hr · B300 $9.98/hr
- RunPod cluster: H200 SXM $4.31/hr
- Vast.ai live offer: 4×H200 France (verified, 99.0% rel, **Max CUDA 12.8**, XEON 8568Y+, 96/192 CPU, 1032/2064 GB RAM, 3.84TB NVMe, 7.9 Gbps) **$14.742/hr** → week ≈ $2,477 (¥17.8k)
- Week estimates: B300 4× ≈ $6,700 · B200 4× ≈ $5,700 · H200 4× ≈ $2,500-4,000
- Europe H200 spot (2026-08-01): Italy 8×H200 (host:259870, 99.905%) · France 4×H200 (datacenter:131937, 99.0%) · Czechia 1×H200 NVL (datacenter:214845) — **no Germany offers that day**; H200 spot is scarce and region-rotating, so if the user insists on a country, set expectations that it may simply not exist today.

## China notes
- Weights download: `export HF_ENDPOINT=https://hf-mirror.com` (or proxy 127.0.0.1:10808)
- User tutorial doc written to Desktop: `Vast.ai租用4xH200教程.md` (registration→rent→SSH walkthrough)
