# sherpa-onnx 流式 ASR 详细笔记 (1.13.x, Windows)

## 模型选择

- 流式中文识别: `csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en`(HF)
- 文件: `encoder.onnx`(~607MB) + `decoder.onnx`(~218MB) + `tokens.txt`
- 仓库**没有** joiner.onnx / model.onnx → 必须用 `from_paraformer` 加载
- 下载: hf-mirror resolve 直链可下但限速; 也可试 ModelScope 镜像

## 加载 (关键: 不是 from_transducer!)

```python
import sherpa_onnx
rec = sherpa_onnx.OnlineRecognizer.from_paraformer(
    tokens="tokens.txt",
    encoder="encoder.onnx",
    decoder="decoder.onnx",
    num_threads=1,              # 官方示例用 1, 不要 4
    sample_rate=16000,          # 模型内部采样率
    feature_dim=80,
    enable_endpoint_detection=True,   # 调试期可改 False
    rule1_min_trailing_silence=2.4,
    rule2_min_trailing_silence=1.2,
    rule3_min_utterance_length=300,
)
```

## API 位置 (1.13.x 与旧教程不同)

| 操作 | 正确位置 | 错误写法(旧教程) |
|---|---|---|
| 取识别结果 | `rec.get_result(stream)` | `stream.result.text` ✗ |
| 端点检测 | `rec.is_endpoint(stream)` | `stream.is_endpoint()` ✗ |
| 解码推进 | `rec.decode_stream(stream)` | 无 |
| 是否可解码 | `rec.is_ready(stream)` | 无 |
| 创建流 | `rec.create_stream()` | 同 |
| 喂音频 | `stream.accept_waveform(sr, samples)` | 同 |

## 正确喂数据循环 (必须 decode! 否则不出字)

```python
# 录音用 48kHz (模型内部重采样到 16k), 100ms 一块
sample_rate = 48000
samples_per_read = int(0.1 * sample_rate)
stream = rec.create_stream()

with sd.InputStream(channels=1, dtype="float32",
                    samplerate=sample_rate, device=MIC_DEVICE) as s:
    while running:
        samples, _ = s.read(samples_per_read)   # 或用 callback+queue 模式
        samples = samples.reshape(-1)
        stream.accept_waveform(sample_rate, samples)   # 传 48000!
        while rec.is_ready(stream):
            rec.decode_stream(stream)                   # 关键!
        text = rec.get_result(stream)
        if rec.is_endpoint(stream):
            # 一句话结束
            rec.reset(stream)
```

## 高频坑

1. **用 16k 直喂** → `features.cc:GetFrames: N + M > K` 断言错误。必须传 48k(或模型支持的其他率), 让 sherpa 内部重采样。官方示例用 48k 就是为了演示这一点。
2. **不调 decode_stream** → 麦克风音量正常但结果永远为空。
3. **端点检测 + reset 误清**: 说话中停顿会被判为"说完了"然后 reset 清空已识别文本。调试期 `enable_endpoint_detection=False` + 固定时长录音最稳。
4. **默认录音设备可能是混音器/静音**: Windows 默认输入设备 (sd.default.device[0]) 可能是 "Recording Mixer" 或虚拟设备, 音量 <0.001。必须写脚本扫描所有输入设备找真实麦克风:
   ```python
   for i, d in enumerate(sd.query_devices()):
       if d['max_input_channels'] > 0 and i > 0:
           # 逐个录 0.5s 测峰值音量, 最高的就是真麦
   ```
5. **`s.read()` 阻塞读 vs callback**: 某些声卡上 `s.read()` 返回的数据异常(识别为空), 但 callback+queue 模式正常。不确定时用 callback 模式。
6. **唤醒词**: 流式 ASR 常驻 + 文本匹配最灵活, 自定义中文词(汐月/阿月)同音字变体都要加(七月/西月/晓月...), 否则口语识别出来对不上。
7. 模型会打印 `Creating a resampler: in 48000 out 16000` 是正常日志, 不是错误。

## 参考

官方示例: `k2-fsa/sherpa-onnx` repo → `python-api-examples/streaming-paraformer-asr-microphone.py`
