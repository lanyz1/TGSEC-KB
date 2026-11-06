---
name: local-ai-voice-assistant
description: >-
  测绘引擎·Use when building offline local AI voice assistants.
owned: true
tier: general
pack: survey-skill
---

# local-ai-voice-assistant（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/local-ai-voice-assistant/`

溯源（仅标记）：`hermes/mlops`

---

# Local AI Voice Assistant (offline, Windows)

Use this skill when building a private/local voice assistant ("Jarvis", AI companion, AI girlfriend) that must run fully offline on one Windows PC: wake word → speech-to-text → local LLM → tool execution → text-to-speech. All data stays on the machine.

## When to use

- User wants a voice-controlled assistant / AI girlfriend / Jarvis running locally, no cloud APIs
- Deploying llama.cpp (`llama-server`) on Windows with an NVIDIA GPU
- Wiring sherpa-onnx streaming ASR + wake words + TTS into a Python app
- Any task where the user insists on privacy → every component must be local

## Architecture blueprint (proven)

```
[mic + speaker] → wake-word (streaming ASR + text match, NO separate KWS model)
                → ASR text → llama-server (OpenAI-compatible /v1/chat/completions)
                → optional tool layer (subprocess / pyautogui / files) with danger confirmation
                → TTS (edge-tts to bootstrap; CosyVoice for cloned voices)
```

- One engine, multiple personas: route by wake word; **load ONE model at a time** (16GB VRAM cannot hold two ~10GB models; switching costs ~10s)
- Wake word via always-on streaming ASR + substring match works for ANY custom name (separate KWS models can't recognize arbitrary Chinese words)
- Personas = separate system prompts + per-role tool sets (chatbot gets a trimmed tool list)

## Critical pitfalls (all hit in production)

1. **Qwen3 empty replies**: Qwen3 defaults to thinking mode → `content` is empty and the draft sits in `reasoning_content`. Fix: send `"chat_template_kwargs": {"enable_thinking": false}` **in every API request**. Server-start flags (`--chat-template-kwargs`, env var) did NOT work; request-level did.
2. **RTX 50xx (Blackwell) needs CUDA 13.x builds**: the CUDA-12.4 llama.cpp build recognizes the GPU but produces garbage/mixed output. Use `llama-b*-bin-win-cuda-13.3-x64.zip` + its matching `cudart-llama-bin-win-cuda-13.3-x64.zip`.
3. **NEVER unzip cudart over the main program dir**: the cudart zip also contains `ggml.dll`; extracting it on top of the engine dir overwrites the correct DLL with a mismatched version → random ASCII garbage output from every model. Extract engine zip first, then copy ONLY `cublas64_*.dll`, `cublasLt64_*.dll`, `cudart64_*.dll` from the cudart zip.
4. **Windows bat files must be ANSI(GBK) + CRLF**: a bat written as UTF-8/LF (what editors/write_file produce) makes cmd eat the first char of each line (`echo`→`cho`) and garble Chinese. Generate bats from Python: `content.replace("\n","\r\n").encode("gbk")`. Put `chcp 65001 >nul` at the top of bats that run Python printing Chinese, and in the Python script do `sys.stdin/stdout.reconfigure(encoding="utf-8", errors="replace")`.
5. **sherpa-onnx 1.13.x API changed**: streaming paraformer loads via `OnlineRecognizer.from_paraformer(tokens, encoder, decoder, ...)` — NOT `from_transducer` (which demands a joiner). Text/endpoint live on the RECOGNIZER: `rec.get_result(stream)` and `rec.is_endpoint(stream)`; `stream.result.text` no longer exists.
6. **Model downloads in China**: ModelScope (`modelscope.cn/models/<org>/<repo>/resolve/master/<file>`, ~39MB/s, direct) is ~20× faster than hf-mirror (~2MB/s). Use ModelScope for Qwen GGUF; hf-mirror as fallback; GitHub needs the local proxy.
7. **venv fragility**: a venv created from another venv's python (e.g. Hermes's own venv) breaks when the parent moves; `python` on PATH may point at the wrong interpreter. Verify with `python -c "import sys; print(sys.executable)"`. Either install deps into the `python` that bat files will call, or write CLI test scripts with stdlib-only (`urllib.request` instead of `requests`) so any python works.
8. **Multiple llama-server instances pile up VRAM**: each new `llama-server` launch leaves old ones running (15GB+ used). Check `powershell Get-Process llama-server`; kill extras by PID with `Stop-Process -Id <pid> -Force` (git-bash `taskkill //F //PID` mangles args).
9. **Port conflicts**: 8080 is commonly taken by other tools (e.g. NERV-BREAK relay). Use 8081+. Check with `curl localhost:<port>/health` → `{"status":"ok"}`.
10. **Test Chinese via Python, not curl**: cmd/curl send GBK bytes and break JSON. Always test the API from Python `requests`/`urllib` with `ensure_ascii=False`.
11. **TTS echo feedback loop**: the assistant's own voice playback is picked up by the mic, re-recognized as a new command, answered again → infinite self-conversation (log shows `[asr] 指令:` repeating the assistant's own reply). Fix: `pause()` the mic InputStream (stop stream + drain queue) BEFORE playing TTS, `resume()` (start + reset ASR stream) after playback finishes. Always pass the voice engine handle into the TTS call.
12. **Verify the real mic device FIRST, before debugging ASR**: the default `sd.default.device` can be a mixer with no signal (e.g. `Recording Mixer kX 10k1` — peak 0.0002 = dead). Run a "find my mic" scan: enumerate input devices, record 0.5s each, report peak volume, ask user to speak while it scans; pick the device with volume > 0.01 (a sound card / USB mic typically lands on `Primary Sound Capture Driver`). Put the device index in config, NOT a hardcoded guess. A user's bluetooth speaker may falsely appear as an input device — trust the volume scan, not the name.
13. **Streaming paraformer: feed 48kHz, call decode via `is_ready` loop** (official example `streaming-paraformer-asr-microphone.py`): record at 48000 (`samples_per_read = int(0.1*48000)`), `stream.accept_waveform(48000, samples)`, then `while recognizer.is_ready(stream): recognizer.decode_stream(stream)`. Feeding raw 16k data that was actually captured at 48k garbles recognition (yields one-character results like "嗯"); skipping the `is_ready`-gated decode causes `GetFrames: 0 + 61 > 19` assertions and empty results. Note `sd.rec()`-based recording works but the blocking `s.read()` InputStream may return silence on some sound cards — the callback-based InputStream is the reliable path.
14. **Wake-word list needs homophone variants**: ASR transcribes custom names with common homophones (汐月 → 七月/西月/惜月/希月/晓月/萧月; 贾维斯 → 佳维斯/假维斯/家维斯). The wake-word match list must include these or the user's spoken name won't trigger. Test the matcher with a table of expected hit/miss cases before wiring audio.
15. **`pip` vs `python -m pip` may target different interpreters**: on this machine bare `pip` resolved to a different env than `python` → package installed but `import` failed at runtime. Rule: always install with `python -m pip install ...` so the package lands in the interpreter that runs the code.
16. **Global `PYTHONPATH` env var can poison EVERY python on the machine (deepest root cause)**: if `echo $PYTHONPATH` shows `C:\...\hermes-agent;...\hermes-agent\venv\Lib\site-packages`, then every python process — regardless of which venv you activate — resolves packages from that path first. Symptom: you install into `venv_clone` (site-packages verified via `site.getsitepackages()`), but `import tokenizers` still loads `...\hermes-agent\venv\Lib\site-packages\tokenizers`. ALL prior venv/install fixes look broken; this is why. Fix: run with `env -u PYTHONPATH -u PYTHONHOME <python> ...` (bash) or `set PYTHONPATH=& set PYTHONHOME=& <python> ...` (cmd/.bat). In .bat launchers, put `set PYTHONPATH=` at the TOP, before any python call. Check `sys.executable` AND `sys.prefix` when diagnosing — prefix pointing at hermes-agent means you're still poisoned.
17. **A venv built FROM Hermes' python inherits its broken base even after the PYTHONPATH fix**: `D:\xibei\venv` was created with `hermes-agent\venv\Scripts\python.exe -m venv` → its pyvenv.cfg `home`/`executable` point into hermes-agent; `import` may still resolve there. Build independent venvs with the REAL system python: `C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe -m venv <dir>` (this machine's clean 3.12.10, has working pip 25.0.1). `uv venv --python <that path>` also works and is fast. Never create the project venv from hermes-agent's python.
18. **`pip install` of a HUGE package (torch ~2.7GB) can hang forever with CPU≈0 while small packages install fine**: pip's dependency-resolution phase stalls (visits blocked upstream metadata). `pip download` hangs the same way. Bypass: get the wheel URL yourself and pull it with curl, then `pip install <local.whl>` (or `pip install --no-deps` + install deps separately). The TUNA simple index pages use RELATIVE hrefs (`../../packages/<hash>/torch-2.11.0-cp312-cp312-win_amd64.whl`) — prepend `https://pypi.tuna.tsinghua.edu.cn/`; the `simple/<pkg>/` page is static HTML, fetch it with curl `-H "User-Agent: pip/25.0"`. Verify download is progressing by polling the file size, not the pip process. Note pip's `--progress-bar` accepts only `on|off|raw` in pip 25 (no `pretty`).
19. **Media apps hijack .mp3 playback and survive ffplay kills**: playing a generated mp3 with `os.startfile` hands it to the system default app — here Douyin's **SodaMusic** (7 processes) kept playing after ffplay was killed, and the user heard audio with no visible player. When user says "还在播放" after ffplay cleanup, sweep media apps too: `Get-Process | ? { $_.ProcessName -match "ffplay|mpv|vlc|wmplayer|Groove|Music|MediaPlayer|SodaMusic|QQMusic|cloudmusic" } | Stop-Process -Force` (ask the user first — SodaMusic may be their own music app).

## Deployment sequence (Windows)

1. Hardware check: `nvidia-smi` (VRAM), RAM, free disk. Pick model: 16GB VRAM → 14B Q4 (~9GB) or 8B Q4 (~5GB); both fit ONE at a time.
2. Get engine: GitHub releases → `llama-b<build>-bin-win-cuda-13.3-x64.zip` + `cudart-llama-bin-win-cuda-13.3-x64.zip` (see pitfall 3 for extraction order).
3. Get models: ModelScope for Qwen GGUF (`Qwen/Qwen3-14B-GGUF` etc.), hf-mirror for others.
4. Python env: install `sherpa-onnx sounddevice numpy edge-tts pyautogui pyscreenshot requests` into the interpreter your bats will actually call (pitfall 7).
5. Get ASR model: `csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en` → `encoder.onnx` + `decoder.onnx` + `tokens.txt` (no joiner).
6. Launch `llama-server -m <model.gguf> --host 127.0.0.1 --port 8081 -ngl 99 -c 16384 --jinja`; verify `/health`.
7. Test chat with thinking disabled, then tool calls, then wire ASR+TTS.

## User conventions (this user)

- Every download task must show a visible progress bar — use PowerShell `Invoke-WebRequest` (its default progress) or `curl --progress-bar`; never silent `curl -s` downloads.
- Multi-step deployments: present the plan first, get approval, then execute.
- One model running at a time; keep the server window open (closing it kills the assistant).
- Never kill/restart running processes without telling the user first.
- **Voice-tuning UX**: when adjusting TTS voice, generate numbered sample files into ONE folder (`试听集/01_xxx.mp3 ... 10_xxx.mp3`) + a `00_说明.txt` mapping each number to its setting, then play them in order. The user listens sequentially and reports a number — do not make them remember parameter names. Iterate on rate/pitch in small steps (`+15%` → `+12%` → `+10%`) until they pick. Clean up stray ffplay processes (`powershell Get-Process ffplay | Stop-Process -Force`, re-check) when the user says audio is still playing.
- **Default TTS tuning**: edge-tts `rate`/`pitch` are the tuning knobs (`Communicate(text, voice, rate="+15%", pitch="+4Hz")`). Default edge-tts Taiwan voices sound robotic/official to this user; `zh-CN-XiaoxiaoNeural` (晓晓) at ~+12% rate was chosen as most natural, then final voice replaced by a cloned one.

## Voice cloning from video (make the assistant sound like a real person)

User may want the assistant's voice cloned from a sample (a video of a real person). Workflow verified this session:

1. Get the source: Douyin links are hard to auto-download — yt-dlp demands fresh cookies (`ERROR: Fresh cookies ... are needed`), the headless-browser blob download doesn't persist to disk. Fastest reliable path: **ask the user to save the video locally** (Douyin app 保存本地 → send to PC, or browser 视频另存为) and hand you the file path.
2. Extract audio: `ffmpeg -i in.mp4 -vn -ac 1 -ar 16000 full.wav`.
3. **If background music covers the whole video** (common in vlogs), you CANNOT clone directly — the music gets learned into the voice. Run AI source separation first: `python -m demucs --two-stems=vocals -n htdemucs full.wav -o separated` → yields `vocals.wav` (clean speech) + `no_vocals.wav`. (`demucs` installs via pip; watch the pip/python env pitfall #15.)
4. Find a clean 10–30s speech segment in `vocals.wav`: energy-scan windows (RMS per 2s), but if BGM was everywhere even separation leaves residual, cut segments and let the USER listen to choose the clearest one.
5. Clone with CosyVoice2 (offline, zero-shot from ~10s reference) — see the project reference for the exact bootstrap.
6. Replace the edge-tts backend with the cloned voice; keep the pause/resume echo fix from pitfall 11.

## References

- **[windows-bat-encoding.md](references/windows-bat-encoding.md)** — bat GBK/CRLF/chcp rules, python IO reconfigure, generator pattern
- **[llama-cpp-windows-cuda.md](references/llama-cpp-windows-cuda.md)** — Blackwell/CUDA 13.x details, cudart extraction order, Qwen3 thinking fix, VRAM budgeting, process cleanup
- **[sherpa-onnx-voice.md](references/sherpa-onnx-voice.md)** — streaming paraformer loading, get_result/is_endpoint API, wake-word-by-ASR design, TTS bootstrap with edge-tts
- **[voice-loop-debugging-and-cloning.md](references/voice-loop-debugging-and-cloning.md)** — echo-feedback fix, mic-device energy scan, 48k-feed/is_ready decode pattern, homophone wake words, demucs vocal separation + CosyVoice2 cloning from video

## Resources

- llama.cpp releases: https://github.com/ggml-org/llama.cpp/releases
- ModelScope: https://modelscope.cn
- sherpa-onnx: https://github.com/k2-fsa/sherpa-onnx (models on HF `csukuangfj/...`)
- edge-tts voices: zh-TW-HsiaoYuNeural (sweet), zh-TW-HsiaoChenNeural (mature) for Taiwan-accent references
