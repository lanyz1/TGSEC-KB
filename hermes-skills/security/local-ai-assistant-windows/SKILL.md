---
name: local-ai-assistant-windows
description: >-
  测绘引擎·Use when building local AI voice assistants on Windows.
owned: true
tier: general
pack: survey-skill
---

# local-ai-assistant-windows（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/local-ai-assistant-windows/`

溯源（仅标记）：`hermes/software-development`

---

# 本地AI语音助手 (Windows)

构建"对电脑说话 → 本地LLM → 语音回答"的助手(贾维斯/AI女友类项目)。整条链路: 唤醒词 → ASR → LLM → TTS, 全本地。**本技能集中了多次踩坑后的可靠做法。**

## 架构

```
[麦克风] → 唤醒词(sherpa-onnx 流式ASR + 文本匹配) → LLM(llama.cpp server, OpenAI API)
         → TTS(edge-tts 过渡 / CosyVoice2 克隆音) → [音箱]
```

- 唤醒词用**流式 ASR 常驻 + 文本匹配**(自定义中文词如"汐月/阿月"无需训练, KWS 模型词表没有自定义词)
- 双人格/双模型 = 一核换载: 一次只加载一个模型(显存 16GB 装不下两个), 按唤醒词切换, 切换 5~10s
- 注意: 8080 等端口可能被本机中转代理(NERV-BREAK)占用, 用 8081

## RTX 50系 (Blackwell) 跑 llama.cpp

- **必须用 CUDA 13.x 版编译的 llama.cpp**, 12.4 版能识别显卡但推理输出乱码(纯ASCII标点)
- 下载: GitHub releases 的 `llama-bXXXXX-bin-win-cuda-13.3-x64.zip` + `cudart-llama-bin-win-cuda-13.3-x64.zip`
- **cudart 包绝不能解压覆盖主程序目录**(会覆盖 ggml.dll/llama.dll 为不匹配版本 → 所有模型乱码)。只把 cudart64/cublas64/cublasLt64 三个 dll 拷进主目录
- 验证: `nvidia-smi` 看显存占用(模型进显存=5~12GB), 日志 `eval time` 应 100+ t/s(CPU 只有 5 t/s)

## Qwen3 思考模式(必踩坑)

- Qwen3 默认 `enable_thinking=true` → API 返回 `content` 为空、`reasoning_content` 全被思考草稿占满, 看起来像"没回答"
- 修复: **请求级** `chat_template_kwargs: {"enable_thinking": false}` 最稳
- 启动参数 `--chat-template-kwargs` 和环境变量 `LLAMA_ARG_CHAT_TEMPLATE_KWARGS` 在 git-bash 下会因引号转义失效, 别用

## sherpa-onnx 流式 ASR (1.13.x)

- 加载用 **`from_paraformer`**(不是 `from_transducer`——transducer 需要 joiner.onnx 且 paraformer 模型没有)
- API 位置: `rec.get_result(stream)` / `rec.is_endpoint(stream)` 在 **Recognizer** 上, 不在 stream 上(旧教程的 `stream.result` 已废)
- 正确喂数据循环:
  ```python
  stream.accept_waveform(48000, samples)   # 用 48kHz 录, 模型内部重采样到 16k
  while recognizer.is_ready(stream):
      recognizer.decode_stream(stream)      # 必须手动 decode! 否则不出字
  text = recognizer.get_result(stream)
  ```
- 用 16k 直喂会报 `features.cc:GetFrames` 错误; 录音用 **48kHz + callback 模式**(`s.read()` 阻塞读在某些声卡返回异常数据)
- 调试期 `enable_endpoint_detection=False` 更稳(端点检测+reset 可能误清已识别文本); 参数参考官方 `streaming-paraformer-asr-microphone.py`
- 详情见 `references/sherpa-onnx-streaming-asr.md`

## 回声循环(语音助手必踩)

- 现象: TTS 播放 → 麦克风录回 → 当成新指令 → 无限自问自答
- 修复: 播放 TTS **前 `stream.stop()` + 清队列**, 等 ffplay 播放**结束**(`subprocess.run` 阻塞等退出)再 `stream.start()` 恢复
- 播放用 `ffplay -nodisp -autoexit -loglevel quiet`(Windows 自带/已装)

## Windows 中文环境(必踩)

- **`.bat` 必须 ANSI(GBK) + CRLF**: write_file 默认 UTF-8/LF, cmd 解析会命令截断(`echo`→`cho`)、中文乱码
- 生成 bat 用 Python: `content.replace("\n","\r\n").encode("gbk")` 写文件
- bat 开头 `chcp 65001 >nul`, Python 脚本内 `sys.stdout.reconfigure(encoding="utf-8")` 双保险
- **Python 环境混乱**: 本机 `python` 命令可能指向 Hermes 的 venv, 而 pip 装的包进另一个 venv。规则: 全程用绝对路径 `/d/xibei/venv/Scripts/python.exe`, 装包用 `python -m pip install`(保证同一环境); 给用户的双击脚本也写死 venv 全路径
- 测试脚本尽量用**纯标准库**(urllib)避免 requests 等依赖在双击环境找不到

## 模型下载(国内)

- **优先 ModelScope**(39MB/s) 而非 hf-mirror(2MB/s 限速)
- hf-mirror resolve 直链可下但慢; GitHub 需代理 127.0.0.1:10808
- 大文件断流: `curl -C -` 断点续传 + for 循环重试
- 用户要求: **所有下载必须带进度条**(PowerShell `Invoke-WebRequest` 自带进度, 比 curl -s 静默好)

## 声音克隆管线(BGM 全程覆盖的视频)

1. `ffmpeg -i video.mp4 -vn -ac 1 -ar 16000 full.wav` 提音频
2. **demucs 人声分离**(BGM 覆盖全程时必须, 直接切段会把音乐学进去): `python -m demucs --two-stems=vocals -n htdemucs full.wav -o separated` → 输出 `separated/htdemucs/full/vocals.wav`
3. 按 2s 窗口 RMS 能量找说话段, 切 10~30s 连续人声
4. CosyVoice2 零样本克隆(参照音 10s 以上效果最好); 样本要求: 单人清晰说话、无笑声环境音

## 用户偏好(重要)

- 用户是小白: 给**双击式 .bat** + 每步"做什么/为什么/预期结果", 不要让他敲命令; 部署/多步骤任务**先出计划再动手**
- **杀任何进程前必须先告知并获得明确同意**(用户明确要求, 违者挨骂)
- 一次只跑一个 llama-server(多实例挤爆显存/内存导致卡死); 用户问"怎么这么多进程"时主动清理残留
- 用户不耐烦时停止自动折腾, 给交接文档(资产清单/问题诊断/避坑/从零流程)让他自己决定

## 调试速查

| 现象 | 原因 | 解法 |
|---|---|---|
| 输出纯ASCII标点乱码 | CUDA版本不对 或 ggml.dll被cudart覆盖 | 换13.x引擎; 重解压主包只拷3个cudart dll |
| content为空 reasoning有内容 | Qwen3思考模式 | 请求加 enable_thinking:false |
| ASR不出字 | 没调 decode_stream / 16k直喂 / 端点误reset | is_ready循环+decode; 48k喂; 关端点检测 |
| 语音自问自答 | 回声 | 播放TTS时暂停麦克风 |
| bat命令截断/乱码 | UTF-8+LF | GBK+CRLF, chcp 65001 |
| ModuleNotFoundError | python命令指向错误venv | 全路径调用 + python -m pip |
