# sherpa-onnx 语音链路 (流式 ASR + 唤醒词 + TTS)

## 版本 API 变化 (1.13.x)

### 模型加载 — 用 `from_paraformer`,不是 `from_transducer`

流式中文 paraformer 模型 (`csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en`) 只有 encoder/decoder/tokens,**没有 joiner**:
- ✅ `OnlineRecognizer.from_paraformer(tokens=..., encoder=..., decoder=..., num_threads, sample_rate, feature_dim, enable_endpoint_detection=True, rule1_min_trailing_silence=2.4, rule2_min_trailing_silence=1.2, rule3_min_utterance_length=300)`
- ❌ `from_transducer(...)` — 强制要 joiner,直接 TypeError

### 取结果 / 端点检测 — 在 Recognizer 上,不在 Stream 上

- ❌ `stream.result.text` (旧 API,已移除)
- ❌ `stream.is_endpoint()` (已移除)
- ✅ `rec.get_result(stream)` → 当前识别文本
- ✅ `rec.is_endpoint(stream)` → 是否到端点(静音结束)

## 唤醒词设计 (任意自定义词)

不用独立 KWS 模型(词表里没有"汐月/阿月"这类自定义词,效果差)。方案:
- 常驻跑流式 ASR (`OnlineRecognizer`,规则1尾静音2.4s)
- 对 `rec.get_result(stream)` 做**子串匹配**唤醒词
- 匹配到 → 回调进入对话模式 → 重置 stream

9800X3D 跑流式 ASR 无压力;自定义词 100% 准确。

## 录音采集 (sounddevice)

```python
import sounddevice as sd, queue, numpy as np
q = queue.Queue()
def cb(indata, frames, t, status):
    q.put(indata.copy())
stream = sd.InputStream(samplerate=16000, channels=1, dtype="int16",
                        blocksize=3200, callback=cb)  # 200ms 块
# 喂给 recognizer: samples.astype(np.float32) / 32768.0
# stream.accept_waveform(16000, samples)
```

注意 Windows 默认输入采样率可能是 44100/48000,ASR 要 16000 → 让 sounddevice 重采样(samplerate=16000 即可,声卡会转)。

## TTS 起步 (edge-tts, 免费中文)

```python
import edge_tts, asyncio
asyncio.run(edge_tts.Communicate(text, voice).save(out.mp3))
```

台湾口音参照音 (给 CosyVoice 克隆用):
- 甜妹: `zh-TW-HsiaoYuNeural`
- 高冷御姐: `zh-TW-HsiaoChenNeural`
- 播放: ffplay (`ffplay -nodisp -autoexit -loglevel quiet file.mp3`)

## 完整调用链

```
唤醒词(流式ASR子串匹配) → rec.get_result → LLM(enable_thinking:false)
→ 工具执行(可选,危险操作需语音确认) → TTS合成 → ffplay播放
```

## 依赖

`pip install sherpa-onnx sounddevice numpy edge-tts` — 装在 bat 实际调用的那个 python 里(见主 SKILL pitfall 7)。
