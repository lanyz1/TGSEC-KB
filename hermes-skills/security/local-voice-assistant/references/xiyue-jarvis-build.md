# 汐月 & 贾维斯 build state (D:\xibei) — resumable

User: 阿荣, Windows 10, RTX 5080 16GB (Blackwell!), Ryzen 7 9800X3D, 61.6GB RAM, D: 646GB free.
Network: GFW. hf-mirror.com + ModelScope + tsinghua pypi = direct; GitHub needs proxy 127.0.0.1:10808.

## Decisions locked with user (2026-08-02)

- **Dual persona, one engine**: wake "贾维斯" → work assistant (Qwen3-14B), wake "汐月/阿月/小月" → girlfriend (GLM-4-9B-chat). Hot-swap model by wake word (terminate + restart llama-server).
- **Full local privacy**: LLM + ASR + TTS + memory all offline. edge-tts used ONCE to generate Taiwan-accent reference voices (ref_yujie.mp3 / ref_tianmei.mp3 already generated), CosyVoice2 local clone planned as final TTS backend.
- **Girlfriend persona**: 高冷御姐 ⇄ 甜妹, switches by context AND explicit command; Taiwan accent; addresses 阿荣/老板/老公 situationally. Work persona calls user 老板, terse.
- **Dangerous ops**: voice confirmation loop (TTS ask → ASR confirm). 开机自启 + phone remote (TG bot/Web) + ESP32-S3 voice box = P5/P6 pending.
- **Fine-tune path agreed**: two-step — run generic models first, then QLoRA fine-tune 汐月 (Unsloth, GLM-4-9B or Qwen3-14B base) on generated persona data. User wanted a genuinely "专属" model; was told honest cost reality (from-scratch training impossible, LoRA fine-tune viable on 5080, 2-10h).
- User prefers: model choices presented as option tables, never dictated; corrections must be honest and immediate (was told GLM-4.5-Air was 10B, corrected to 110B before download).
- User prefers: every download shows a visible progress bar (no silent curl); bat files ANSI+CRLF (see SKILL.md Pitfalls).

## Layout (as of end of 2026-08-02 session)

```
D:\xibei\
  config.yaml                  # paths, llama_server (jarvis/xiyue — both now point at Qwen3-14B), voice, tools, memory, remote — PORT 8081 (8080 taken by NERV-BREAK)
  start.bat                    # one-click start (needs ANSI+CRLF regen if re-written by write_file)
  venv\                        # Python 3.11 (fragile: created from Hermes's venv — prefer stdlib-only scripts)
  bin\                         # OLD llama.cpp b10232 CUDA-12.4 — POLLUTED by cudart overwrite, DO NOT USE
  bin\v13\                     # GOOD: llama.cpp b10233 CUDA-13.3 (llama-server.exe + cudart64_13/cublas64_13) — use THIS one for RTX 5080
  models\
    Qwen3-14B-Q4_K_M.gguf      # THE model — drives BOTH personas; only 汐月 active now (8.4GB) — VERIFIED WORKING (chat + tool_calls)
    glm-4-9b-chat-Q4_K_M.gguf  # dead — tokenizer-broken under new llama.cpp, keep only as reference
    asr\{encoder.onnx, decoder.onnx, tokens.txt}   # sherpa-onnx streaming paraformer
  app\
    personas.py  # 汐月 system prompt (GLM persona retained; 贾维斯 persona code kept but unused)
    llm.py       # LlamaManager: start/swap/chat (OpenAI-compatible) — bakes enable_thinking:false into EVERY payload
    voice.py     # VoiceEngine: wake-word listen loop + recognize_command
    tts.py       # TTSEngine (edge now, cosyvoice hook), gen_reference_voices
    tools.py     # ToolExecutor + TOOLS + XIYUE_TOOLS + dangerous regex
    memory.py    # JSONL + keyword recall + summarize_today
    main.py      # Assistant: on_wake → dialog loop → tool loop → speak
    test_jarvis.py / test_chat.py  # pure-stdlib (urllib) CLI chat tests — NO requests dependency
  data\
    ref_yujie.mp3 / ref_tianmei.mp3   # 台湾口音参照音 (已生成)
    memory.jsonl
    shots\
Desktop (hand-off scripts, ANSI+CRLF via gen_bats.py — user keeps ONLY these two):
  启动汐月.bat    # chcp 65001 + llama-server Qwen3-14B :8081 — keep window OPEN
  跟汐月说话.bat  # chcp 65001 + python app\test_chat.py
  (dead/ignorable: 启动贾维斯.bat, 跟贾维斯说话.bat, 下载Qwen3-8B.bat, 下载13.3引擎.bat, 通用下载器.bat, 启动汐月测试.bat, 汐月项目交接文档.md)
```

## CRITICAL session lessons (2026-08-02 afternoon)

1. **RTX 5080 (Blackwell sm_120) requires the CUDA 13.x llama.cpp build.** The 12.4 build (b10232) `--list-devices` shows the GPU but produces GARBLED output (pure-ASCII punctuation) and ~5 tok/s. Correct: `llama-b10233-bin-win-cuda-13.3-x64.zip` + `cudart-llama-bin-win-cuda-13.3-x64.zip` from GitHub release b10233, into `bin\v13\`.
2. **cudart zip overwrites engine DLLs if unzipped into the engine dir** (contains ggml.dll/llama.dll/ggml-cuda.dll). Must unzip engine → copy only cudart64_13.dll/cublas64_13.dll/cublasLt64_13.dll. This overwrite is the likely cause of the GLM garbled output that was still unresolved at session end — **next step: clean-reinstall v13 engine, copy only 3 cudart DLLs, retest GLM.**
3. **Garbled output triage**: same GGUF ran clean on CPU earlier → corruption is engine-DLL/template level, not the model file. Check md5sum of ggml.dll/llama.dll in the active dir vs. a fresh engine unzip.
4. **bat encoding**: write_file produces UTF-8/LF → cmd eats first char of each line. Regen via Python `replace("\n","\r\n").encode("gbk")`; keep prompts ASCII-only.
5. **venv python in bat**: use full path `D:\xibei\venv\Scripts\python.exe`, not `activate.bat` + bare `python` (system python wins → ModuleNotFoundError).
6. Port 8080 occupied by NERV-BREAK relay → project uses 8081.

## Exact download URLs

```
# ModelScope (FAST, ~39MB/s — prefer this in CN):
https://modelscope.cn/models/Qwen/Qwen3-14B-GGUF/resolve/master/Qwen3-14B-Q4_K_M.gguf
# hf-mirror (slow ~1.5MB/s, resume with curl -C - + retry loop):
https://hf-mirror.com/Qwen/Qwen3-14B-GGUF/resolve/main/Qwen3-14B-Q4_K_M.gguf
https://hf-mirror.com/bartowski/glm-4-9b-chat-GGUF/resolve/main/glm-4-9b-chat-Q4_K_M.gguf
https://hf-mirror.com/csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en/resolve/main/{encoder.onnx,decoder.onnx,tokens.txt}
# llama.cpp engine (GitHub, needs proxy 127.0.0.1:10808) — release b10233:
llama-b10233-bin-win-cuda-13.3-x64.zip
cudart-llama-bin-win-cuda-13.3-x64.zip
```
Note: repo is `Qwen/Qwen3-14B-GGUF` (not -2507 suffix); GLM-4.5-Air GGUF repos are all 110B — do not use.

## RESOLVED at session end (2026-08-02 evening)
- **GLM garbling root cause FOUND: the 2024-era GLM-4-9B GGUF itself is tokenizer-incompatible with new llama.cpp** — it loads with warning `special_eot_id is not in special_eog_ids - the tokenizer config may be incorrect` and outputs ASCII-punctuation garbage on BOTH CPU (`-ngl 0`) AND GPU. Proven: same v13 engine runs Qwen3-14B perfectly. NOT a cudart-DLL issue (the cudart-overwrite theory was wrong; v13 dir was clean). GLM model is dead — do not retry it.
- **"贾维斯不能用了" false alarm — it was Qwen3 thinking mode.** Symptom: `content:""` empty + `reasoning_content` full + `finish_reason:"length"`. The `--chat-template-kwargs '{"enable_thinking":false}'` startup flag AND `LLAMA_ARG_CHAT_TEMPLATE_KWARGS` env var both silently failed; the fix that worked: **send `"chat_template_kwargs": {"enable_thinking": false}` in every request body**. Now baked into `llm.py` + test scripts. Qwen3-14B verified: chat OK (0.7s) + tool_calls OK.
- **FINAL ARCHITECTURE DECISION (user overrode dual-persona): delete 贾维斯, keep ONLY 汐月, and run 汐月 directly on the Qwen3-14B model** (no Qwen3-8B download, no model hot-swap). Reasons: 16GB VRAM holds only one model (~12.4GB for 14B); user wants a single companion. The desktop Qwen3-8B downloader (`下载Qwen3-8B.bat`) is obsolete — do not run it. `config.yaml` xiyue.model now points at `Qwen3-14B-Q4_K_M.gguf`; `启动汐月.bat` + `跟汐月说话.bat` are the only two scripts the user needs. Verified: 汐月 persona on Qwen3-14B replies in 1.6s with Taiwan-accent sweet-girl tone. Jarvis bats are dead files on the Desktop (harmless, ignorable).
- **Console-encoding final solution**: bat first line `chcp 65001 >nul` + Python `sys.stdin/stdout.reconfigure(encoding="utf-8")` — this user's OS has UTF-8 Beta enabled, so the earlier GBK-reconfigure approach garbled (`��Լ�ά˹˵` mojibake); chcp 65001 + UTF-8 combo is the verified fix. test_jarvis.py / test_chat.py are pure-stdlib (urllib, no requests) so no venv dependency chain.

## NEW this session (evening, after 交接文档): voice loop VERIFIED end-to-end

- **Full spoken round-trip works**: `语音启动.bat` → `app/voice_main.py` → wake word (汐月→"七月" homophone) → ASR recognized user's actual question ("你会做什么") → 汐月 replied correctly with Taiwan-accent tone → TTS spoke it. The live log proved wake→ASR→LLM→TTS all connected. `main.py` is superseded by `voice_main.py` (direct HTTP to running server; adds echo prevention).
- **Echo loop hit and fixed**: her own TTS greeting got picked up by the mic and fed back as a "user" command (log: `[asr] 指令: 阿荣我在呢你说话有什么想说` — that's her welcome line) → infinite self-conversation. Fix in `voice_main.py`: `tts_speak()` pauses the mic (`voice_engine.pause()` = stream.stop + drain), plays via BLOCKING `subprocess.run(["ffplay",...])`, then `resume()` (stream.start + fresh recognizer stream) in finally, 0.3s settle. VoiceEngine gained pause()/resume(). Details in SKILL.md §3.
- **Real-time ASR form that works on this machine**: callback + queue (NOT blocking `s.read()`), 48kHz float32, `enable_endpoint_detection=False`, feed from queue with is_ready loop. `test_asr.py` v5 is the verified pattern (recognized 七月你好七月). find_mic.py confirmed device 12.
- **TTS voice tuning state**: user rejected default robotic edge-tts. 4 rate variants A/B'd (+0/+18/+25/+35%), user picked **+25% / +6Hz**. Then user disliked the TIMBRE → 4-voice A/B generated (`t1_晓臻_台湾`, `t2_晓晓_大陆`=most natural, `t3_晓萱_大陆`, `t4_晓伊_大陆`) at that rate — **user's final pick NOT yet locked when session ended** (he was reviewing them). Next step: confirm which of the 4 timbres 汐月 uses; bake into `VOICE_STYLES` in tts.py (e.g. `{"rate": "+25%", "pitch": "+6Hz"}` + chosen voice name). Files in `D:\xibei\data\voice_test\`.

## Resume checklist

1. **Already done (do NOT redo)**: GLM garbling diagnosed (tokenizer-incompatible GGUF, dead end); Qwen3 thinking-mode fixed via per-request `chat_template_kwargs`; final arch = single persona 汐月 on Qwen3-14B, verified replying 1.6s.
2. Verify downloads (sizes: 8.4GB Qwen3-14B; encoder 606MB + decoder 218MB + tokens.txt).
3. **ASR bring-up status — DONE (voice loop verified)**: `app/test_asr.py` + `app/voice.py` fixed for sherpa-onnx 1.13.4 API — `from_paraformer` (NOT from_transducer, no joiner file exists), `recognizer.get_result(stream)` / `recognizer.is_endpoint(stream)` / `recognizer.decode_stream(stream)` / `recognizer.is_ready(stream)` (stream has no .result/.is_endpoint; **decode_stream MUST be driven by an is_ready loop**, and capture at 48kHz with 100ms reads — the official pattern in sherpa-onnx-official-pattern.md; this killed the `GetFrames: 0 + N > M` assertion and the empty-output problem). **Mic found via scan (`scripts/find_mic.py`): device 12 `Primary Sound Capture Driver` (external sound card, peak 0.68)**; default device was a silent bus mixer; "耳机式麦克风 (LP90 Pro)" was the Bluetooth SPEAKER — names lie, scan volumes instead. `config.yaml` has `mic_device: 12`; voice.py reads it. **Real-time form that works here: callback+queue (NOT blocking s.read()), 48kHz float32, `enable_endpoint_detection=False`** — verified: WAV fed at true rate recognizes cleanly (`您好西月...` = 汐月你好); live callback loop recognized `七月你好七月` in test_asr.py v5; full spoken round-trip in voice_main.py worked (wake→ASR→LLM→TTS).
4. Next real steps: **confirm 汐月's TTS timbre pick (t2 晓晓大陆 likely) + bake into VOICE_STYLES**; then P3 dangerous-confirm live test; tune endpoint silence rules (voice.py rule1/2).
5. Tune: TTS backend switch to CosyVoice2 (reference voices already generated), 御姐/甜妹 voice switching.
6. P3: dangerous-confirm live test. P4: memory summary cron. P5: auto-start (Task Scheduler/NSSM) + TG bot + LAN web. P6: ESP32-S3 voice box (purchase list + flashing + serial bridge).
7. Optional revisit: fine-tune 汐月 (QLoRA on Qwen3-14B) for a genuinely 专属 model — user agreed two-step path; data generation still pending user's persona素材.
8. Process hygiene: after any llama-server restart, confirm exactly ONE instance (`Get-Process llama-server`) — stacked instances froze the machine at 15.5GB/16GB VRAM.

## Tool-chain notes for this machine

- git-bash: `wmic` absent → `powershell -NoProfile -Command '...'` with single quotes (bash eats `$`).
- `tasklist //FO CSV //NH` / `cmd //c` both break in git-bash — use `cmd /c "tasklist /FO CSV /NH"` quoted, or PowerShell `Get-Process`.
- python 3.11.15; pip → tsinghua mirror `-i https://pypi.tuna.tsinghua.edu.cn/simple`.
- ffplay present (WinGet) for TTS playback.
- Proxy env for GitHub/raw: `-x http://127.0.0.1:10808`.
- hf-mirror `/api/models/...` returns empty; probe files with `curl -sIL <resolve-url>` and grep HTTP/content-length (200 + length = exists, 404 = wrong filename).
- aria2 (`winget install aria2.aria2`) got blocked by Windows firewall at 16 threads ("socket forbidden"); 4 threads worked but no faster than curl — prefer ModelScope for big files.
