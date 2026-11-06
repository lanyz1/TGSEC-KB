#!/usr/bin/env bash
# hf_model_sizing.sh — one-shot footprint probe for any HuggingFace model.
# Usage: hf_model_sizing.sh <hf-model-id>   (e.g. deepseek-ai/DeepSeek-V4-Flash-0731)
# Outputs: license/quantization tags, architecture config, and TOTAL weight size (GB)
# = the disk/VRAM floor for deployment planning. No download required.
set -euo pipefail
ID="${1:?usage: hf_model_sizing.sh <hf-model-id> e.g. deepseek-ai/DeepSeek-V4-Flash-0731}"
B="${HF_BASE:-https://huggingface.co}"

echo "== meta (tags/license/quant) =="
curl -s --max-time 30 "$B/api/models/$ID" | python3 -c "
import json,sys
d=json.load(sys.stdin)
tags=d.get('tags',[])
print('tags:', ', '.join(tags[:25]))
print('siblings:', len(d.get('siblings',[])))
" || echo "meta fetch failed"

echo "== config.json (architecture) =="
curl -s --max-time 30 "$B/$ID/raw/main/config.json" | python3 -m json.tool | head -70 || echo "config fetch failed"

echo "== weight sizes =="
curl -s --max-time 30 "$B/api/models/$ID/tree/main?recursive=true" | python3 -c "
import json,sys
d=json.load(sys.stdin)
tot=0; big=0
for f in d:
    sz=f.get('size',0) or 0
    tot+=sz
    if sz>100*1024*1024:
        big+=1
print(f'files: {len(d)}, big files (>100MB): {big}')
print(f'TOTAL WEIGHT: {tot/1e9:.1f} GB')
"
