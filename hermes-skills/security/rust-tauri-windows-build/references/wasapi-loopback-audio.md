# WASAPI loopback system-audio capture (Rust, windows crate 0.62)

Working recipe (2026-08) for making a Tauri/Rust app react to **system playback audio**
(music through headphones — NOT the microphone). Built as `src-tauri/src/services/audio_loopback.rs`
in cc-pane to drive a reactive particle wallpaper. Standard Windows WASAPI loopback:
open the default render device with `AUDCLNT_STREAMFLAGS_LOOPBACK`, read its PCM stream.

## Cargo.toml — windows crate features (target.'cfg(windows)'.dependencies)

Must add ALL of these or you get unresolved-import / missing-method errors:
```toml
windows = { version = "0.62", features = [
    "Win32_System_Com",
    "Win32_System_Com_StructuredStorage",
    "Win32_System_Variant",            # ← IMMDevice::Activate is cfg-gated on this!
    "Win32_Media_Audio",
    "Win32_Media_KernelStreaming",     # ← WAVE_FORMAT_EXTENSIBLE lives here
    "Win32_Media_Multimedia",          # ← WAVE_FORMAT_IEEE_FLOAT lives here
    "Win32_Devices_Enumeration",
] }
```
`Win32_System_Variant` is easy to miss: `IMMDevice::Activate<T>` has
`#[cfg(all(feature = "Win32_System_Com_StructuredStorage", feature = "Win32_System_Variant"))]`.

## Module location gotchas (windows 0.62, all hit in production)

| Item | Actual path | Wrong guess that failed |
|---|---|---|
| `WAVEFORMATEX` struct | `Win32::Media::Audio` | `Win32::Media::KernelStreaming` (only the GUID constants are there) |
| `WAVE_FORMAT_IEEE_FLOAT` | `Win32::Media::Multimedia` | `Audio` / `KernelStreaming` |
| `WAVE_FORMAT_EXTENSIBLE` | `Win32::Media::KernelStreaming` | `Audio` |
| `CoTaskMemFree` | `Win32::System::Com` (root) | `Com::StructuredStorage` |
| `HRESULT` type | `windows::core::HRESULT` | `windows::Win32::System::Com::HRESULT` (doesn't exist) |
| `IMMDevice`, `IMMDeviceEnumerator`, `IAudioClient`, `IAudioCaptureClient` | `Win32::Media::Audio` | — |

## GUID constants — NOT provided by windows 0.62, define manually

The crate has the interfaces but no `CLSID_MMDeviceEnumerator` / `IID_IAudioClient` consts.
`CoCreateInstance` takes `*const GUID`, `IMMDevice::Activate<T>` uses `T::IID`, so you
only need the enumerator CLSID and the two IIDs for the fallback path:
```rust
const CLSID_MMDEVICE_ENUMERATOR: GUID = GUID::from_u128(0xbcde0395_e52f_467c_8e3d_c4579291692e);
const IID_IAUDIO_CLIENT: GUID        = GUID::from_u128(0x1cb9ad4c_dbfa_4c32_b178_c2f568a703b2);
const IID_IAUDIO_CAPTURE_CLIENT: GUID = GUID::from_u128(0xc8adbd64_e71e_48a0_a4de_185c395cd317);
```

## Core sequence

```rust
let _com = CoInitializeEx(None, COINIT_MULTITHREADED);   // returns HRESULT, NOT Result — no `?`
let enumerator: IMMDeviceEnumerator = CoCreateInstance(&CLSID_MMDEVICE_ENUMERATOR, None, CLSCTX_ALL)?;
let device: IMMDevice = enumerator.GetDefaultAudioEndpoint(eRender, eMultimedia)?;
let audio_client: IAudioClient = device.Activate::<IAudioClient>(CLSCTX_ALL, None)?;
let mix_ptr: *mut WAVEFORMATEX = audio_client.GetMixFormat()?;   // caller frees

// ⚠️ DO NOT copy just the WAVEFORMATEX header (18 bytes) — see 0x80070057 pitfall below.
// GetMixFormat returns WAVE_FORMAT_EXTENSIBLE (tag=65534) whose REAL data lives in the
// extension body (cbSize bytes) after the header. Copy ALL of it into a Vec, keep it
// alive, and pass a pointer INTO the vec to Initialize.
let mix_size = 18usize + (*mix_ptr).cbSize as usize;
let format_bytes: Vec<u8> = std::slice::from_raw_parts(mix_ptr as *const u8, mix_size).to_vec();
CoTaskMemFree(Some(mix_ptr as _));
let format_ref = unsafe { &*(format_bytes.as_ptr() as *const WAVEFORMATEX) };  // header fields valid; ext body kept alive by vec

audio_client.Initialize(AUDCLNT_SHAREMODE_SHARED, AUDCLNT_STREAMFLAGS_LOOPBACK, 0, 0, format_ref, None)?;
let capture_client: IAudioCaptureClient = audio_client.GetService::<IAudioCaptureClient>()?;
audio_client.Start()?;
// loop: GetNextPacketSize → GetBuffer(&mut ptr, &mut frames, &mut flags, None, None)
//       → read `frames * nChannels` samples per format → ReleaseBuffer(frames)
audio_client.Stop()?;
```

## Pitfalls

- **`0x80070057 E_INVALIDARG` from `Initialize` ("The parameter is incorrect")** — the #1
  runtime failure. Cause: `let format = *mix_ptr;` copies only the 18-byte
  `WAVEFORMATEX` header by value; `GetMixFormat` actually returns
  `WAVEFORMATEXTENSIBLE` (tag=65534) whose extension data (sub-format GUID, channel mask)
  lives in the body pointed to by `cbSize` — and loopback `Initialize` validates the full
  struct. Symptom in logs: capture thread retries every 5s forever with
  `capture attempt failed: The parameter is incorrect. (0x80070057)` and NEVER reaches
  `capture started`. Fix: byte-copy `18 + cbSize` bytes into a `Vec<u8>`, pass a pointer
  into the vec (see Core sequence). Verified working: `2 ch, 48000 Hz, 32 bits, tag=65534`.
- **Always log capture failures** (`Err(e) => tracing::warn!(...)`) — a silent retry loop
  hides whether the device is wedged vs. working; and log a one-line `capture started:
  {ch} ch, {hz} Hz, {bits} bits, tag={tag}` after `Start()` so you can confirm the path.
- **WAVEFORMATEX is `#[repr(C, packed(1))]`** — taking a *reference* to any field
  (e.g. inside `tracing::info!("{}", format.nChannels)`) fails with
  `E0793: reference to field of packed struct is unaligned`. Copy fields to locals first:
  `let (ch, hz, bits, tag) = (format_ref.nChannels, ...);` then format them.
- **`app.emit` MOVES the payload** — using `payload.level` after `app.emit(evt, payload)`
  is `E0382: borrow of moved value`. Copy `let (level, bass) = (payload.level, payload.bass);`
  BEFORE the emit if you log it after.
- **Status-log throttle bug**: don't measure "elapsed since last emit" from the timer you
  just reset (`last_emit.elapsed()` right after reset is always ~0 → never logs). Use a
  separate `last_status_log` Instant for the periodic `level=… bass=…` line.
- **`CoInitializeEx` returns `windows_core::HRESULT`, not `Result`** — `?` fails with
  `E0277: ? operator can only be applied to values that implement Try`. Check `hr.is_ok()`,
  build error with `windows::core::Error::from_hresult(hr)` (exists in windows-core 0.62),
  and wrap in a Drop guard that calls `CoUninitialize()`.
- **CoInitialize is per-thread** — the capture runs on its own `std::thread`; call
  CoInitializeEx there, not on the main thread.
- **WAVEFORMATEX decode**: check `format.wFormatTag as u32`:
  - `WAVE_FORMAT_IEEE_FLOAT` (3) and `WAVE_FORMAT_EXTENSIBLE` (0xFFFE): read as `f32` slices.
  - PCM 16-bit: read as `i16`, divide by 32768.0. PCM 32-bit: `i32` / 2147483648.0.
- **Silence-burst noise**: `GetNextPacketSize` can return 0 — loop until >0; each packet
  read must be followed by `ReleaseBuffer(frames)` even on decode errors.
- **Don't busy-spin**: `sleep(10ms)` per loop iteration; emit to frontend at ~16 Hz
  (60ms throttle) so the IPC channel isn't flooded.
- **Thread lifecycle**: `AtomicBool` stop flag + a 10-min session deadline so a wedged
  device eventually gets a fresh capture session; on device error sleep 5s and retry.
  Power: user may have NO playback device / loopback unsupported → whole function
  returns Err → caller must degrade gracefully (see frontend fallback chain below).

## Verification (do this BEFORE shipping)

Run the app from a terminal and grep the log:
1. Expect `[audio-loopback] capture started: 2 ch, 48000 Hz, 32 bits, tag=65534` (any
   non-zero values mean Initialize succeeded).
2. Play a sound, then expect a periodic `[audio-loopback] level=0.xx bass=0.xx` line
   (30s throttle) — non-zero level proves PCM data is actually flowing end-to-end.
   Quick test tone without a media app: `[console]::beep(880, 1000)` via a .ps1 file
   (a bash inline `powershell -Command` beep loop gets mangled by `$` eating).
3. If you see `capture attempt failed` repeatedly → the 0x80070057 fix is missing/regressed.

**Do NOT redirect the app's stdout/stderr to /dev/null when testing** (`./app.exe >/dev/null 2>&1 &`):
fern's logger panics on a closed stderr pipe → `crash.log` with `Error performing stderr
logging... The pipe is being closed. (os error 232)` and you get NO logs to inspect.
Run it in a foreground terminal (timeout-bounded) and grep the live output instead; log
files under `%LOCALAPPDATA%\com.<app>.app\logs\` exist in the release build but the panic
kills the app before they flush. Debug builds write logs to stdout — foreground is the
only reliable capture.

## Cheap bass/level analysis without FFT

Accumulate mono samples (average channels), chunk by 512:
- RMS per chunk (`sqrt(sum(s²)/n)`) → median across chunks → `level = clamp(rms_med * 20, 0, 1)`.
- Zero-crossing rate per chunk (sign changes / len) → median. Low ZCR ⇒ bass-dominated
  waveform. Map: `bass = clamp(1 - (zcr_med - 0.005)/0.10, 0, 1)`; force bass=0 when level<0.02
  so silence doesn't make particles jitter.
- Median (not mean) resists transient bursts.

## Frontend consumption (Tauri event)

Rust: `let _ = app.emit("ccpanes-audio-level", AudioLevelPayload{ level, bass });` with
`use tauri::Emitter;` — payload must be `Serialize`.

TS: dynamic import keeps the bundle lean:
```ts
let sysAudioAvailable = false, sysAudioLevel = 0, sysBassLevel = 0;
void import("@tauri-apps/api/event").then(({ listen }) =>
  listen<{ level: number; bass: number }>("ccpanes-audio-level", (e) => {
    sysAudioAvailable = true; sysAudioLevel = e.payload.level; sysBassLevel = e.payload.bass;
  }));
// in rAF loop: smooth with audioLevel += (sysAudioLevel - audioLevel) * 0.35
```
**Fallback chain (never break the UI):** WASAPI loopback → getUserMedia microphone →
free-flowing particles. Frontend checks `sysAudioAvailable` first; mic is only a fallback
now that loopback exists. Web/非-Tauri runtime: no event → mic/free path.

## Start/stop wiring in Tauri

Start in `.setup()` after services init (`#[cfg(windows)] { start_loopback_capture(handle); }`).
Keep a `static THREAD_ALIVE: AtomicBool` so start is idempotent; the module must be
`pub mod` in `services/mod.rs` (a bare `mod` triggers `E0603: module is private` when
referenced from lib.rs setup).
