<!-- archived from /root/.hermes/skills/security/local-voice-ai-assistant/SKILL.md on 2026-10-21 -->

---
name: local-voice-ai-assistant
description: >-
  测绘引擎·Build a fully-local voice AI assistant on Windows.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/local-voice-ai-assistant`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/local-voice-ai-assistant/…')`，不要相对 `references/legacy/` 解析。

# local-voice-ai-assistant（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/local-voice-ai-assistant/`

溯源（仅标记）：`hermes/mlops`

---

# Local Voice AI Assistant (Jarvis / AI-girlfriend style, fully offline)

Build a voice-controlled assistant that lives on the user's Windows PC: talk to it, it controls the computer (open apps, run commands, click, type, read files) and talks back — with a personality. All inference stays on-device (privacy requirement).

## When to use
- User wants "my own Jarvis / AI girlfriend / AI companion" that controls their PC by voice
- Requirement: FULL privacy — no cloud APIs for brain/ASR/TTS/memory
- Multi-persona routing (e.g. work-assistant + girlfriend on the same engine)

## Architecture (one engine, N personas)

```
[PC mic+speaker] ─┐
[ESP32 voice box] ─┼─> Python core (常驻服务)
[phone remote] ────┘        │
                            ├─ wake word: streaming ASR, text-match on wake words
                            ├─ brain: llama.cpp server (GGUF, CUDA) — switch model per persona
                            ├─ tool layer: subprocess/pyautogui + dangerous-op verbal confirm
                            ├─ TTS: edge-tts (startup) → CosyVoice2 cloned voice (privacy final)
                            └─ memory: JSONL keyword recall (local, no vector DB needed to start)
```

- Persona routing = wake word → role → model + system prompt + voice. Same engine, hot-swap model.
- Project layout that worked: `D:\xibei\{config.yaml, start.bat, app\{personas,llm,voice,tts,tools,memory,main}.py, bin\ (llama.cpp), models\{GGUF,asr\}}`

## Key components & versions (verified working)

### 1. llama.cpp server (brain)
- **CUDA build version MUST match GPU architecture.** RTX 5080 (Blackwell, sm_120) needs the **CUDA 13.x build** (`llama-b10233-bin-win-cuda-13.3-x64.zip`). The 12.4 build passes `--list-devices` but compute kernels silently corrupt output (garbled text, ~5 tok/s) — cost a whole debugging session. Check `nvidia-smi --query-gpu=name` first: 13.x for Blackwell, 12.x for Ampere/older. (GitHub release download needs proxy in CN)
- **cudart zip must NOT be unzipped over the main engine dir.** `cudart-llama-bin-win-cuda-13.3-x64.zip` contains ggml.dll/llama.dll/ggml-cuda.dll alongside cudart64_13 — extracting it into the same folder as the engine **overwrites the engine's own DLLs with a mismatched set → garbage output on BOTH CPU and GPU**. Correct install: unzip engine zip → copy ONLY cudart64_13.dll/cublas64_13.dll/cublasLt64_13.dll from the cudart zip. Verify: `md5sum ggml.dll llama.dll` should match the ENGINE zip, never the cudart zip.
- **Garbled-output triage**: output that is pure printable-ASCII punctuation (e.g. `D'D!$16+'9%!-;4!=8D0...`) = template/tokenizer/engine-DLL corruption, NOT a bad GGUF and NOT a GPU failure. If the same file ran clean on CPU earlier → suspect DLL overwrite (cudart zip) or wrong CUDA-arch build. `md5sum` the DLLs and reinstall cleanly. A `special_eot_id is not in special_eog_ids - tokenizer config may be incorrect` load warning on old-format GGUFs (e.g. 2024 GLM-4-9B conversions) is another tokenizer-corruption signal — model "talks" fast (120 tok/s) but decodes to garbage; try a same-family newer model or a different GGUF converter.
- Launch: `llama-server.exe -m <winpath> -ngl 99 -c 16384 --jinja`
  - `--jinja` reads the chat template from the GGUF — do NOT hardcode chatml/chatglm3 per model, it's auto
  - **Qwen3 thinking-mode OFF: the startup flag does NOT work — use the per-request JSON field.** Symptom: `content: ""` (empty) with `reasoning_content` full of inner monologue, `finish_reason: "length"`. The `--chat-template-kwargs '{"enable_thinking":false}'` startup flag AND the `LLAMA_ARG_CHAT_TEMPLATE_KWARGS` env var BOTH silently failed in the 13.3 build (git-bash quote mangling / not honored). Fix: send `"chat_template_kwargs": {"enable_thinking": false}` inside EVERY request body to `/v1/chat/completions`. Bake it into the LLM client payload, not the server launch.
- OpenAI-compatible: `POST /v1/chat/completions` with `tools` + `tool_choice:auto`; model returns `tool_calls` → execute → append `role:tool` results → loop (max ~5 iters)
- Health: `GET /health` → `{"status":"ok"}`
- **Model size pitfall: verify config.json params before recommending** (GLM-4.5-Air is 110B MoE, not 10B!). See llm-selfhost-planning skill.
- **Only ONE model running at a time.** Two ~8GB models loaded together exhaust RAM and freeze the machine (user hit this hard). Hot-swap = terminate server, restart with other GGUF.

### 2. sherpa-onnx (wake word + ASR, all local)
- `pip install sherpa-onnx` (1.13.4 verified)
- Streaming Chinese model: `sherpa-onnx-streaming-paraformer-bilingual-zh-en` (encoder.onnx ~606MB + decoder.onnx ~218MB + tokens.txt). NOTE: it has NO joiner — load with `OnlineRecognizer.from_paraformer(tokens=, encoder=, decoder=, ...)`, NOT `from_transducer` (that needs joiner and errors)
- **API drift in 1.13.4**: methods moved off `OnlineStream` — always `dir()` the object before coding: `create_stream`, `accept_waveform` exist; `is_endpoint`/`result` are NOT on the stream in this version. Check with `dir(sherpa_onnx.OnlineStream)` / `dir(stream)` at runtime, don't trust old docs.
- Wake words: do NOT use KWS models (vocab can't hold custom Chinese names like 汐月). Instead run the streaming ASR constantly + regex-match wake words in partial text — zero false negatives for custom names, fine on 9800X3D.
- Audio: `sounddevice.InputStream(samplerate=16000, channels=1, dtype='int16', blocksize=3200)` → numpy float32 → `accept_waveform`. Endpoint detection built into recognizer (rule1/2/3 trailing-silence params).

### 3. TTS (mouth)
- Start with `edge-tts` (free, works in CN): `asyncio.run(edge_tts.Communicate(text, voice).save(out))`. Taiwan-accent voices: `zh-TW-HsiaoChenNeural` (mature/御姐) + `zh-TW-HsiaoYuNeural` (young/甜妹).
- Privacy-final path: generate ONE reference clip per voice via edge-tts (one-time, ~2 sentences), then clone locally with CosyVoice2 — permanent offline after bootstrap.
- Playback: `ffplay -nodisp -autoexit` (Windows winget installs ffmpeg/ffplay; check `where ffplay`).

### 4. Tool layer (hands)
- pyautogui (mouse/keyboard, FAILSAFE=True) + subprocess `cmd /c` + `os.startfile` for apps/URLs + pyscreenshot
- **Dangerous-op guard**: regex list (`rm`, `del`, `format`, `diskpart`, `shutdown`, `taskkill /f`…) → LLM tool returns "needs confirmation" → assistant SPEAKS the question → ASR listens for 确认/取消 → only then execute. This was a hard user requirement.
- GLM-4-9B tool-calling is weaker: give girlfriend persona a MINIMAL 2-tool set (open_app, read_file), full 7-tool set to the work persona.

## Windows / git-bash pitfalls (all hit this session)
- **Native exes (llama-server.exe) do NOT accept MSYS paths** (`/d/xibei/...` → "No such file or directory"). Pass Windows paths: `-m "D:\\xibei\\models\\x.gguf"`.
- Port 8080 is often taken (NERV-BREAK relay etc.) — check `netstat -ano | grep LISTEN` and pick free port (8081 worked); put it in config.yaml.
- curl POST with Chinese text from git-bash mangles UTF-8 (GBK console) → JSON parse errors from server. Use Python `requests` for any Chinese payload.
- big model load: `llama-cli -p ...` on an 8GB GGUF can look hung (>300s) — it's loading to VRAM. Use `--no-display-prompt` and grep for `error|failed` only, or just start the server and poll /health.
- Playback audio via `os.startfile` in background = opens default player window; prefer ffplay with CREATE_NO_WINDOW.
- **Windows .bat files: MUST be ANSI(GBK) + CRLF, never UTF-8/LF.** `write_file` emits UTF-8/LF → cmd mangles it: first char of each line eaten (`echo`→`cho`), Chinese comments garbled (`瓑寰?`). Symptom: "X is not recognized as an internal or external command" for your own echo lines. Fix: generate .bat via Python `content.replace("\n","\r\n").encode("gbk")` (write_file can't do it), or keep bat 100% ASCII. Verify with a byte read before shipping to the user.
- **User preference (阿荣): every download must show a visible progress bar** — no silent `curl -s`. Use PowerShell `Invoke-WebRequest -UseBasicParsing` (draws its own progress bar) in .bat downloaders, or `curl --progress-bar`. Also: .bat launchers for the user should call venv python by FULL path (`D:\\xibei\\venv\\Scripts\\python.exe`), because `call venv\\Scripts\\activate.bat` then bare `python` can resolve to the system python → ModuleNotFoundError for venv packages.
- **Python scripts launched from a .bat need GBK console handling** (second layer after the .bat encoding fix). cmd is code page 936 (GBK): a UTF-8 script's `input("中文提示")` reads GBK bytes → `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc4...`. Put at top of every script the user will double-click: `sys.stdin.reconfigure(encoding="gbk", errors="replace"); sys.stdout.reconfigure(encoding="gbk", errors="replace")` (try/except). You need BOTH the ANSI+CRLF .bat AND this reconfigure.
- **chcp 65001 alternative (used when GBK reconfigure still shows mojibake)**: if the user's system has "Beta: Use Unicode UTF-8" enabled or the window code page is already 65001, forcing GBK output makes things WORSE. Robust fix: .bat starts with `chcp 65001 >nul`, and the Python script reconfigures stdin/stdout to `utf-8` instead of gbk. Both combos (gbk-reconfigure + default 936, utf8-reconfigure + chcp 65001) are valid; pick based on what the user's console shows. Verify with a simulated double-click (`cmd /c <bat>` via subprocess with `input=` piped) before shipping.
- **Multi-turn chat launcher**: a test script that asks ONE question then exits feels broken ("只能聊一句就自动退出"). For a chat .bat, loop: maintain `messages` list (system prompt + history), append user turn, POST, append assistant reply, repeat until user types a farewell word (拜拜/再见/退出/bye/exit). The LLM needs the full history for context; without it every turn forgets prior conversation.
- **venv created from another venv is fragile — prefer pure-stdlib scripts for user-facing launchers.** pyvenv.cfg `executable`/`home` pointed at Hermes's own venv (created FROM it); if that base moves, venv python breaks even with full paths. When a user .bat keeps failing on imports, rewrite the launcher using ONLY stdlib (`urllib.request` + `json`, no `requests`) and call plain `python` — zero dependency chain. Confirmed working for 跟X说话.bat launchers.
- **Escalation control for auto-deploy**: when repeated auto-deploy attempts fail (downloads flaky, garbage output, machine freezes), the user may demand to take over ("暂停,我不要你帮我自动部署了,我自己来"). STOP auto-fixing immediately; deliver: (1) honest status table of what works / what doesn't, (2) click-level .bat scripts + a handoff document (assets, known issues, fix directions, from-scratch steps), (3) full reset instructions (delete project dir + desktop scripts). Do not delete user assets without explicit choice; offer keep-vs-reset options via clarify.

## Model pick (16GB VRAM, RTX 5080, tested)
- Work persona: Qwen3-14B-Instruct Q4_K_M (~8.4GB) — solid tool calling, Chinese good
- Girlfriend persona: **Qwen3-14B reuse (user's final choice)** — GLM-4-9B-chat (5.8GB) was the original pick but its 2024-era GGUF is tokenizer-incompatible with new llama.cpp (`special_eot_id is not in special_eog_ids` warning + ASCII-punctuation garbage on BOTH backends, not flag-fixable). Qwen3-8B (~5GB) was the planned swap, but the user simplified: drop the work persona entirely, run girlfriend on Qwen3-14B. For a dual-persona build, Qwen3-8B remains the proven same-family drop-in.
- 16GB holds ONE model at a time → hot-swap per wake word (config-driven, ~5-10s reload) OR single-persona single-model (simpler, this user's choice)
- Download in CN: ModelScope resolve URLs are ~20-40x faster than hf-mirror (see llm-selfhost-planning skill)

## Workflow
1. Clarify persona/name/wake-words/voice/boundaries FIRST (user requirement: 先出计划再动手, one page at a time)
2. Verify hardware (nvidia-smi, RAM, disk) → pick models
3. Download models via ModelScope first, hf-mirror+retry-loop second
4. Prove brain alone (llama-server + curl/Python chat + tool_calls loop) BEFORE wiring audio — debugging voice+LLM together is miserable
5. Wire ASR + TTS loop, then tools, then memory, then auto-start + remote

## References
- `references/xiyue-jarvis-project.md` — the 汐月&贾维斯 project: dual persona spec, config, wake-word routing, component versions, current build status
