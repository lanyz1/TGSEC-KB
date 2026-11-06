# Voice Cloning from a Video (CosyVoice2, fully local)

Goal: user provides a video (often a Douyin/TikTok clip of a person talking) and wants the assistant to speak with that person's voice. Pipeline: acquire video → extract clean speech segment → clone with CosyVoice2 → use as persona voice. All synthesis stays local; only the edge-tts bootstrap step (if used) touches the network.

## 1. Acquiring the video (Douyin example)

**yt-dlp needs fresh cookies** — `yt-dlp -x --audio-format wav <douyin-url>` fails with `ERROR: [Douyin] ... Fresh cookies (not necessarily logged in) are needed`. Don't fight it; alternatives in order of success:

1. **Resolve the short link → video ID** (works without cookies):
   ```bash
   curl -sI -x http://127.0.0.1:10808 --max-time 15 "https://v.douyin.com/<code>/" -H "User-Agent: Mozilla/5.0 (iPhone...)" | grep -i location
   # → https://www.iesdouyin.com/share/video/<VIDEO_ID>/?region=CN...
   ```
2. **BEST: ask the user to save the video locally and give you the path.** The Hermes headless browser's blob-download trick (below) "succeeds" in the console but **the file never lands on the user's disk** — user reported "没看到啊,浏览器都没打开" and no file appeared in Downloads/Desktop (Hermes browser runs headless in the background, NOT the user's visible browser). This is the reliable path for a 小白 user: have them use the phone Douyin app (share → 保存本地) and send it to the PC, or open the page in THEIR browser and 右键→视频另存为. Verify the file exists before proceeding.
3. **Headless-browser blob download (may not persist to disk — verify with `find` afterwards, fall back to step 2)**: `browser_navigate` to `https://www.douyin.com/video/<ID>`, then trigger a download of the already-buffered blob from the console:
   ```js
   (()=>{const v=document.querySelector('video');if(!v||!v.currentSrc)return 'no video';
     const a=document.createElement('a');a.href=v.currentSrc;a.download='douyin_video.mp4';
     document.body.appendChild(a);a.click();return 'download triggered: '+v.currentSrc.slice(0,60)})()
   ```
   This uses the in-memory blob URL (`blob:https://www.douyin.com/...`), bypassing the anti-bot fetch that blocks `window.fetch` (douyin's security SDK wraps fetch; direct page-context `fetch()` throws `TypeError: Failed to fetch` from `lf-security.bytegoofy.com`). After triggering, `find ~ -name "douyin_video*" -newermt <date>` — if nothing, switch to step 2.
4. **Do NOT try** the old API `https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids=<ID>` — returns `{"status_code":11110,"status_msg":"encrypt_data_miss"}` (dead endpoint).
5. Browser-console evaluation pitfall: some browser toolchains echo the expression into a shell — if you see `'video' is not recognized as an internal or external command`, the console tool is passing the expression to cmd; fall back to the anchor-click trick above or `performance.getEntriesByType('resource')` filtering for `/video|mp4|playwm/`.

## 2. Extract the voice track

```bash
# strip audio to 16k mono wav for clean analysis
ffmpeg -i douyin_video.mp4 -ar 16000 -ac 1 -vn clean_voice.wav
```

**If BGM/music covers the ENTIRE video (common in vlogs — user said \"背景音乐是覆盖全部视频时长的\"), no time-slice will be clean. You MUST separate stems first** — energy-scanning raw audio just ranks the loudest moments, which are often music, not speech. Use demucs (Meta, local, GPU-accelerated on 5080):

```bash
# install into the SAME venv as everything else, then run with that venv's python
/d/xibei/venv/Scripts/python.exe -m pip install demucs
cd /d/xibei/data/clone
/d/xibei/venv/Scripts/python.exe -m demucs --two-stems=vocals -n htdemucs full.wav -o separated
# → separated/htdemucs/full/vocals.wav (speech only) + no_vocals.wav (music only)
```

- demucs runs in ~25s for 160s audio on a 5080 (first run downloads the htdemucs model).
- After separation, energy-scan **vocals.wav** (2s windows, RMS) to find the cleanest speech spans; pick 10-30s. Present 2-3 candidate segments to the user and let them pick by listening (user preference: numbered files in one folder + legend, not sequential auto-play).
- `ffprobe -show_entries format=duration` on the demucs output to confirm real duration. **A Python-side duration miscalc (e.g. 325.5s vs actual 162.7s) is usually STEREO, not a frame-rate bug**: demucs outputs 44.1kHz STEREO wav; `wave.readframes(n)` returns interleaved `n*channels` samples, so treating them as mono doubles the apparent length and garbles the signal. Convert to mono first (`ffmpeg -i vocals.wav -ac 1 -ar 16000 vocals_mono.wav`) and scan THAT, or divide by `wf.getnchannels()`.
- **BGM residue survives demucs → VAD/silencedetect is useless on separated vocals.** ffmpeg `silencedetect` on vocals.wav found silence only at the very start; the rest stayed "loud" from music bleed. Use an energy-threshold scan (50ms RMS windows, speech = energy > max(median*1.2, 0.015), gaps >0.6s split segments, keep ≥6s spans) instead. Optional extra cleaning before scanning: `ffmpeg -af "afftdn=nf=-25"` — but it also weakens speech, so lower the threshold after denoising (e.g. med*1.2 vs *1.8). Present top candidates (longest spans first) as numbered files for the user to pick by ear.
- Cut the winning span: `ffmpeg -y -v error -ss <start> -t <dur> -i separated/htdemucs/full/vocals.wav -ar 16000 -ac 1 speech.wav`

Find a 10-30s segment where ONLY the target person speaks (no music/BGM, no other voices) — that becomes the reference. If the track is noisy, cut with ffmpeg `-ss <start> -t <dur>` around the cleanest spoken part.

## 3. Clone with CosyVoice2 (zero-shot, local)

- CosyVoice2 (Alibaba FunAudioLLM, ~2GB model, ModelScope) does zero-shot voice cloning from a short reference clip. ModelScope is CN-friendly: `modelscope.cn/models/iic/CosyVoice2-0.5B`.
- **Setup: `pip install cosyvoice` gives only an API SHELL** (`api.py`, `server.py`) with no inference code. You need the official repo for the real thing:
  ```bash
  git clone --depth 1 https://github.com/FunAudioLLM/CosyVoice.git
  cd CosyVoice
  git submodule update --init --recursive   # REQUIRED — shallow clone leaves third_party/Matcha-TTS EMPTY
  /d/xibei/venv/Scripts/python.exe -m pip install -r requirements.txt   # torch + torchaudio etc, large
  ```
  **`third_party/Matcha-TTS` is a git submodule and `git clone --depth 1` leaves the directory EMPTY** — without it you get `pydoc.ErrorDuringImport: problem in cosyvoice.flow.flow_matching - ModuleNotFoundError: No module named 'matcha'` when the model loads (hyperpyyaml `pydoc.locate` resolves the yaml's class references at load time, so the failure appears during `AutoModel(model_dir=...)`, not at `import`). Fix: `git submodule update --init --recursive` (verified: checks out commit dd9105b...). **Do NOT `pip install -e .` the Matcha-TTS submodule on Windows/py3.12** — its setup.py runs `cythonize()` which fails to build; the source is importable directly via `sys.path.append(third_party/Matcha-TTS)` (the repo's example.py does exactly this) and that is all inference needs.
  Then use `AutoModel(model_dir='pretrained_models/CosyVoice2-0.5B')` + `inference_zero_shot(text, prompt_text, prompt_wav, stream=False)` (see `example.py` in the repo). Save via `torchaudio.save(path, out['tts_speech'], cosyvoice.sample_rate)`. Remember `sys.path` must include the CosyVoice repo root AND `third_party/Matcha-TTS`.
- **Model download: use the Python API, NOT the CLI.** `python -m modelscope download --model iic/CosyVoice2-0.5B` fails with `No module named modelscope.__main__; 'modelscope' is a package` on older modelscope. Working form:
  ```python
  from modelscope.hub.snapshot_download import snapshot_download
  snapshot_download('iic/CosyVoice2-0.5B', local_dir=r'D:\xibei\data\clone\CosyVoice2-0.5B')
  ```
  (Or `pip install -U modelscope` to get the CLI.) Model dir must be the local_dir path, and AutoModel expects the model files directly under it.
- **VENV PATH TRAP (this user's machine): bare `python` resolves to Hermes's OWN venv** (`C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`), while `pip` may install into `D:\xibei\venv` — `python -m demucs` then fails with `No module named demucs` even though `import demucs` works. Always run heavy tools via the full venv path: `/d/xibei/venv/Scripts/python.exe -m <tool>`. Check `python -c "import sys; print(sys.executable)"` before debugging module-not-found ghosts.
- **PYTHONPATH POLLUTION — the night-killer for this exact pipeline.** This machine has an OS-level `PYTHONPATH` pointing at Hermes's venv site-packages, so even a freshly created independent venv imports packages from HERMES's site-packages (`venv_clone/Scripts/python.exe` reported `D:\xibei\venv_clone\Lib\site-packages` in `site.getsitepackages()` but `import tokenizers` still loaded `C:\...\hermes-agent\venv\Lib\site-packages\tokenizers`). Consequence: transformers demands `tokenizers>=0.22,<=0.23.0`, Hermes's env has 0.23.1, and no pip reinstall inside the venv fixes it because imports never use the venv. **Every CosyVoice/demucs command must run with the env cleared**: `set PYTHONPATH=& set PYTHONHOME=` in .bat, or `env -u PYTHONPATH -u PYTHONHOME <venv>/Scripts/python.exe ...` in bash. Verify after: `python -c "import tokenizers; print(tokenizers.__file__)"` must show the venv path.
- **CosyVoice deps version-lock**: requirements.txt alone is not enough on this box — install `torch torchaudio transformers tokenizers==0.23.0 hyperpyyaml onnxruntime modelscope` together. `tokenizers` MUST be pinned ≤0.23.0 or transformers refuses to import (`ImportError: tokenizers>=0.22.0,<=0.23.0 is required... found tokenizers==0.23.1`). `--force-reinstall --no-deps` may silently keep the old version if the wrong env is active — see PYTHONPATH trap above; clear env first, then pin.
- **A clean venv created from system Python may lack pip** (`No module named pip` after `-m venv` — ensurepip failed with Permission denied during creation). Fix: `<venv>/Scripts/python.exe -m ensurepip --upgrade` before installing anything. System Python on this box: `C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python312\\python.exe`; use full Windows paths when creating the venv (git-bash `/d/xibei` gets mangled to `D:\\d\\xibei`).
- **`pip install torch` may hang indefinitely (CPU ~0, no cache growth) even from CN mirrors — don't fight it; curl the wheel directly.** On this box `pip install torch` sat at CPU 0.015 with site-packages frozen for 5+ minutes, and `pip download torch` timed out at 300s, while tiny packages (pyyaml) installed instantly. Diagnosed via `curl` against `pypi.tuna.tsinghua.edu.cn/simple/torch/` (returns 200 with the full wheel list) — the mirror had `torch-2.11.0-cp312-cp312-win_amd64.whl`; the hang was pip's metadata/dependency resolution (likely reaching for blocked pypi.org). **Fix: resolve the wheel URL yourself and curl it** (works, ~2.4MB/s; aria2c also completes it with `-c -x 16`), then `pip install --no-index --no-deps <wheel>.whl` from the local file, then `pip install` the remaining deps normally.
- **Do NOT assume torch's wheel size — verify what you actually downloaded.** The cp312 win_amd64 CPU wheel for torch 2.11.0 is only **~114MB compressed / ~408MB unpacked (12,403 files)** — NOT the 2.5-3GB you'd guess from Linux builds. A 114MB file is COMPLETE; the "it must still be downloading" assumption caused repeated false restarts. Verify completeness with Python: `zipfile.ZipFile(path).testzip()` → None means OK, plus count files. curl exiting 0 with a smaller-than-guessed file is not a failure.
- **pip 25 `--progress-bar` only accepts `on|off|raw`** — `--progress-bar pretty` fails with `invalid choice: 'pretty'`. Use `--progress-bar on` in .bats that promise a progress bar.
- **uv is NOT a reliable escape hatch on this box.** `uv venv` creates fine and fast, but `uv pip install` of torch also hung (CPU ~0, site-packages stayed 9KB). Don't burn time switching package managers when the root cause is pip's metadata resolution — go straight to curl-the-wheel + `--no-index --no-deps`.
- **CPU torch "import hangs" — usually a RED HERRING; check numpy FIRST.** Symptom: `import torch` runs >3-6 min with CPU ~0, faulthandler silent, no error. **Root cause on this box: `numpy` was NOT installed** — torch's import path initializes numpy inside `torch/_subclasses/functional_tensor.py` and hangs/fails with only a buried warning (`UserWarning: Failed to initialize NumPy: No module named 'numpy'`). Fix: `pip install numpy` (tiny, instant), then `import torch` succeeds in <60s even on CPU (`torch 2.11.0+cpu`, EXIT=0). **Do NOT burn hours (or a 2.8GB GPU-wheel download) on "CPU torch is broken" before verifying numpy.** The numpy warning appears only on stderr with `-X faulthandler`; a plain run looks like a silent hang.
- **CosyVoice deps are scattered — auto-loop, do NOT trust requirements.txt.** `pip install -r requirements.txt` fails on py3.12 because it pins old builds (grpcio==1.57.0, conformer==0.3.2, diffusers==0.29.0) that fail to compile. Instead run an import→catch→install loop that keeps importing `AutoModel`, extracts each `ModuleNotFoundError: No module named 'X'`, pip-installs X, retries — this session needed `omegaconf`, `scipy`, then `conformer`, then `diffusers` after the visible ones (`openai-whisper`, `inflect`). Reusable script: `scripts/fix_cosy_deps.py`. Order matters: transformers must be present before frontend.py's `import whisper` is reached, and each round only surfaces the NEXT missing module. The pure-Python deps can be bulk-installed in one go (`diffusers fastapi gdown gradio hydra-core librosa lightning matplotlib networkx onnx pydantic pyarrow rich pyworld`) — only the C-extension pins (grpcio, pyworld, conformer-build) fail, and those aren't needed for inference.
- **pip batch installs ROLL BACK on one bad pin** — nothing in the batch gets installed. `pip install numpy torchaudio transformers tokenizers==0.23.0 ...` failed with `No matching distribution found for tokenizers==0.23.0` and NONE of numpy/torchaudio/transformers landed (numpy import still failed afterwards). Install in small batches WITHOUT likely-to-fail pins, or let transformers pick its own compatible tokenizers: `transformers 5.14.1` accepts `tokenizers 0.22.2` (what tsinghua actually has — 0.23.0 is NOT on the mirror, only 0.23.1/0.22.x). Prefer unpinned `transformers` + whatever tokenizers it resolves, instead of the old pin-to-0.23.0 advice.
- **Verify a "completed" download with `zipfile.testzip()`, not file size.** aria2 reported `(OK): download completed` yet the cu128 wheel was corrupt (`.aria2` control file still present + `zipfile` → `Error -3 while decompressing`). A `torch-cu128-*.whl` at 2626MB was NOT complete; only re-downloading with `--max-tries=0 --retry-wait=3 --connect-timeout=15` (infinite retry for the flaky download-r2 CDN) and then passing `testzip()` confirmed it. Also `curl -sL` can exit 0 with a truncated file — always `testzip()` a wheel before `pip install`/unzip.
- **GPU torch (cu128) for the 5080: prefer the ALIYUN pytorch-wheels mirror over download-r2.** `download-r2.pytorch.org` is reachable but its CDN drops long transfers from CN: aria2 finished with `(ERR)` and a CORRUPT 2626MB file (`zipfile.testzip()` → `Error -3`), even with `--max-tries=0 --retry-wait=3`. The reliable CN path is **`https://mirrors.aliyun.com/pytorch-wheels/cu128/` — direct wheel URL works, HTTP 200, Content-Length 2753189216 (2.75GB)**, e.g.:
  ```bash
  aria2c -c -x 16 -s 16 -k 1M --file-allocation=none -o torch-cu128-2.11.0-cp312-win.whl \
    "https://mirrors.aliyun.com/pytorch-wheels/cu128/torch-2.11.0%2Bcu128-cp312-cp312-win_amd64.whl"
  ```
  Probe the mirror index with `curl -s "https://mirrors.aliyun.com/pytorch-wheels/cu128/"` (it's plain HTML; note the `&#43;` HTML entity stands for `+` in the filename — decode it when building the URL). Always `zipfile.testzip()` after any multi-GB download. Scraping note: tsinghua/aliyun *PyPI* simple-index pages either lack cp312 win_amd64 wheels or are dynamically rendered — the dedicated `pytorch-wheels` mirror is the one that has them.
- **Manual wheel install = unzip to site-packages, works when pip install hangs.** A .whl is a zip with the package layout at the top level: `python -c "import zipfile; zipfile.ZipFile('x.whl').extractall(site_packages_dir)"` installs it (verified for torch: 12,403 files → torch/, functorch/, torchgen/). Use `--no-index --no-deps` pip install on the local wheel as the first choice (it avoids network metadata resolution), and the unzip route only when pip itself hangs even on a local file. Verify with `import torch`.
- **`pip install --python <path>` flag position trap**: pip 25 requires `--python` BEFORE the subcommand (`python -m pip --python <path> install ...`), not after — `pip install --python ...` errors `The --python option must be placed before the pip subcommand name`. This silently aborted a command that then looked like a hang.
- **A venv created FROM another venv (e.g. from Hermes's venv) is a trap**: `pyvenv.cfg` points `home`/`executable` at the parent, and even with full paths the child imports the parent's site-packages. Prefer a venv from real system Python (`C:\\\\Users\\\\Administrator\\\\AppData\\\\Local\\\\Programs\\\\Python\\\\Python312\\\\python.exe -m venv <dir>`). If one already exists and misbehaves, create a fresh one from system Python rather than repairing it.
- **CPU-only crash at clone time: `RuntimeError: mat1 and mat2 must have the same dtype, but got Float and BFloat16` (followed by `Calculated padded input size per channel: (2). Kernel size: (3)` from a conv1d).** CosyVoice2's checkpoints are saved in bf16; on CPU there is no autocast to reconcile bf16 weights with fp32 inputs, so the LLM/flow forward pass dies. **Fix (verified, one place): in `cosyvoice/cli/model.py` `CosyVoiceModel.load()`, after the three `load_state_dict` calls, force fp32 when on CPU**:
  ```python
  if self.device.type == 'cpu':
      self.llm = self.llm.float()
      self.flow = self.flow.float()
      self.hift = self.hift.float()
  ```
  (then `.to(device).eval()` as before). The two `torch.cuda.amp.autocast` FutureWarnings in model.py are harmless noise on CPU.
- **CPU synthesis WORKS after the fp32 patch, but quality is noticeably poor — 杂音/破音/语调怪 — and a human listener will reject it.** Verified: full zero-shot clone ran end-to-end on CPU torch (`yield speech len 22.4, rtf 2.74`), produced valid WAVs, but the user's verdict was 杂音/破音/语调怪. Source audio was clean (RMS 0.2, zero clipping, no high-freq residue — checked via peak/clip-ratio diagnostics), so the degradation is CPU synthesis itself (HIFIGAN vocoder quality loss), NOT the reference. **Plan for a GPU torch install before promising usable quality; use CPU runs only to validate the pipeline.** Bonus guard in the save function: normalize peak to 0.9 before writing int16 (`data = data/peak*0.9`) to avoid clip-induced 破音.
- **torchaudio 2.11 REQUIRES torchcodec — CosyVoice's `load_wav` crashes without it; patch it to stdlib instead of installing torchcodec.** Symptom at clone time (not import time): `ImportError: TorchCodec is required for load_with_torchcodec. Please install torchcodec` from `cosyvoice/utils/file_utils.py:45` → `torchaudio.load(wav, backend='soundfile')`. Newer torchaudio ignores the `backend=` arg and routes through torchcodec; `pip install torchcodec` then fails to load its DLL on boxes without matching FFmpeg libs (`Could not load libtorchcodec_core4.dll`), and even uninstalling it leaves torchaudio 2.11 forcing the torchcodec path. **Proven fix: patch `load_wav` in `cosyvoice/utils/file_utils.py` to read WAV with stdlib `wave` + numpy and resample with `torch.nn.functional.interpolate(scale_factor=target_sr/sample_rate, mode='linear', align_corners=False)`** (returns `[1, T]` float tensor like torchaudio did). Also patch the clone script's save: CosyVoice itself never calls `torchaudio.save` — only your own `run_clone.py` does, so replace it with a stdlib `wave` writer (clip to [-1,1], `(x*32767).astype(np.int16)`, 16-bit mono). Verified: with these two patches the full zero-shot clone runs to completion on CPU torch.
- **Scattered deps keep surfacing at MODEL-LOAD time, after `import AutoModel` succeeds.** The import-loop (`fix_cosy_deps.py`) gets `AutoModel` importing cleanly, then `AutoModel(model_dir=...)` throws `pydoc.ErrorDuringImport: problem in cosyvoice.flow.flow_matching - ModuleNotFoundError: No module named 'wget'` (hyperpyyaml's `pydoc.locate` resolves yaml class refs lazily at load). **The dependency loop MUST also wrap the model-load call, and must catch broad `Exception` (not just bare `ModuleNotFoundError`) and regex-extract `No module named 'X'` from the message** — `pydoc.ErrorDuringImport` wraps the real error in its string. Final dep list observed across import+load: `openai-whisper`, `inflect`, `omegaconf`, `scipy`, `conformer`, `diffusers`, `wget`. Model-load verification snippet: `cosyvoice = AutoModel(model_dir=...)` prints `Loading weights: 100%|...| 290/290` + `模型加载成功!` when fully green.
- Reference requirements: 5-30s of clean single-speaker speech; more clean audio = better similarity. One short clip is enough for stable cloning; 3+ varied clips (different sentences) improve it.
- GPU: RTX 5080 16GB runs 0.5B CosyVoice2 comfortably.
- Workflow: load model → `CosyVoice2` zero-shot API with `prompt_audio_path=<reference.wav>` + new text → returns synthesized speech → save wav → play via ffplay.
- Swap TTS backend in the assistant from `edge` to `cosyvoice` (the `TTSEngine` already has a `cosyvoice` branch — see main SKILL.md; keep edge-tts as fallback).

## 4. Privacy note

CosyVoice2 is fully local — cloning, synthesis, and playback never leave the machine. The only cloud touch-point in the whole pipeline is the optional edge-tts bootstrap (generating a *different* reference voice) or downloading the model; neither uploads the user's target voice. This satisfies "数据不出电脑".

## Pitfalls

- Streaming ASR homophones still apply to the cloned voice's wake words — the voice clone changes timbre, not recognition.
- Don't skip the clean-segment step: cloning from a segment with BGM/echo gives a muddy clone.
- If similarity is poor, get more/better reference audio before tweaking model params — reference quality dominates.
