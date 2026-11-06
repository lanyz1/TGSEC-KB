---
name: local-diffusion-setup
description: >-
  测绘引擎·Use when installing ComfyUI/SD/Flux locally on Windows.
owned: true
tier: general
pack: survey-skill
---

# local-diffusion-setup（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/local-diffusion-setup/`

溯源（仅标记）：`hermes/creative`

---

# Local Diffusion Setup (ComfyUI / SD / Flux on this Windows box)

## When to use
- User asks for local unrestricted AI image generation ("有没有随意生成ai图片的模型"), ComfyUI install, SDXL/Flux model setup, or wants me to "生成XXX" via local models.
- Local open-source models = no content review, unlimited, free. Poster text tip: Chinese renders poorly in SD/Flux — generate background, overlay real text via PS/稿定 (avoid 乱码).

## User constraints (non-negotiable)
1. **Big software/models go to D drive, never C.** User correction 2026-08: "别装c盘，装到d盘去".
2. **Minimal downloads.** When asked how many models: pick ONE by default (SDXL: seconds/image on 5080, best plugin ecosystem; Flux Dev fp8 12G is the optional upgrade). User: "选一个就行".
3. Multi-step installs: plan first, show progress + time estimates, no silent downloads (user standing rules).
4. Ask before killing processes; confirm destructive ops (delete installs) even when user seems annoyed.

## Verified environment (2026-08)
- GPU: NVIDIA RTX 5080 16GB VRAM (`nvidia-smi`), CUDA driver 13.x; AMD iGPU also present
- uv at `C:\Users\Administrator\AppData\Local\hermes\bin\uv`; Python 3.11 (`python`); D drive ~614G free
- comfy-cli installs to `~/.local/bin` which is NOT on PATH → `export PATH="$HOME/.local/bin:$PATH"` in every shell call after `uv tool install comfy-cli`
- Network: HuggingFace direct BLOCKED; hf-mirror.com reachable (~4s); proxy at 127.0.0.1:10808 (http + socks5)

## Install procedure (verified sequence)
1. Env check:
   ```bash
   nvidia-smi --query-gpu=name,memory.total --format=csv
   df -h /d
   curl -s -m 3 http://127.0.0.1:8188/system_stats   # port 8188 must be free
   ```
2. `uv tool install comfy-cli` → export PATH (above) → `comfy --version`
3. Install:
   ```bash
   comfy --workspace "D:\\ComfyUI" --skip-prompt install --nvidia --fast-deps
   ```
   ⚠️ **`--workspace` is a GLOBAL comfy option — goes BEFORE `install`.** Placed after → `Error: No such option: --workspace` (real failure this session).
   ⚠️ Interrupted install → re-run with `--restore` appended (output: "ComfyUI is already installed ... add the '--restore' option").
4. China network env for the install command:
   ```bash
   export UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
   export UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cuXXX"  # MUST match comfy's detected CUDA
   export HTTP_PROXY="http://127.0.0.1:10808" HTTPS_PROXY="http://127.0.0.1:10808" ALL_PROXY="socks5://127.0.0.1:10808"
   ```
   → Tsinghua mirror makes ALL small packages download instantly; torch (~1.8GiB) is the bottleneck. comfy auto-selects CUDA ("Detected CUDA driver version: X → using cuXXX") — do NOT fight it with a mismatched UV_EXTRA_INDEX_URL.
5. Models via hf-mirror (HF direct is blocked):
   ```bash
   comfy model download \
     --url "https://hf-mirror.com/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" \
     --relative-path models/checkpoints
   # Flux Dev fp8: https://hf-mirror.com/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors (~12G)
   ```
6. Launch & verify: `comfy launch --background` → `curl http://127.0.0.1:8188/system_stats` → smoke-test image.

## Troubleshooting
- **torch download killed mid-flight (exit -15, completion_reason killed)** happened twice on ~1.8GiB torch. Don't assume stuck: check growth via
  `find /c/Users/Administrator/AppData/Local/uv/cache -mmin -5 -size +500M` (partial downloads live in `uv/cache/.tmp*`). Restart with `--restore`; uv cache resumes.
- uv cache grows to ~5.7G during install (mostly torch) — normal, not a leak.

## Cleanup / rollback (user asked for this once — keep it fast)
```bash
uv tool uninstall comfy-cli
rm -rf /d/ComfyUI
rm -rf /c/Users/Administrator/AppData/Local/uv/cache && mkdir -p /c/Users/Administrator/AppData/Local/uv/cache
```

## Pitfalls
- `--workspace` placement (global vs subcommand) — see step 3.
- `--restore` required when program dir exists but deps incomplete.
- Running install with `--fast-deps` twice in parallel / repeated `process wait` on long installs risks kill — use `notify_on_complete` once and let it run.
- Chinese text in SD/Flux outputs 乱码 — always overlay text as a separate layer.
