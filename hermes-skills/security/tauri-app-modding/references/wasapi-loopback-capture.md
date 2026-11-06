# WASAPI Loopback Audio Capture in Rust (windows crate 0.62)

Captures whatever the system is playing (headphones, speakers, any app) — NOT the mic.
Feed the analyzed level/bass to a Tauri frontend via `app.emit(event, payload)` and let a
canvas layer react. Verified working Aug 2026 on cc-panes (Tauri 2).

## Concept

- WASAPI **loopback** mode (`AUDCLNT_STREAMFLAGS_LOOPBACK`) opens the default *render*
  (playback) device and reads the output PCM stream.
- Browsers cannot read system audio (only mic via getUserMedia) — this is why a Rust
  sidecar is needed for headphones-aware music visualization.
- Analyze in Rust: overall RMS → `level` (0..1); zero-crossing rate → `bass` (low
  frequencies = smooth waveform = low ZCR). Emit ~16 Hz (60ms).

## Cargo features (src-tauri/Cargo.toml, windows = "0.62")

```toml
"Win32_System_Com", "Win32_System_Com_StructuredStorage", "Win32_System_Variant",
"Win32_Foundation", "Win32_Media_Audio", "Win32_Media_KernelStreaming",
"Win32_Media_Multimedia", "Win32_Devices_Enumeration",
```

**`Win32_System_Variant` is mandatory** — `IMMDevice::Activate<T>` is cfg-gated on it.
Missing it = "no method named `Activate` found for struct `IMMDevice`".

## Where the constants live (counterintuitive)

| Item | Module | Notes |
|---|---|---|
| `WAVEFORMATEX` struct | `Win32::Media::Audio` | NOT KernelStreaming |
| `WAVE_FORMAT_IEEE_FLOAT` (3) | `Win32::Media::Multimedia` | |
| `WAVE_FORMAT_EXTENSIBLE` (65534) | `Win32::Media::KernelStreaming` | |
| `WAVE_FORMAT_PCM` (1) | `Win32::Media::Audio` | |
| `CoTaskMemFree` | `Win32::System::Com` (root) | NOT Com::StructuredStorage |
| `HRESULT` type | `windows::core::HRESULT` | NOT Win32::System::Com |
| `CoInitializeEx` | `Win32::System::Com` | returns raw HRESULT, NOT Result |
| `Error::from_hresult(h)` | `windows::core::Error` | convert HRESULT → Result Err |

## GUIDs (not provided as constants in 0.62 — define manually)

```rust
const CLSID_MMDEVICE_ENUMERATOR: GUID = GUID::from_u128(0xbcde0395_e52f_467c_8e3d_c4579291692e);
// IID_IAudioClient / IID_IAudioCaptureClient not needed if using typed Activate::<T>
```

## Capture sequence

```rust
// COM per-thread (background thread must init itself)
let hr = unsafe { CoInitializeEx(None, COINIT_MULTITHREADED) };
if !hr.is_ok() { return Err(windows::core::Error::from_hresult(hr)); }
// guard with Drop -> CoUninitialize

let enumerator: IMMDeviceEnumerator =
    unsafe { CoCreateInstance(&CLSID_MMDEVICE_ENUMERATOR, None, CLSCTX_ALL) }?;
let device: IMMDevice = unsafe { enumerator.GetDefaultAudioEndpoint(eRender, eMultimedia) }?;
let audio_client: IAudioClient = unsafe { device.Activate::<IAudioClient>(CLSCTX_ALL, None) }?;

// ⚠️ GetMixFormat returns *mut WAVEFORMATEX — copy the FULL struct INCLUDING the
// WAVEFORMATEXTENSIBLE extension body, or Initialize fails 0x80070057.
let mix_ptr: *mut WAVEFORMATEX = unsafe { audio_client.GetMixFormat()? };
let mix_size = 18usize + unsafe { (*mix_ptr).cbSize } as usize;   // 18 = sizeof(WAVEFORMATEX)
let format_bytes: Vec<u8> = unsafe { std::slice::from_raw_parts(mix_ptr as *const u8, mix_size) }.to_vec();
unsafe { CoTaskMemFree(Some(mix_ptr as _)) };
let format_ref = unsafe { &*(format_bytes.as_ptr() as *const WAVEFORMATEX) };  // Vec keeps alive

unsafe { audio_client.Initialize(AUDCLNT_SHAREMODE_SHARED, AUDCLNT_STREAMFLAGS_LOOPBACK, 0, 0, format_ref, None)?; }
let capture: IAudioCaptureClient = unsafe { audio_client.GetService::<IAudioCaptureClient>() }?;
unsafe { audio_client.Start()? };

// read loop: sleep 10ms -> GetNextPacketSize -> while >0: GetBuffer -> copy samples -> ReleaseBuffer
let mut packet = unsafe { capture.GetNextPacketSize() }?;
while packet > 0 {
    let mut ptr: *mut u8 = null_mut(); let mut frames = 0u32; let mut flags = 0u32;
    unsafe { capture.GetBuffer(&mut ptr, &mut frames, &mut flags, None, None) }?;
    // samples = frames * nChannels; cast per wBitsPerSample (16: i16/32768, 32: f32 or i32/2^31)
    unsafe { let _ = capture.ReleaseBuffer(frames); };
    packet = unsafe { capture.GetNextPacketSize() }?;
}
// emit every 60ms: app.emit("event-name", AudioLevelPayload { level, bass })
```

## windows-crate compile gotchas (all hit for real)

- **E0793 "reference to field of packed struct is unaligned"** — `WAVEFORMATEX` is
  `#[repr(C, packed(1))]`; you cannot take `&format.nChannels` in a `format_args!`
  (tracing::info / println). Copy fields to locals first: `let (ch, hz, bits, tag) =
  (format.nChannels, format.nSamplesPerSec, format.wBitsPerSample, format.wFormatTag);`.
- **E0382 "borrow of moved value"** — `app.emit(event, payload)` moves `payload` (serde
  Serialize by value); copy `let (level, bass) = (payload.level, payload.bass);` BEFORE
  the emit if you log afterwards.
- **E0277 `?` on HRESULT** — `CoInitializeEx` returns `HRESULT`, not `Result`; check
  `hr.is_ok()` manually (see guard above).
- **"extra operand" link failure is NOT this crate** — that's missing MSVC linker
  (GNU `link.exe` shadowing); see `windows-cli-deployment` skill.
- Real formats seen: `2 ch, 48000 Hz, 32 bits, tag=65534` (WAVE_FORMAT_EXTENSIBLE, float).

## Analysis (level + bass without FFT)

```rust
// block = 512 mono samples; per block: RMS = sqrt(sum(s²)/n) -> level = clamp(rms*20, 0, 1)
// bass proxy: zero-crossing rate. low freq = low ZCR. bass = clamp(1 - (zcr-0.005)/0.10, 0, 1)
// silence guard: if level < 0.02 { bass = 0 }  (avoid idle jitter)
```

## Frontend consumption (Tauri 2, React/TS)

```ts
import { listen } from "@tauri-apps/api/event";
listen<{ level: number; bass: number }>("event-name", (e) => {
  // smooth: audioLevel += (e.payload.level - audioLevel) * 0.35
});
// fallback chain: system loopback -> mic AnalyserNode -> free-flow (no audio)
```

## Verification without speakers

Play a beep loop in a background PowerShell while app runs, then grep app log:
```bash
powershell -NoProfile -Command "for(\$i=0;\$i -lt 20;\$i++){[console]::beep(500+\$i*40, 300); Start-Sleep -Milliseconds 500}"
```
Expect `[audio-loopback] level=0.2x bass=0.2x` in the log. (Note: run the beep via a
.ps1 file or escape `$` — bash swallows `$i` inside inline `-Command` strings.)

## Debug iteration loop

- Debug exe writes logs to stdout — run it FOREGROUND (`./target/debug/app.exe`) so
  `tracing::info!` reaches you. Running with `>/dev/null 2>&1` can panic a fern
  stderr logger ("The pipe is being closed") and crash the app.
- `cargo build -p <main-crate>` (12-30s incremental) before the full
  `npm run tauri build` (minutes) — only package when the debug run is clean.
- Add a success log after `Start()` and a throttled status log (every 30s) to confirm
  data flows; log the error in the retry loop (`capture attempt failed: {e}`) instead of
  swallowing it — the first `0x80070057` was invisible because errors were `Err(_)`.
