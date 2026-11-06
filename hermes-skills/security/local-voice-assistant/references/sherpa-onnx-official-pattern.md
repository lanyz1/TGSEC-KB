# sherpa-onnx Official Streaming Paraformer Microphone Pattern

Source: `k2-fsa/sherpa-onnx` repo, file `python-api-examples/streaming-paraformer-asr-microphone.py` (fetch from raw.githubusercontent.com when needed — don't guess API usage).

## Verified working skeleton (sherpa-onnx 1.13.4, Windows)

```python
import os, time
import numpy as np
import sounddevice as sd
import sherpa_onnx

# Load streaming paraformer (NOT from_transducer — no joiner file for this repo)
recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
    tokens=os.path.join(asr_dir, "tokens.txt"),
    encoder=os.path.join(asr_dir, "encoder.onnx"),
    decoder=os.path.join(asr_dir, "decoder.onnx"),
    num_threads=1,
    sample_rate=16000,
    feature_dim=80,
    enable_endpoint_detection=True,
    rule1_min_trailing_silence=2.4,
    rule2_min_trailing_silence=1.2,
    rule3_min_utterance_length=300,   # effectively disables this rule
)

stream = recognizer.create_stream()

# KEY: record at 48kHz, sherpa resamples to 16k internally
sample_rate = 48000
samples_per_read = int(0.1 * sample_rate)   # 100 ms blocking read

with sd.InputStream(channels=1, dtype="float32", samplerate=sample_rate, device=MIC_IDX) as s:
    while True:
        samples, _ = s.read(samples_per_read)      # blocking
        samples = samples.reshape(-1)
        stream.accept_waveform(sample_rate, samples)

        # KEY: is_ready loop, NOT unconditional decode
        while recognizer.is_ready(stream):
            recognizer.decode_stream(stream)

        is_endpoint = recognizer.is_endpoint(stream)
        result = recognizer.get_result(stream)
        print(result, end="\r", flush=True)

        if is_endpoint:
            recognizer.reset(stream)
```

## The three API traps this solves

1. `from_paraformer` not `from_transducer` (transducer needs `joiner` — 404 on this repo).
2. `get_result(stream)` / `is_endpoint(stream)` live on the RECOGNIZER, not the stream (1.13.4 removed stream.result / stream.is_endpoint()).
3. `decode_stream` driven by `is_ready` loop + 48kHz capture → no more `GetFrames: 0 + N > M` assertions.

## Why 48kHz

The official example deliberately captures at 48kHz "to demonstrate that sherpa-onnx will do resampling inside". Raw 16kHz blocks of arbitrary size break the streaming encoder's chunk bookkeeping. dtype must be `float32` for this path.
