# DeepSeek-V4-Flash-0731 — deployment assessment (2026-08-01)

HF: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731 — MIT license.
Official vLLM recipe: https://recipes.vllm.ai/deepseek-ai/DeepSeek-V4-Flash

## Architecture (from config.json / inference/config.json)
- `DeepseekV4ForCausalLM`, 43 layers (3 hash layers), hidden_size 4096, 64 heads, head_dim 512
- MoE: 256 routed + 1 shared expert, 6 active per token, moe_intermediate_size 2048
- Context: 1,048,576 (1M) tokens via YaRN ×16 from 65536; sliding window 128
- Quantization: FP8 weights (e4m3, ue8m0 scales, 128×128 block) + **FP4 experts**
- DSpark speculative decoding module (3 MTP layers) fused into the checkpoint
- Total weights: **166.9 GB** across 48 safetensors (~3.57 GB each); preview was ~160 GB
- No Jinja chat template — repo ships `encoding/encoding_dsv4.py` (encode_messages / parse_message_from_completion_text); vLLM `--tokenizer-mode deepseek_v4` handles it natively

## Hard requirements
- CUDA ≥ 12.8 (Blackwell) / ≥ 12.4 (A100/H100); vLLM ≥ 0.25.0 (DSpark drafting landed 0.25.0, ROCm support in 0.26.0)
- Always `--trust-remote-code`; sampling temp=1.0, top_p=0.95 agentic / 1.0 otherwise
- Reasoning efforts: low / high / max; `max` needs `--max-model-len ≥ 393216` (384K tokens)

## Official launch commands
vLLM (single 4×GB300 node):
```
vllm serve deepseek-ai/DeepSeek-V4-Flash-0731 --trust-remote-code --kv-cache-dtype fp8 \
  --block-size 256 --data-parallel-size 4 --enable-expert-parallel \
  --moe-backend deep_gemm_mega_moe \
  --attention-config '{"use_fp4_indexer_cache": true}' \
  --speculative-config '{"method":"dspark","num_speculative_tokens":7,"draft_sample_method":"greedy"}'
```
SGLang:
```
sglang serve --trust-remote-code --model-path deepseek-ai/DeepSeek-V4-Flash-0731 --tp 4 \
  --moe-runner-backend flashinfer_mxfp4 --speculative-algorithm DSPARK \
  --mem-fraction-static 0.90 --chunked-prefill-size 4096 --swa-full-tokens-ratio 0.1
```

## Hardware tiers (from vLLM recipe hardware defs)
- A: 4×GB300 NVL4 tray (288 GB HBM3e ×4 = 1152 GB) — official README example
- B: GB200 NVL4 (192 GB ×4 = 768 GB) — recipe: "fills a GB200 NVL4 tray exactly"; also 4-of-8 GPUs on H200/B200/B300 nodes; DP4+EP
- C: single GPU — DGX Station GB300 (252 GB) or AMD MI325X 256 GB run it at TP1 (slow)
- FP4 re-quant (SGLang variant) ≈ 85 GB → fits single H200 (141 GB) / 2×H100

## Live rental findings (2026-08-01, Vast.ai + RunPod)
- **Vast.ai instance #45379679**: 4×H200 140 GB, France, verified, 99.0% reliability, XEON Platinum 8568Y+ (96/192 cores), 1032/2064 GB RAM, Dell 3.84 TB NVMe (9053 MB/s), ~2.6 Gbps, Max CUDA 12.8, max duration 29 days → **$14.742/hr** ($14.737 GPU + $0.005 disk) = $353.79/day = **$2,477/week** (¥17.8k @ 7.2)
- RunPod serverless $/GPU-hr: B300 $9.98, B200 $8.64, H200 $5.93, H100 $4.55; RunPod Cluster: H200 SXM $4.31
- Rule of thumb: Vast on-demand 15-40% cheaper than RunPod for the same GPU
