---
name: local-voice-assistant
description: >-
  测绘引擎·Local offline voice AI assistant (Jarvis/AI女友) for PC.
owned: true
tier: general
pack: survey-skill
---

# local-voice-assistant（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/local-voice-assistant/`

溯源（仅标记）：`hermes/voice-ai`

---

# Local Voice AI Assistant (Jarvis / AI 女友)

Build a voice-controlled personal AI that runs 100% on the user's machine: wake word → speech-to-text → local LLM with tool calling → text-to-speech → optionally controls the computer. No cloud, no data leaves the box.

## When to use

- User asks for "贾维斯", "AI女友", voice assistant, Jarvis-like control of the PC
- Requirement is full privacy / local models only (全本地, 数据不出机)
- Multi-persona: one engine, several "people" (work assistant + girlfriend) switched by wake word
- User wants model choices presented as options with tradeoffs, NOT dictated — this user explicitly pushed back on being handed a single pick

## Architecture (proven layout)

```
[PC mic + speaker] / [ESP32 voice box] / [phone remote (TG/Web)]
        │
        ▼
Wake word detection ── routes to persona ──┐
        │                                  │
Streaming ASR (sherpa-onnx paraformer)     │
        │                                  │
LLM (llama.cpp llama-server, GGUF) ◄───────┘
        │  + tools (OpenAI-compatible /v1/chat/completions, tools=)
        ▼
TTS (edge-tts bootstrap → CosyVoice clone)
```

Key decisions to make with the user BEFORE building (this user cares):
1. Persona(s): names, wake words, personality, how they address the user, mode-switching rules
2. Model per persona (present a table of candidates per VRAM tier — exact picks + download URLs in references/xiyue-jarvis-build.md)
3. What the AI may do directly vs. must confirm (dangerous ops)
4. Privacy boundary: which components must be local vs. acceptable one-time cloud use
5. Remote channels (phone/voice box) and auto-start

## Component picks (all local, verified in build)

### 1. Wake word + ASR — sherpa-onnx streaming paraformer (zh-en bilingual)

- Files: `encoder.onnx` (~600MB) + `decoder.onnx` (~220MB) + `tokens.txt`, repo `csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en`. **There is NO model.onnx — it's an encoder/decoder split.**
- `pip install sherpa-onnx`
- **Wake word = text-match on streaming ASR output** (regex over decoded text). Custom Chinese names (汐月/阿月/小月) work reliably this way; KWS (keyword-spotter) models have fixed vocab and fail on custom words — do NOT use KWS for custom wake words.
- **Wake-word lists MUST include homophone variants.** Streaming ASR freely transcribes homophones: user said 汐月, ASR returned 七月你好七月; 贾维斯 came back as 假维斯/佳维斯. A list containing only the canonical spelling misses real wakes. Ship per-persona homophone-expanded lists (汐月/七月/西月/惜月/希月/晓月/萧月; 贾维斯/佳维斯/假维斯/家维斯) and unit-test the matcher against both homophones and non-wake phrases (this session: 8/8 passed, incl. 七月→xiyue, 假维斯→jarvis, ordinary talk→None).
- **sherpa-onnx 1.13.4 API (verified — differs from older docs/tutorials)**: load streaming paraformer with `OnlineRecognizer.from_paraformer(tokens=..., encoder=..., decoder=..., num_threads=4, sample_rate=16000, feature_dim=80, enable_endpoint_detection=True, rule1_min_trailing_silence=2.4, rule2_min_trailing_silence=1.2, rule3_min_utterance_length=300)`. **NOT `from_transducer`** — that path requires a `joiner` argument the paraformer repo does not ship (`TypeError: ... missing 1 required positional argument: 'joiner'`).
- **In 1.13.4 the stream has NO `.result` and NO `.is_endpoint()`** — those moved to the recognizer: `recognizer.get_result(stream)` and `recognizer.is_endpoint(stream)`.
- **MUST drive `decode_stream` with an `is_ready` loop, and record at 48kHz** (the OFFICIAL sherpa-onnx pattern — verified end-to-end; this finally stopped the `features.cc:GetFrames: 0 + N > M` assertion). Decoding unconditionally after every chunk, or feeding raw 16kHz blocks, throws `GetFrames` assertions even with healthy mic volume:
  ```python
  sample_rate = 48000                      # record at 48k; sherpa resamples to 16k internally
  samples_per_read = int(0.1 * sample_rate)  # 100ms blocking reads
  stream = recognizer.create_stream()
  with sd.InputStream(channels=1, dtype="float32", samplerate=sample_rate, device=12) as s:
      samples, _ = s.read(samples_per_read)
      stream.accept_waveform(sample_rate, samples)
      while recognizer.is_ready(stream):   # NOT unconditional decode_stream
          recognizer.decode_stream(stream)
      result = recognizer.get_result(stream).strip()
      if recognizer.is_endpoint(stream):
          recognizer.reset(stream)
  ```
  Full reference: the official example `streaming-paraformer-asr-microphone.py` in k2-fsa/sherpa-onnx `python-api-examples/` (fetch it rather than guessing API usage). Historical note: `accept_waveform(16000, ...)` + unconditional `decode_stream` at 16kHz DID produce text initially, then hit `GetFrames: 0 + 61 > 19` — the 48kHz + is_ready loop is the stable form.
- `num_threads=1` in the official example; `enable_endpoint_detection=True` with `rule1_min_trailing_silence=2.4, rule2_min_trailing_silence=1.2, rule3_min_utterance_length=300`.
- **Mic device selection — do NOT trust the default input device or device names.** Default was `Recording Mixer (kX 10k1 Audio)` — a bus mixer with near-zero signal (peak 0.0002/3s → "no speech" even when talking). Names lie too: `耳机式麦克风 (LP90 Pro)` was actually the user's Bluetooth SPEAKER, not a mic. Correct procedure: scan ALL input devices, record ~0.5s each, rank by peak volume (`np.max(np.abs(rec))`) — the real mic wins (external sound card = `Primary Sound Capture Driver`, peak 0.68). Bake the winning index into config (`mic_device: 12`) and pass `device=` to `sd.InputStream`. Reusable scanner: `scripts/find_mic.py`.
- Continuous-conversation window (e.g. 20s after each utterance, no re-wake needed) is a UX requirement the user expects.

### 2. LLM brain — llama.cpp llama-server (CUDA build) + GGUF

- **CUDA build version MUST match the GPU architecture.** RTX 5080 (Blackwell, sm_120) needs the **CUDA 13.x build** (`llama-b10233-bin-win-cuda-13.3-x64.zip`). The CUDA 12.4 build `--list-devices` shows the GPU but **compute kernels silently corrupt output** (garbled text, ~5 tok/s). This cost a whole debugging session — check arch first: `nvidia-smi --query-gpu=name` then pick 13.x for Blackwell, 12.x for Ampere/older.
- **cudart zip must NOT be unzipped over the main engine dir.** `cudart-llama-bin-win-cuda-13.3-x64.zip` contains ggml.dll/llama.dll/ggml-cuda.dll alongside cudart64_13 — extracting it into the same folder as the engine **overwrites the engine's own DLLs with a mismatched set → garbage output on BOTH CPU and GPU**. Correct install: unzip engine zip → copy ONLY cudart64_13.dll/cublas64_13.dll/cublasLt64_13.dll from the cudart zip. Verify after: `md5sum ggml.dll` differs between engine zip and cudart zip is expected; never let cudart zip's ggml.dll win.
- **Garbled-output triage**: output that is pure printable-ASCII punctuation (e.g. `D'D!$16+'9%!-;4!=8D0...`) = template/tokenizer/engine-DLL corruption, NOT a bad GGUF and NOT a GPU failure. Same file ran clean on CPU earlier → suspect DLL overwrite (cudart zip) or wrong CUDA arch build. `md5sum` the DLLs and reinstall cleanly.
- Flags: `-m <model.gguf> -ngl 99 -c 16384 --jinja` — **`--jinja` auto-detects the chat template embedded in the GGUF; do NOT hardcode chatml/chatglm3.**
- **Qwen3 thinking-mode OFF: the startup flag does NOT work — use the per-request JSON field.** Symptom of thinking mode on: reply comes back `content: ""` (empty) with `reasoning_content` full of the model's inner monologue, `finish_reason: "length"`, ~0.7-5s. The `--chat-template-kwargs '{"enable_thinking":false}'` startup flag and the `LLAMA_ARG_CHAT_TEMPLATE_KWARGS` env var BOTH silently failed in the 13.3 build (git-bash quote mangling / not honored) — the model kept thinking. The fix that worked: send `"chat_template_kwargs": {"enable_thinking": false}` inside **every request body** to `/v1/chat/completions`. Bake it into the LLM client's payload, not the server launch.
- **Old GLM-4-9B GGUF (2024-era) is tokenizer-incompatible with new llama.cpp** — loads fine, warns `special_eot_id is not in special_eog_ids - the tokenizer config may be incorrect`, then outputs ASCII-punctuation garbage on BOTH CPU and GPU backends. Not fixable by flags; swap the persona to a Qwen-family GGUF (Qwen3-8B is the proven drop-in for the chat persona). Distinguish this from the cudart-DLL corruption: tokenizer warning present + same garbage on `-ngl 0` = model file issue; no warning + only GPU garbles = engine/DLL issue.
- Windows: run with `subprocess.Popen(..., creationflags=subprocess.CREATE_NO_WINDOW)`; health check `GET /health` → 200 before first call (14B Q4 on RTX 5080 ≈ 2min load).
- Hot-swap between personas: one server at a time, terminate + restart with the other GGUF (5-10s). 16GB VRAM holds ONE ~10GB model + KV cache only.
- **One llama-server at a time — check for stacked instances.** During debugging, terminated servers were restarted without killing the old ones; 3 instances stacked = 15.5GB/16GB VRAM → system freeze. After any restart, verify: `Get-Process llama-server` count == 1 and `nvidia-smi --query-gpu=memory.used` is sane. Kill strays via `powershell -NoProfile -Command "Stop-Process -Id <pid> -Force"` (git-bash `taskkill //F //PID` breaks; `cmd //c` breaks too).
- 16GB VRAM picks: work model Qwen3-14B Q4_K_M (9.3GB); chat model **Qwen3-8B Q4_K_M (~5GB)** — GLM-4-9B-chat (5.8GB) was the original chat pick but its 2024 GGUF is tokenizer-broken under new llama.cpp (see garbled-output triage); GLM-4.5-Air is 110B MoE — does NOT fit. Exact filenames + download URLs: references/xiyue-jarvis-build.md.
- Tool calling: register OpenAI `tools` schema via `/v1/chat/completions`; loop: reply has tool_calls → execute → append tool results → call again (max ~5 iterations). **GLM-4-9B tool-calling under llama.cpp is unreliable — give chat personas only 2-3 safe tools (open_app, read_file); full toolset for the work persona only.**

### 3. TTS — edge-tts bootstrap → CosyVoice clone

- edge-tts (free, works in China): Taiwan-accent voices exist — `zh-TW-HsiaoChenNeural` (成熟御姐) / `zh-TW-HsiaoYuNeural` (甜妹). `asyncio.run(edge_tts.Communicate(text, voice).save(path))`.
- **Default edge-tts delivery sounds robotic — tune rate/pitch and A/B-listen with the user before locking a voice.** `edge_tts.Communicate(text, voice, rate="+25%", pitch="+6Hz")` supports rate/pitch overrides. Proven workflow: generate 4 rate variants of one sentence (+0%, +18%, +25%, +35%, pitch bumping +0→+8Hz). **User correction (阿荣): do NOT auto-play candidates sequentially via ffplay and expect him to remember which was which ("我记不清楚"). Instead copy ALL candidates into ONE numbered folder (e.g. `D:\xibei\data\试听集\`) as `01_….mp3, 02_….mp3…` plus a `00_说明.txt` legend mapping each number → voice/rate/pitch, and let him listen at his own pace and report a number.** This user chose "+25%/+6Hz" (活泼但自然) over the robotic default. If they then dislike the TIMBRE itself (not just speed), generate cross-voice alternatives on the same rate for A/B: `zh-TW-HsiaoChenNeural` (other Taiwan option), `zh-CN-XiaoxiaoNeural` (most natural overall), `zh-CN-XiaoxuanNeural` (少女感), `zh-CN-XiaoyiNeural` (干练). Final settled pick this session: `zh-CN-XiaoxiaoNeural` at `rate='+12%', pitch='+4Hz'` (fine-tuned +25→+15→+12, each round = regenerate a new numbered file in the 试听集 folder). Bake the winner into a per-persona `VOICE_STYLES` dict (`{"rate": "+12%", "pitch": "+4Hz"}`) in tts.py — a config-level switch, not a code change.
- **Echo-loop prevention is MANDATORY in the voice loop: pause the mic while TTS plays, or the speaker audio gets re-recognized as the user's next command → infinite self-conversation.** Live symptom: after wake, `[asr] 指令: 阿荣我在呢你说话有什么想说` — that was the assistant's OWN greeting picked up by the mic and fed back as input. Fix in `voice_main.py`: `voice_engine.pause()` (stop InputStream + drain queue) before synthesizing/playing → play with BLOCKING `subprocess.run(["ffplay", ...])` (NOT Popen — must wait for playback to finish) → `voice_engine.resume()` (restart stream + fresh recognizer stream) in a `finally`. Give the mic a 0.3s settle delay after resume. Implement pause/resume on VoiceEngine as stream.stop()/start() + drain + `recognizer.create_stream()`.
- Privacy path: use edge-tts ONCE to generate reference audio for the persona's voice, then switch TTS backend to CosyVoice2 (local zero-shot cloning from that reference). User approved this one-time-cloud-then-offline pattern.
- Playback: ffplay if present (`ffplay -nodisp -autoexit -loglevel quiet file.mp3`), else `os.startfile`.
- **\"Audio still playing after killing ffplay\" → a music app hijacked the .mp3 association.** On this user's machine SodaMusic (汽水音乐, Douyin's music app) had registered system audio playback; `os.startfile`/double-clicking .mp3 routed to it, so killing ffplay left it playing. Triage: `Get-Process | Where-Object { $_.ProcessName -match 'ffplay|mpv|vlc|wmplayer|Groove|Music|SodaMusic' }` — look for music apps, not just players. Kill via `powershell -NoProfile -Command 'Get-Process <name> | Stop-Process -Force'` (single quotes — bash eats `$`). Also note `Get-Process ffplay | Stop-Process` intermittently leaves one behind; re-check with a fresh `Get-Process` after 1s.

### 4. Computer-control tools (the "do anything" layer)

- pyautogui (mouse/keyboard; **FAILSAFE=True**), `subprocess.run(["cmd","/c",cmd], creationflags=CREATE_NO_WINDOW)`, `os.startfile` for apps/URLs, pyscreenshot for screen capture.
- Tool names: run_command, open_app, type_text, click, screenshot, read_file, list_dir.

### 5. Safety — dangerous-op confirmation (voice loop)

- Regex blocklist on commands (rm, del, format, diskpart, shutdown, reg delete, taskkill /f, rd /s, rmdir /s, del /s, cipher /w, > windows path).
- Matched → do NOT execute: TTS-ask "这是危险操作:{desc}。确认执行吗?" → re-run ASR → proceed only on 确认/可以/执行/对/好/是. This is non-negotiable for a voice-controlled machine; user agreed and wants it tuned gradually.

### 6. Memory — local JSONL + keyword recall (no vector DB for v1)

- Append JSONL entries `{t, cat, imp, text}`; recall = token-overlap scoring × importance × time decay (1/(1+age_days*0.02)); inject top-k as an extra system message before each turn.
- "自观察" = the assistant records the user's statements AND its own replies as dialogue entries; nightly/periodic summary job folds the day into a summary entry.

## Persona design (dual-mode example that works)

- Girlfriend (汐月): 高冷御姐 ⇄ 甜妹 — switches by context (work talk → 御姐) AND by explicit user command ("阿月,切御姐腔"); Taiwan-accent TTS; addresses user situationally (阿荣/老板/老公).
- Work assistant (贾维斯): professional, terse, tool-heavy, reports results in one line.
- Per-persona: system prompt, wake words, voice, toolset, memory scope. Memory stores may share but route by role.

## Pitfalls

- **ECHO LOOP: the assistant talks to itself.** Symptom: after the welcome TTS, ASR logs show the assistant's OWN words as the next "user" utterance (`[asr] 指令: 阿荣我在呢你说话有什么想说` — that's her welcome line coming back through the mic), then she replies again → infinite loop. Speaker audio gets picked up by the mic. Fix: **pause the mic stream while TTS plays, resume after** — add `pause()` (stream.stop + drain queue) / `resume()` (stream.start + reset ASR stream) to the voice engine and wrap every TTS playback in them (use blocking `subprocess.run([ffplay ...])` so you know playback finished before resuming). Proven in build.
- **TTS voice selection — verify by listening, don't assume accent preference survives.** User asked for Taiwan accent; edge-tts `zh-TW-HsiaoYuNeural`/`HsiaoChenNeural` sounded too robotic ("语速太像机器人了"). Presented 6 candidates (2 TW + 4 CN voices at the chosen rate) — user picked `zh-CN-XiaoxiaoNeural` (most natural) at `rate='+12%', pitch='+4Hz'` (settled on +12 after trying +25 then +15; each fine-tune = one ffplay A/B listen). edge-tts supports rate/pitch args: `edge_tts.Communicate(text, voice, rate='+12%', pitch='+4Hz')`. Bake per-persona VOICE_STYLES dict {rate, pitch} into the TTS layer.
- **Voice cloning from a user-supplied video** (e.g. "克隆这个视频里女孩的声音"): extract 10-30s clean speech → CosyVoice2 zero-shot clone (fully local). Douyin acquisition, ffmpeg extraction, and CosyVoice2 steps: `references/voice-cloning.md`. **CosyVoice deps are scattered and requirements.txt fails on py3.12 — run the auto-loop `scripts/fix_cosy_deps.py` (import → install missing → retry) instead of hand-installing one-by-one.**
- **`features.cc:GetFrames: 0 + N > M` assertion = ASR chunking mismatch, not a mic problem.** Happens when decode is called before enough frames are buffered or chunk sizes don't match the streaming encoder. Fix = the 48kHz + `is_ready` loop pattern above. Don't chase the mic volume (it's fine) when this error shows.
- **Windows .bat files: MUST be ANSI(GBK) + CRLF, never UTF-8/LF.** `write_file` emits UTF-8/LF → cmd mangles it: first char of each line eaten (`echo`→`cho`), Chinese comment garbled (`瓑寰?`). Symptom: "X is not recognized as an internal or external command" for your own echo lines. Fix: generate .bat via Python `content.replace("\n","\r\n").encode("gbk")` (write_file can't do it), or keep bat 100% ASCII + no chcp 65001. Verify with a byte read before shipping to the user.
- **User preference (阿荣): every download must show a visible progress bar** — no silent `curl -s`. Use PowerShell `Invoke-WebRequest -UseBasicParsing` (draws its own progress bar) in .bat downloaders, or `curl --progress-bar`. Also: bat launchers for the user should call venv python by FULL path (`D:\\\\xibei\\\\venv\\\\Scripts\\\\python.exe`), because `call venv\\\\Scripts\\\\activate.bat` then bare `python` can resolve to the system python → ModuleNotFoundError for venv packages.
- **When an auto-deploy/debug loop stalls, hand the user runnable .bat files instead of continuing to fight remotely.** This user (小白, impatient, was burned all night) explicitly demanded: \"你直接告诉我怎么跑,我手动去跑\" and \"你太废物了,一晚上还没做好\". The recovery pattern that ended the loop: (1) state the ONE root cause in plain words (the PYTHONPATH trap), (2) stop debugging, (3) deliver 2 numbered double-click .bats on the Desktop — an install one with `set PYTHONPATH=& set PYTHONHOME=&` prefix + `pip install --progress-bar on` (pip 25 accepts only `on|off|raw` — `pretty` is an invalid choice there; draw the progress bar via `on`, the user's explicit ask), and a run-one — plus 2-3 copy-paste cmd lines as fallback. Each .bat must `chcp 65001 >nul` + GBK+CRLF + full paths. Let the user drive from there and only interpret their pasted error output. Long silent tool-call loops with no user-facing artifact read as incompetence; a handoff script is both faster and restores trust.
- **Python scripts launched from a .bat need console-encoding handling** — second layer on top of the .bat encoding fix. cmd runs at code page 936 (GBK) by default; a UTF-8 script's `input("中文提示")` reads GBK bytes and dies `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc4...` (looks like a broken script, it's the console). Two proven fix combos:
  - **Final working combo (prefer this)**: put `chcp 65001 >nul` as the first line of the .bat (window switches to UTF-8 code page), AND at the top of the Python script `sys.stdin.reconfigure(encoding="utf-8"); sys.stdout.reconfigure(encoding="utf-8")` (try/except). Verified: clean Chinese prompt + reply when double-clicked, regardless of the system's regional setting (works even if the OS has UTF-8 Beta enabled — in which case the GBK combo below garbles).
  - **GBK combo (works when OS is pure GBK)**: no chcp, script reconfigures stdin/stdout to `gbk`. This was the first fix tried and garbled on a UTF-8-Beta system — if output shows `��Լ�ά˹˵`-style mojibake where content is clearly present, switch to the chcp 65001 + UTF-8 combo.
  - You need BOTH the ANSI+CRLF .bat AND one of these reconfigure combos.
- **venv created from another venv is fragile — prefer pure-stdlib scripts for user-facing launchers.** This venv's `pyvenv.cfg` had `executable`/`home` pointing at Hermes's own venv (it was created FROM it); if that base moves/updates the venv python breaks even with full paths. When a user-facing .bat keeps failing on imports across environments, stop fighting: rewrite the launcher/test script using ONLY stdlib (`urllib.request` + `json`, no `requests`) and call plain `python` — zero dependency chain to break. Confirmed working for the 跟X说话.bat pattern.
- **THE BIG ONE: a system-level `PYTHONPATH` env var silently redirects EVERY Python process's imports to another environment — check it FIRST when packages \"won't install\" or keep version-conflicting.** This user's machine had `PYTHONPATH=C:\\Users\\Administrator\\AppData\\Local\\hermes\\hermes-agent;C:\\...\\hermes-agent\\venv\\Lib\\site-packages` set at the OS level. Consequence: every `python`/`pip` invocation (even inside a fresh venv with its own site-packages) imported packages from Hermes's venv — torch/transformers/tokenizers version conflicts that no amount of reinstall fixed, `venv_clone/Scripts/python.exe` reporting Hermes's site-packages, `import tokenizers` loading `0.23.1` no matter what you pip-installed. This burned an entire night of \"clone pipeline fails mysteriously\". **Diagnose instantly:** `echo $PYTHONPATH` (bash) or check with `python -c "import sys; print(site.getsitepackages())"` — if it shows a foreign path, that's the root cause. **Fix: prepend `set PYTHONPATH=& set PYTHONHOME=` to every bat / `env -u PYTHONPATH -u PYTHONHOME <python> ...` to every command** so the process starts clean. Also re-verify with `python -c \"import tokenizers; print(tokenizers.__file__)\"` that it now loads from the intended venv. This is the single most expensive environment trap on this user's box — check it before ANY multi-package Python work.
- **Clean venv creation on this box**: system Python is `C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python312\\python.exe` (NOT the Hermes venv that bare `python` resolves to). Create with full Windows paths (`\"C:\\...\\Python312\\python.exe\" -m venv D:\\xibei\\venv_clone`) — git-bash path mangling (`/d/xibei` → `D:\\d\\xibei`) breaks it otherwise. **New venv may lack pip** (`No module named pip` after creation, from a Permission-denied ensurepip during `-m venv`) — fix with `<venv>/Scripts/python.exe -m ensurepip --upgrade` before any install.
- **GLM-4.5-Air is 110B MoE (~60GB Q4)** — never recommend it for 16GB VRAM. Verify model param counts before promising sizes (this session caught it via HF search after wrongly calling it 10B).
- GLM-4-9B tool-calling under llama.cpp is flaky — minimal toolset for chat personas.
- hf-mirror.com `/api/models/...` returns empty/404; use `resolve/main/<file>` probing (details in references/xiyue-jarvis-build.md). **ModelScope `resolve/master/...` is ~20-40x faster than hf-mirror in CN (39MB/s vs 1.5MB/s)** — check ModelScope first (e.g. `modelscope.cn/models/Qwen/Qwen3-14B-GGUF/resolve/master/Qwen3-14B-Q4_K_M.gguf`). HF API over proxy returns `Invalid username or password` (proxy interference) — probe with `curl -sIL` on resolve URLs instead.
- Don't hardcode chat templates; `--jinja` reads them from GGUF.
- Windows git-bash: `wmic` is absent — use `powershell -NoProfile -Command '...'` with SINGLE quotes (bash eats `$`); also `$` interpolation breaks in double quotes.
- edge-tts is cloud (Microsoft) — OK for one-time reference voices, not for the always-on pipeline if the user demands full privacy.
- Download speeds from hf-mirror can be ~1.5MB/s; 8GB models take ~1.5h — start downloads in background with notify_on_complete and keep building the code meanwhile.

## Verification

1. `llama-server` health 200 + one `/v1/chat/completions` round-trip per model.
2. ASR: speak a wake word → console prints `[wake] <role>`.
3. Tools: ask it to open notepad; verify process exists.
4. Danger path: ask to delete a file → it must ask confirmation → say no → nothing deleted.
5. TTS: each persona speaks with its own voice (Taiwan accent for girlfriend).

## ASR debugging: isolate mic vs pipeline BEFORE touching real-time

When real-time recognition returns empty despite healthy mic volume, do NOT keep tweaking the stream — isolate first:

1. **WAV-first isolation**: record ~5s to a file (`sd.rec(..., device=MIC_IDX)` → save WAV) and feed that WAV to the same streaming recognizer (`accept_waveform` in 100ms chunks + is_ready loop). 
   - WAV recognizes but live stream doesn't → pipeline/streaming problem (chunking, callback, device stream mode).
   - WAV ALSO empty → model/sample-rate/config problem. 
   - This single step separates "mic" from "ASR" in one shot — proven: same 48kHz WAV that produced garbage labeled-as-16k (`嗯`) recognized cleanly (`您好西月...`) once fed at its true 48000 rate.
2. **`sd.rec` (blocking) vs `sd.InputStream` (callback) diverge on the same device** — tested both. Blocking one-shot `sd.rec` captured audio fine (peak 0.77), but the LIVE `s.read(n)` blocking-read InputStream returned EMPTY in this build even though volume was healthy (peak 0.68 in the same callback InputStream). **The form that finally worked end-to-end was callback + queue (`callback=lambda indata,frames,t,s: q.put(indata.copy())`, main loop drains `q.get(timeout=0.5)`), 48kHz float32, `enable_endpoint_detection=False`**, feeding the recognizer from the queue. If live recognition is empty: (a) verify mic index via find_mic.py, (b) verify volume is >0.01 in the live stream, (c) switch between callback-queue and blocking-read forms — one will work on a given device/PortAudio backend where the other silently returns nothing.
3. Feed samples at the **recorded native rate** (`accept_waveform(48000, chunk)`) — labeling 48k samples as 16k silently garbles to `嗯`/empty.
4. Print peak volume per chunk (`np.max(np.abs(block)))` so you can tell "no signal" from "recognizer not decoding" at a glance.

## References

- **[xiyue-jarvis-build.md](references/xiyue-jarvis-build.md)** — concrete build state of the user's D:\xibei project: locked decisions, layout, exact download URLs, resume checklist
- **[sherpa-onnx-official-pattern.md](references/sherpa-onnx-official-pattern.md)** — verified 48kHz + is_ready-loop microphone skeleton (stops GetFrames assertions)
- **[voice-cloning.md](references/voice-cloning.md)** — clone a persona voice from a user-supplied video (Douyin acquisition, ffmpeg extraction, CosyVoice2 zero-shot, fully local). **Resume state 2026-08 (pipeline RUNS end-to-end on CPU; quality gate remains):** the box's OS-level PYTHONPATH redirects imports to Hermes's venv (must `set PYTHONPATH=` / `env -u PYTHONPATH -u PYTHONHOME` first); "torch import hangs" was MISSING NUMPY — CPU torch 2.11.0 imports fine (<60s) once numpy is installed; CosyVoice deps are scattered and surface at BOTH import and model-load time (openai-whisper, inflect, omegaconf, scipy, conformer, diffusers, wget) — use the two-stage auto-dependency loop `scripts/fix_cosy_deps.py`; torchaudio 2.11 forces torchcodec — patch `cosyvoice/utils/file_utils.py load_wav` to stdlib wave+numpy and your save calls to a stdlib wav writer; **CPU clone now works after patching `cosyvoice/cli/model.py` to `.float()` the three sub-models on CPU (bf16-checkpoint vs fp32-input crash) — output WAVs generated (clone_test_1/2.wav), BUT user judged CPU synthesis quality 杂音/破音/语调怪, so a GPU (cu128) torch install via Aliyun pytorch-wheels mirror is the pending quality step**; model already at `D:\xibei\data\clone\CosyVoice2-0.5B`, clean reference at `D:\xibei\data\clone\vocals_mono_denoised.wav`.
