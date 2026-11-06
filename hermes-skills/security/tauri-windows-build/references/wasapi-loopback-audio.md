# WASAPI Loopback 系统音频捕获（Rust + windows crate 0.62）

目标：捕获**系统播放输出**（不碰麦克风），让桌面应用随任意应用出声律动。浏览器只能 `getUserMedia` 读麦克风，戴耳机时拾不到音乐 → 必须 Rust 侧 WASAPI loopback。

## Cargo features（容易漏）

`Win32_System_Com`、`Win32_System_Com_StructuredStorage`、`Win32_System_Variant`（**IMMDevice::Activate 需要它**）、`Win32_Media_Audio`、`Win32_Media_KernelStreaming`、`Win32_Media_Multimedia`。

## 核心调用链

```rust
// 手动定义（crate 无此常量）
const CLSID_MMDEVICE_ENUMERATOR: GUID = GUID::from_u128(0xbcde0395_e52f_467c_8e3d_c4579291692e);

CoInitializeEx(None, COINIT_MULTITHREADED)  // 返回 HRESULT 不是 Result！手动检查
CoCreateInstance(&CLSID_MMDEVICE_ENUMERATOR, None, CLSCTX_ALL)  // -> IMMDeviceEnumerator
enumerator.GetDefaultAudioEndpoint(eRender, eMultimedia)          // -> IMMDevice（默认播放设备）
device.Activate::<IAudioClient>(CLSCTX_ALL, None)                 // -> IAudioClient
audio_client.GetMixFormat()?                                      // -> *mut WAVEFORMATEX
audio_client.Initialize(AUDCLNT_SHAREMODE_SHARED, AUDCLNT_STREAMFLAGS_LOOPBACK, 0, 0, fmt, None)
audio_client.GetService::<IAudioCaptureClient>()?                 // -> IAudioCaptureClient
audio_client.Start()?
// 循环：GetNextPacketSize / GetBuffer(&mut data, &mut frames, &mut flags, None, None) / ReleaseBuffer(frames)
```

## 已踩的坑（都修过）

1. **`0x80070057 The parameter is incorrect`**：只拷贝 18 字节 WAVEFORMATEX 头部，丢掉 WAVEFORMATEXTENSIBLE 扩展体（cbSize>0）→ Initialize 失败。修复：按 `18 + (*mix_ptr).cbSize` 拷贝完整字节到 Vec 保活，把 Vec 指针传给 Initialize。
2. **CoInitializeEx 返回 `HRESULT` 非 `Result`**，`?` 编译不过。手动 `hr.is_ok()` 检查 + `Error::from_hresult(hr)` + Drop guard 里 CoUninitialize。
3. **`CoTaskMemFree` 在 `Win32::System::Com` 根模块**（不是 StructuredStorage 子模块）。
4. **WAVEFORMATEX 是 `packed(1)` 结构**，不能取字段引用（E0793）——打日志前先把字段拷成本地变量。
5. **常量位置分散**：`WAVE_FORMAT_IEEE_FLOAT` 在 Multimedia、`WAVE_FORMAT_EXTENSIBLE` 在 KernelStreaming、`WAVE_FORMAT_PCM` 在 Audio。且都是 u32，`wFormatTag` 是 u16，match 时 `as u32`。
6. **线程安全**：每个线程必须自己 CoInitialize；后台线程捕获，`AtomicBool` 做 stop 标志；会话 10 分钟超时重拉（设备热插拔保活）；失败 5s 重试 + warn 日志（别静默吞错，否则排查靠猜）。
7. **emit 节流**：60ms 一次（16Hz 够顺滑）；状态日志用独立 Instant 节流（30s），别复用 emit 计时器。

## 频谱分析（无需 FFT）

- 多声道取平均成 mono，512 样本分块，块内 RMS；取**中位数**抗突发噪音
- `level = clamp(mid_rms * 20, 0..1)`（0.05 RMS ≈ 很响）
- 低频占比用**过零率**近似：过零率低 = 波形平滑 = 低频。zcr 0.02→bass≈1，0.12→bass≈0；静音（level<0.02）时 bass 强制归零
- emit `{ level: f32, bass: f32 }`，前端 `listen("ccpanes-audio-level", ...)` 平滑跟进（lerp 0.35）

## 验证方法

- 启动成功后打日志：`capture started: 2 ch, 48000 Hz, 32 bits, tag=65534`（tag 65534=EXTENSIBLE）
- 每 30s 打 `level=.. bass=..`；用 `powershell [console]::beep(...)` 制造系统音，期望 level>0
- 快速验证用 debug 构建前台跑：`timeout 45 ./cc-panes.exe 2>&1 | grep audio-loopback`（**别用 `>/dev/null 2>&1` 后台跑——fern 日志器对关闭的 stderr 会 panic**）
- debug 版数据在 `~/.cc-panes-dev/`，release 在 `~/.cc-panes/`，日志路径别搞混
