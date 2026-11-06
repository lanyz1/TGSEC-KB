# Voice-loop debugging & voice cloning — session detail (2026-08, 汐月 project)

## Echo feedback loop (assistant talks to itself)

Symptom in logs: after wake, `[asr] 指令:` shows the assistant's OWN TTS reply being
recognized again → she answers it → infinite loop.

Root cause: the mic keeps recording while the speaker plays the TTS audio.

Fix (in the voice engine and the TTS wrapper):
```python
def pause(self):            # on VoiceEngine
    self.stream.stop()      # stop capturing
    self._drain()           # drop queued audio (incl. her own voice)
def resume(self):
    self.stream.start()
    self._reset_stream()    # fresh ASR stream so stale text is gone

def tts_speak(text, persona, voice_engine=None):
    if voice_engine: voice_engine.pause()
    try:
        audio = tts.speak(text, persona)
        subprocess.run(["ffplay","-nodisp","-autoexit","-loglevel","quiet",audio],
                       creationflags=0x08000000)   # blocking: waits for playback end
    finally:
        if voice_engine:
            time.sleep(0.3)                        # tail silence
            voice_engine.resume()
```
Always pass `voice_engine` into every TTS call (welcome message, replies, exit message).

## Mic device selection (energy scan, not names)

`sd.default.device` can be a dead mixer. Scan script pattern:
```python
for dev_id, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] <= 0: continue
    rec = sd.rec(int(0.5*sr), samplerate=16000, channels=1, dtype="float32", device=dev_id)
    sd.wait(); peak = float(np.max(np.abs(rec)))
    print(f"[{dev_id}] peak={peak:.4f} {d['name']}")
```
User speaks during the scan; pick device with peak > 0.01. This user's working input was
`Primary Sound Capture Driver` (external sound-card mic), NOT the bluetooth speaker that
appeared in the device list. Store the chosen index in config (`mic_device: 12`).

## Streaming paraformer decode (official example)

```python
recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
    tokens=..., encoder=..., decoder=..., num_threads=1,
    sample_rate=16000, feature_dim=80, enable_endpoint_detection=True,
    rule1_min_trailing_silence=2.4, rule2_min_trailing_silence=1.2,
    rule3_min_utterance_length=300)
stream = recognizer.create_stream()
# record at 48k, accept at 48k — recognizer resamples internally
with sd.InputStream(channels=1, dtype="float32", samplerate=48000,
                    blocksize=int(0.1*48000), callback=cb, device=MIC) as s:
    while ...:
        samples = audio_q.get()[:].reshape(-1)
        stream.accept_waveform(48000, samples)
        while recognizer.is_ready(stream):
            recognizer.decode_stream(stream)
        text = recognizer.get_result(stream).strip()
        is_end = recognizer.is_endpoint(stream)
```
Mistakes that produced empty/garbage results (each cost a debug cycle):
- feeding 16k-int16 samples as if 16k when the hardware actually captured 48k → "嗯"-style one-char results
- `accept_waveform` without the `is_ready`/`decode_stream` loop → `GetFrames: 0 + 61 > 19` assertion, empty result
- blocking `s.read()` InputStream on this sound card returned silence; callback-based InputStream worked
- endpoint-detection + `reset()` mid-utterance can wipe a 5s command → for fixed-duration test scripts use `enable_endpoint_detection=False`

## Wake words with homophones

Custom Chinese names get transcribed as homophones by ASR. 汐月 came back as 七月/西月.
Wake list must include variants:
```yaml
xiyue: ["汐月","阿月","小月","月月","七月","西月","惜月","希月","晓月","萧月"]
jarvis: ["贾维斯","佳维斯","假维斯","家维斯","贾维斯先生","jarvis"]
```
Test matcher with a hit/miss table (8/8 expected) before wiring audio.

## Voice cloning from video (CosyVoice2 path)

Source acquisition: Douyin auto-download blocked (yt-dlp needs fresh cookies; headless
browser blob download does not persist). Ask user to save locally and provide the path
(their file landed at `C:\Users\Administrator\.hermes\desktop-attachments\<hash>.mp4`).

Separation when BGM spans the whole clip:
```
ffmpeg -y -i in.mp4 -vn -ac 1 -ar 16000 full.wav
python -m demucs --two-stems=vocals -n htdemucs full.wav -o separated
# -> separated/htdemucs/full/vocals.wav  (clean speech)
```
Then: energy-scan vocals.wav, cut candidate 10–30s segments, have the USER listen and pick
the clearest (they will, given numbered samples — same UX as voice tuning), then clone with
CosyVoice2 offline zero-shot. Install demucs with `python -m pip install demucs`
(pitfall: bare `pip` may install into a different interpreter than `python`).

## CosyVoice2 clone — exact execution (verified 2026-08)

Setup (CN network):
- `pip install cosyvoice` gives only an API shell — the real inference code is the GitHub repo:
  `git clone --depth 1 https://github.com/FunAudioLLM/CosyVoice.git`
- Model from ModelScope (fast in CN): `modelscope.hub.snapshot_download` with `local_dir` —
  the `-m modelscope download` CLI may not exist on old versions; use the Python API:
  ```python
  from modelscope.hub.snapshot_download import snapshot_download
  snapshot_download('iic/CosyVoice2-0.5B', local_dir=r'D:\...\CosyVoice2-0.5B')
  ```
  ~4.3GB, 21 files; llm.pt (~2GB) downloads last and shows as `llm.pt.incomplete` until done.
- Install deps into the CLEAN venv (see SKILL.md pitfalls 16–18): torch/torchaudio/transformers/
  tokenizers==0.23.0/hyperpyyaml/onnxruntime. `torch` is the hang-prone one — curl the wheel
  from TUNA (`torch-2.11.0-cp312-cp312-win_amd64.whl`, ~2.7GB) instead of pip-resolving it.
- Runtime requirements that bite: `import torchaudio` (missing → install), transformers↔tokenizers
  version pin (`tokenizers>=0.22.0,<=0.23.0`; 0.23.1 fails the check — force `==0.23.0`).

Inference (zero-shot, ~10s clean reference audio):
```python
import sys; sys.path.insert(0, r'...\CosyVoice')
sys.path.append(r'...\CosyVoice\third_party\Matcha-TTS')
from cosyvoice.cli.cosyvoice import AutoModel
import torchaudio
cv = AutoModel(model_dir=r'...\CosyVoice2-0.5B')   # ~1-2min load on CPU torch
for i, out in enumerate(cv.inference_zero_shot(
        '阿荣，你终于回来啦。',        # text to synthesize
        '',                           # prompt text (empty OK for zero-shot)
        r'...\speech_50_10s.wav',     # reference voice clip
        stream=False)):
    torchaudio.save(f'out_{i}.wav', out['tts_speech'], cv.sample_rate)
```
Note: `pip install` into the Hermes-derived venv lands packages in Hermes' site-packages —
imports still work from `D:\xibei\venv\Scripts\python.exe` ONLY if PYTHONPATH is cleared;
a fresh system-python venv (`C:\Users\...\Python312\python.exe -m venv`) avoids the whole class.

## Process hygiene during playback tests

ffplay with `-autoexit` can still leave a zombie window/process; when the user says
"还在播放", sweep with:
```
powershell -NoProfile -Command 'Get-Process ffplay -ErrorAction SilentlyContinue | Stop-Process -Force'
```
and re-check (`if (Get-Process ffplay ...) {"STILL"} else {"ALL CLEAR"}`) — one pass may
not catch all; loop until clear.
