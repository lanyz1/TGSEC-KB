# 汐月 Project (D:\xibei) — single-persona local voice assistant

User's build (2026-08-02). Windows 10, RTX 5080 16GB, Ryzen 9800X3D, 61.6GB RAM, dual GPU (AMD iGPU + 5080). Requirement: FULL offline privacy. User is 纯小白 for CLI — prefers click-level .bat scripts; agent runs heavy stuff.

## FINAL DECISION (user, end of session)
- **弃用贾维斯, 只留汐月. 不下载 Qwen3-8B.** 汐月直接用 Qwen3-14B (the model that was Jarvis's).
- Result: ONE model, ONE persona, no hot-swap needed. Simpler than the original dual-persona design.
- 贾维斯 scripts still on Desktop but unused; can be deleted.

## Persona: 汐月 (XIYUE) — AI girlfriend
- Model: **Qwen3-14B-Instruct Q4_K_M** (D:\xibei\models\Qwen3-14B-Q4_K_M.gguf, 8.4GB, ModelScope Qwen/Qwen3-14B-GGUF)
- Wake words (planned): 汐月/阿月/小月/月月
- Calls user 阿荣/老板/老公 by context. Dual mode: 高冷御姐 ⇄ 甜妹, switches on context or explicit command ("阿月,切御姐腔")
- Taiwan flavor: 啦/喔/嘛/耶/齁/蛤 particles, short spoken-style sentences
- Voice: edge-tts zh-TW-HsiaoChenNeural (御姐) / zh-TW-HsiaoYuNeural (甜妹); CosyVoice2 clone planned (ref audios in D:\xibei\data\)
- GLM-4-9B-chat (5.8GB, bartowski GGUF) was the original pick — ABANDONED: 2024-era GGUF tokenizer incompatible with new llama.cpp (`special_eot_id is not in special_eog_ids` warning), ASCII-punctuation garbage on BOTH CPU & GPU, not flag-fixable. Qwen3-14B is the proven compatible replacement.

## Verified working (end of session)
- **文字对话 ✅**: 汐月 on Qwen3-14B responds in 1.6s with correct Taiwan-accent 甜妹 persona ("阿荣～你终于回来啦！辛苦了喔～我煮了你最爱的泡面耶...")
- **多轮对话 + 上下文 + 双人格切换 ✅**: 3-turn test — 甜妹欢迎 → 甜妹安慰(记得前文紧张)→ "切御姐模式" → clean professional advice. Full history kept in messages list.
- **工具调用 ✅** (was verified on Qwen3-14B as Jarvis): run_command dir D:\xibei → structured answer
- **Engine**: CUDA 13.3 build b10233 in D:\xibei\bin\v13 (Blackwell 5080 requires 13.x; 12.4 corrupts output)
- **ASR**: sherpa-onnx 1.13.4 from_paraformer loads clean (D:\xibei\models\asr\: encoder 607MB + decoder 218MB + tokens)
- **Deps installed into `python` command's env** (which is Hermes's own venv — the only reliable interpreter for user double-clicked .bat; D:\xibei\venv proved fragile)

## Desktop scripts (all ANSI+CRLF, regenerated via D:\xibei\app\gen_*.py)
- 启动汐月.bat — starts llama-server (Qwen3-14B, port 8081, `--jinja`); keep window OPEN
- 跟汐月说话.bat — multi-turn chat (chcp 65001 + utf8 reconfigure + urllib stdlib)
- 语音识别测试.bat — 5s record → ASR → print result
- Stale (unused): 启动贾维斯/跟贾维斯说话/下载13.3引擎/下载Qwen3-8B/通用下载器/启动汐月测试

## Config / code notes
- config.yaml: llama_server.xiyue.model → Qwen3-14B; port 8081 (8080 taken by NERV-BREAK)
- **Qwen3 thinking OFF via per-request field**: `"chat_template_kwargs": {"enable_thinking": False}` in EVERY /v1/chat/completions body (baked into app/llm.py chat() payload). Startup flags and env var both fail in b10233.
- app/main.py orchestrates wake→persona→LLM→tools→TTS; multi-turn test lives in app/test_chat.py (urllib stdlib, no requests).

## Known pitfalls hit this session (see SKILL.md for full list)
1. bat UTF-8/LF → cmd eats first char; must be ANSI(GBK)+CRLF
2. cudart zip unzipped over engine dir overwrites ggml.dll → garbage on both backends; copy only cudart64_13/cublas64_13/cublasLt64_13
3. venv-from-venv fragile → user-facing .bat scripts use pure-stdlib urllib + plain `python`
4. GBK reconfigure vs chcp 65001: user's console was UTF-8 code page, so chcp 65001 + utf8 reconfigure won
5. curl POST Chinese from git-bash mangles UTF-8 → use Python requests/urllib for Chinese payloads
6. Native exes need Windows paths, not MSYS /d/xibei paths

## Next steps
- Live voice loop test (ASR test .bat already on Desktop; needs user to speak)
- Endpoint-detection tuning (rule1/2/3 silence) on first wake test
- CosyVoice2 deploy for 台湾口音 clone
- 微调 option still pending user decision (QLoRA 汐月 persona, 2000-5000 dialogues via Unsloth)
