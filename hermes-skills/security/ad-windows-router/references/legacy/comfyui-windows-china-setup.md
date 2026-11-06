<!-- archived from /root/.hermes/skills/security/comfyui-windows-china-setup/SKILL.md on 2026-10-21 -->

---
name: comfyui-windows-china-setup
description: >-
  测绘引擎·Use when installing/running ComfyUI on Windows in China.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/comfyui-windows-china-setup`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/comfyui-windows-china-setup/…')`，不要相对 `references/legacy/` 解析。

# comfyui-windows-china-setup（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/comfyui-windows-china-setup/`

溯源（仅标记）：`hermes/creative`

---

# ComfyUI Local Setup — Windows + China network

Environment: RTX 5080 16GB (CUDA driver 13.1 → cu130), uv available, python 3.11, D drive has ~614GB free. **User wants big installs on D drive, NOT C.** User may abort slow downloads — keep downloads fast via mirrors and show progress early.

## Install (commands that worked)

1. `uv tool install comfy-cli` (no pipx needed). comfy lands in `~/.local/bin`.
2. `comfy --workspace "D:\\ComfyUI" --skip-prompt install --nvidia --fast-deps`
   - **`--workspace` is a GLOBAL flag — it MUST come BEFORE `install`.** `comfy install --workspace ...` fails with "No such option: --workspace".
3. China speed env vars (prefix before the command):
   ```
   export UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
   export UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cu128"  # comfy auto-detects cu130
   export HTTP_PROXY="http://127.0.0.1:10808"; export HTTPS_PROXY="http://127.0.0.1:10808"
   ```
   Small packages fly off Tsinghua; the **1.8GB torch wheel is the bottleneck**.
4. Re-run after an interruption: add **`--restore`** (plain re-run says "ComfyUI is already installed at the specified path... add the '--restore' option"). uv cache means small packages are NOT re-downloaded — only torch re-fetches.
5. Verify: `curl -s http://127.0.0.1:8188/system_stats`.

## Model download (China)

- HF direct is blocked; **hf-mirror.com works** (~4s response). Set `HF_ENDPOINT=https://hf-mirror.com` or use `comfy model download --url <hf-mirror URL> --relative-path models/checkpoints`.
- SDXL base ~6.5GB (5080: seconds/image — user's pick); Flux Dev fp8 ~12GB (30-60s). User chose **SDXL only**; Flux can be added later with one command.
- Chinese text on posters: neither renders Chinese reliably — overlay real text layers in PS/稿定 instead.

## Full uninstall / cleanup ("delete everything")

```bash
rm -rf /d/ComfyUI                      # workspace
uv tool uninstall comfy-cli            # removes comfy, comfy-cli, comfycli
rm -rf ~/AppData/Local/uv/cache && mkdir -p ~/AppData/Local/uv/cache   # torch cache ~5.7GB
```
- After a killed download, `du -sh cache` may still show GBs — hidden `.tmpXXXXXX` dirs survive; wipe the whole cache dir.

## Pitfalls

- `--workspace` position (global, before subcommand); `--restore` on re-run.
- git-bash: `dd` may fail for test files; use `fsutil file createnew`.
- Kill of the install process (exit -15) mid-torch is common on long downloads — resume via `--restore` rather than restarting from scratch.
- Overlaps with the hub-installed `comfyui` skill (general install/API/workflows); this skill adds China-mirror + Windows + user-specific (D-drive, abort-sensitivity) specifics. Session history: install aborted by user after torch stall; full cleanup done — next attempt should go straight to mirrors.
