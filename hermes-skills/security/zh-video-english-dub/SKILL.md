---
name: zh-video-english-dub
description: >-
  测绘引擎·Use when 中文短视频转英文版. whisper转录+edge-tts配音+demucs分离+ffmpeg合成.
owned: true
tier: general
pack: survey-skill
---

# zh-video-english-dub（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/zh-video-english-dub/`

溯源（仅标记）：`hermes/media`

---

# 中文短视频 → 英文版 (配音+字幕+保BGM)

## When to Use
用户要把中文短视频做成英文版(英文配音/英文字幕/保留BGM/时长一致),或要提取视频内A/B对话台词稿时使用。典型:口播+字幕类竖屏短视频,如AI情感陪伴视频(路遥AI风)。

针对竖屏口播/字幕类短视频(如AI情感陪伴视频"路遥AI"风),产出同时长英文版。
参考成品: `Downloads\eng_video_work\` (完整工作目录示例)。

## 环境避坑(本机 Windows)
- 全局 `PYTHONPATH` 指向 hermes venv,会污染 Python312 导入 → 每条 python 命令前加 `PYTHONPATH=` 前缀
- Python312 (3.12.10): 需 numpy≥2.0 + numba 配套 (实测 numpy 2.5.2 + numba 0.67.0 + torch 2.11 可用; torch 2.11 必须 numpy≥2,否则 whisper/demucs 报 "Numpy is not available")
- whisper 模型 `small.pt`(461MB) 缓存于 `~/.cache/whisper/`,下载用 `curl -L -C - -o small.pt <url>` 断点续传(无 wget)
- numba<0.59 无 py3.12 wheel;旧 numba(0.66)配 numpy1.26 会挂 → 版本组合要对

## 步骤
1. **分析**: `ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_type,codec_name,width,height -of json 视频.mp4`
2. **提取音频**: `ffmpeg -y -i 视频.mp4 -vn -ac 1 -ar 16000 audio.wav`
3. **转录拿台词+时间轴**: `whisper audio.wav --model small --language zh`(word_timestamps=True 存 json)。注意:
   - 画面字幕=浓缩版,旁白=完整版,两份内容不同,都要提取
   - whisper 可能漏检中段 → 分段 `-ss/-to` 切片单独转录补齐(如 2.9-30.2s 空档)
4. **字幕切换时间检测**(typewriter 逐字出现时): fps=2 抽帧 → 裁字幕行带(crop=680:46:200:714 类) → 白色像素量骤降点=换行时刻(字幕带里混有手部动作,别用整帧diff)
5. **TTS 配音**: `pip install edge-tts`; `edge-tts --voice en-US-JennyNeural --rate=-10% --text "..." --write-media x.mp3` (温柔女声 Jenny/Michelle,英音 Sonia)
   - ⚠️ edge-tts 每句尾部自带 0.2-0.5s 静音 → 必须裁: `silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,apad=pad_dur=0.06`
   - 英文比中文话多,按原旁白段落分组对齐起点,超窗则精简文本+加速率
6. **人声/音乐分离**: `pip install demucs`; `demucs --two-stems=vocals -o stems audio.wav` → `stems/htdemucs/audio/no_vocals.wav`(BGM)
7. **字幕遮罩条**(Pillow 生成 1080x1920 透明 PNG): 圆角矩形 alpha≥235(必须盖死中文,165 会透出),白字 Segoe UI Semibold(`C:\Windows\Fonts\seguisb.ttf`)自动缩字号;字幕行位置用白色像素行检测(竖屏类在 y≈717-756,条盖 y=700-775)
8. **混音** (ffmpeg): 每条 `afade=t=in/out → adelay` → `amix=inputs=N:normalize=0` + `atrim`
   - ⚠️⚠️ **ffmpeg 8.x: `afade` 必须在 `adelay` 之前!** 顺序 `adelay,afade` 会静音整段(实测 fade-out 毁整条)
   - 响度对齐原片: `ffmpeg -v info ... -af volumedetect`(必须 -v info,error 会吞输出)对比 mean_volume,差多少补 `volume=XdB`,再 `alimiter=limit=0.92` 防削波
9. **合成**: 原视频 + 各遮罩PNG `overlay=0:0:enable='between(t,start,end)'` 链式叠加 → `-c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart`

## 验证(必做)
- [ ] 抽 6 个时间点帧,字幕内容/时机正确、中文被盖死
- [ ] whisper 转最终音频,英文配音全覆盖且时间轴对
- [ ] volumedetect 响度≈原片(±2dB)
- [ ] 时长=原片±0.5s

## 台词交付(用户要对话稿时)
- 直接转录语音即可(用户明确偏好:勿逐帧抠屏幕)
- 交付 A/B 对话稿:中英对照+说话人标注(旁白是AI独白,要还原"用户问→AI答"结构),或纯英文 txt
