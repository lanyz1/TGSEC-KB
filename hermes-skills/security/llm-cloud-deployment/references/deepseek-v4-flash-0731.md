# DeepSeek-V4-Flash-0731 — self-host sizing case study (2026-08)

Repo: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731 · MIT · 1M context

## Architecture (config.json + inference/config.json)
- DeepseekV4ForCausalLM, 43 layers (3 hash layers), hidden 4096, 64 heads × head_dim 512
- MoE: 256 routed experts, 6 active/token, 1 shared, moe_intermediate 2048, **expert_dtype fp4**
- Context: max_position_embeddings 1,048,576 (YaRN ×16 from 64K), sliding_window 128
- Quant: fp8 weights (e4m3, ue8m0 scales, 128×128 block) + fp4 experts
- DSpark speculative decoding: 3 MTP layers fused (dspark_block_size 5, markov_rank 256, noise_token_id 128799)
- No Jinja chat template → repo ships `encoding/encoding_dsv4.py` (encode_messages / parse_message_from_completion_text); vLLM alternative: `--tokenizer-mode deepseek_v4`
- Weights: 48 safetensors, **166.9 GB** (verify via tree API)

## Official launches (DeepSeek README — single 4×GB300 node)

vLLM (needs vLLM ≥ 0.25.0):
```
vllm serve deepseek-ai/DeepSeek-V4-Flash-0731 \
  --trust-remote-code --kv-cache-dtype fp8 --block-size 256 \
  --data-parallel-size 4 --enable-expert-parallel \
  --moe-backend deep_gemm_mega_moe \
  --attention-config '{"use_fp4_indexer_cache": true}' \
  --speculative-config '{"method":"dspark","num_speculative_tokens":7,"draft_sample_method":"greedy"}'
```

SGLang:
```
sglang serve --trust-remote-code --model-path deepseek-ai/DeepSeek-V4-Flash-0731 \
  --tp 4 --moe-runner-backend flashinfer_mxfp4 \
  --speculative-algorithm DSPARK --mem-fraction-static 0.90 \
  --chunked-prefill-size 4096 --swa-full-tokens-ratio 0.1
```

## vLLM recipe (recipes.vllm.ai/deepseek-ai/DeepSeek-V4-Flash) key facts
- "Recommended deployment: single-node DP + EP with --data-parallel-size 4. **Fills a GB200 NVL4 tray exactly**; uses 4 of 8 GPUs per replica on H200/B200/B300."
- DGX Station single GPU (252GB GB300): TP1 + MTP spec decode (`num_speculative_tokens 3`), `--gpu-memory-utilization 0.92`
- AMD MI325X 1×256GB works (ROCm: `VLLM_ROCM_USE_AITER=1`, vLLM ≥ 0.26.0 for ROCm DSpark; 0.25.0 enough for NVIDIA-only)
- Reasoning effort: low/high/max. Max mode requires `--max-model-len >= 393216` (384K). Rec sampling: temp 1.0, top_p 0.95 (agentic) / 1.0 otherwise.

## Hardware matrix (vLLM recipe preset names)
| preset | hardware | gpu_count | vram |
|---|---|---|---|
| gb300 | GB300 NVL4 tray (288GB HBM3e/GPU) | 4 | 1152 GB |
| gb200 | GB200 NVL4 tray (192GB/GPU) | 4 | 768 GB |
| b300 | HGX B300 SXM (268GB/GPU) | 8 | 2144 GB |
| dgx_station_gb300 | DGX Station 1× GB300 superchip | 1 | 252 GB |

## Cloud rental (RunPod, verified 2026-08-01, serverless $/hr/GPU)
- B300 280GB $9.98 → 4× ≈ $40/hr
- B200 180GB $8.64 → 4× ≈ $34/hr
- H200 140GB $5.93 → 4× ≈ $24/hr
- H100 80GB $4.55 · A100 80GB $2.72 · L40S 48GB $1.75
- Domestic Chinese clouds: NO GB200/GB300/H100-class (export controls) → rent overseas; HF download via proxy or `HF_ENDPOINT=https://hf-mirror.com`
