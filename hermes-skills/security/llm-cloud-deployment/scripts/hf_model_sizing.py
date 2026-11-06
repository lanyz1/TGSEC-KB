#!/usr/bin/env python3
"""Probe a HuggingFace model repo and print deployment-sizing info.

Usage: python hf_model_sizing.py <org/model>
Example: python hf_model_sizing.py deepseek-ai/DeepSeek-V4-Flash-0731

Uses only stdlib (urllib). Output: license, weight size (sum of safetensors),
and key architecture fields from config.json / inference/config.json.
"""
import json
import sys
import urllib.request

BASE = "https://huggingface.co"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    model = sys.argv[1]
    api = f"{BASE}/api/models/{model}"
    meta = json.loads(fetch(api))
    print(f"model      : {meta.get('id')}")
    tags = meta.get("tags", [])
    print(f"license    : {[t for t in tags if t.startswith('license:')]}")
    print(f"tags       : {[t for t in tags if not t.startswith('license:')][:12]}")
    print(f"downloads  : {meta.get('downloads')}  likes: {meta.get('likes')}  gated: {meta.get('gated')}")

    try:
        tree = json.loads(fetch(f"{api}/tree/main?recursive=true"))
        tot, n = 0, 0
        for f in tree:
            if f["path"].endswith(".safetensors"):
                tot += f.get("size", 0)
                n += 1
        print(f"weights    : {n} safetensors, {tot/1e9:.1f} GB")
    except Exception as e:
        print(f"weights    : tree API failed: {e}")

    keys = ["architectures", "model_type", "hidden_size", "num_hidden_layers",
            "n_routed_experts", "num_experts_per_tok", "n_activated_experts",
            "max_position_embeddings", "vocab_size", "expert_dtype", "dtype",
            "num_attention_heads", "head_dim", "n_layers", "dim"]
    for cfg_name in ("config.json", "inference/config.json"):
        try:
            cfg = json.loads(fetch(f"{BASE}/{model}/raw/main/{cfg_name}"))
        except Exception:
            continue
        print(f"\n-- {cfg_name} --")
        for k in keys:
            if k in cfg:
                print(f"  {k:24s}: {cfg[k]}")
        q = cfg.get("quantization_config", {})
        if q:
            print(f"  {'quant':24s}: {q.get('quant_method')} fmt={q.get('fmt')} block={q.get('weight_block_size')}")


if __name__ == "__main__":
    main()
