---
name: video-localization
description: >-
  测绘引擎·Use when 把短视频翻录成外语版(英文等)——外语配音+烧录字幕替换+保留BGM. 全流程8步+ffmpeg坑位.
owned: true
tier: general
pack: survey-skill
---

# video-localization（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/video-localization/`

溯源（仅标记）：`hermes/media`

---

# 视频翻录(外语配音+字幕替换)流水线

用户常见诉求: 把中文短视频(口播+烧录字幕+背景音乐)做成英文版。流程已验证(2026-08, 55s竖屏情感口播视频为例)。

## 触发条件
- "做英文版视频 / 翻录成英文 / 配音+字幕替换"
- 用户要"教程"同时要成品 → 两条线都交付: 成品视频 + 教程md + 对话稿(用户翻录用)

## 核心原则
- **音频转录优先于逐帧抠屏**(用户明确纠正过): 旁白语音=屏幕对话内容, 直接 whisper 转录拿文字, 不要一帧帧 OCR 设备屏幕。只有旁白没念的屏幕文字才需要补读帧。
- **画面字幕是浓缩版, 旁白是完整版**: 两套都要提取。字幕=屏幕上烧录的短句(每条~5s), 旁白=念出来的完整故事(可多出 2-3 倍内容)。英文配音用旁白, 英文画面字幕用浓缩版, 还原原片设计。
- 交付物放桌面 + 中间素材留工作目录, 每步验证。

## 流水线(8步)

### 1. 分析视频
```bash
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_type,codec_name,width,height -of json 视频.mp4
```

### 2. 提取音频 + 转录
```bash
ffmpeg -y -i 视频.mp4 -vn -ac 1 -ar 16000 audio.wav
whisper audio.wav --model small --language zh --output_format txt --output_dir .
# 旁白可能被 whisper 分段跳过(音乐掩盖), 把 gap 区间单独切片再转录:
ffmpeg -ss 2.9 -to 30.2 -i audio.wav -ac 1 -ar 16000 mid.wav
```
- whisper small 模型首次下载 461MB, 速度慢 → 后台 `curl -C - -o small.pt <url>` 断点续传(wget 在 git-bash 不存在)
- 转录含 word_timestamps 拿精确时间轴

### 3. 翻译脚本
- 旁白翻成口语化英文短句, 保留情感递进(问句→回忆→高潮→落点)
- 画面字幕单行 ≤50 字符; 英文比中文啰嗦 ~1.8x, 长句要精简或调语速

### 4. TTS 配音(edge-tts)
```bash
pip install edge-tts
edge-tts --voice en-US-JennyNeural --rate=-10% --text "..." --write-media line_01.mp3
```
- 温柔女声: en-US-JennyNeural / MichelleNeural; 英音: en-GB-SoniaNeural
- **必须裁掉句尾静音**再对时间轴, 否则叠加越拖越乱:
```bash
ffmpeg -i in.mp3 -af "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,apad=pad_dur=0.06" out.wav
```
- rate 参数影响小(-10% 实际只省 ~10%), 主要靠精简文本+裁静音

### 5. 人声分离保 BGM(demucs)
```bash
pip install demucs
demucs --two-stems=vocals -o stems audio.wav   # 出 no_vocals.wav + vocals.wav
```
- 输出在 stems/htdemucs/audio/; demucs 输出会 pad 到整秒(~58.5s), 混音时 atrim

### 6. 字幕遮罩条(Pillow 生成透明 PNG)
- 烧录中文字幕用**不透明(alpha≥230)深色圆角条**盖住 + 白色英文居中。alpha 165 会让中文透出来(实测返工)
- 字体: C:\Windows\Fonts\seguisb.ttf (Segoe UI Semibold); 字号自动缩到适配 ≤830px
- 条位置用像素分析测, 别信 vision 模型给的坐标(会幻觉)
- 脚本: scripts/find_subtitle_band.py + scripts/make_subtitle_overlays.py

### 7. 混音(ffmpeg)
见 references/ffmpeg-recipes.md 的完整 filter_complex。关键坑:
- **⚠️ ffmpeg 8.x: `afade` 必须放 `adelay` 前面!** `adelay,afade` 顺序会让 fade-out 把整段音频静音(实测: 只听到前两句, 后面全消失; 逐层隔离才定位)。正确顺序: `afade=...,adelay=...`
- 每句配音 adelay=start_ms|start_ms 定位, amix inputs=N:normalize=0
- 响度对齐原片: `volumedetect` **必须用 `-v info`**(`-v error` 看不到输出), 差多少 dB 补 `volume=XdB` + `alimiter=limit=0.92`

### 8. 合成导出
- 11 张 overlay PNG 按时间窗 `overlay=0:0:enable='between(t,s,e)'` 链式叠加
- `-c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart`
- 音轨返工只需重混音 + `-c:v copy` 重封装, 不用重渲染画面

## 验证清单
1. 抽 6 个时间点帧, 视觉确认字幕内容/时机/居中/中文盖住
2. whisper 转最终成品音频, 确认全部配音在场且时间轴对
3. volumedetect 响度 ≈ 原片(±2dB)
4. ffprobe 时长 = 原片

## 本机环境坑(2026-08 实测)
- **全局 PYTHONPATH 指向 hermes venv**, 会污染 Python312 等其它解释器的导入(报错特征: 包从 hermes-agent\venv\Lib\site-packages 加载失败)。**调用其它 Python 一律前缀 `PYTHONPATH=` 清空**; pip list 也会被污染显示假包
- 版本矩阵: torch 2.11 需 numpy≥2.0; whisper 需 numba; numba 0.58.1 无 cp312 wheel(0.59.1 起有)。可用组合: numpy 2.5.2 + numba 0.67.0 + torch 2.11
- faster-whisper 若从 hermes venv 加载会因 ctranslate2 版本冲突报 `AttributeError: StorageView`

## 用户偏好
- 成品视频 + 教程 md + A/B 对话稿(中英对照, 标注说话人) 都要给
- 对话稿用于用户在真实设备上翻录 → 只给英文版对话时存 txt, 带 A/B 标注
- 教程文档放桌面, 用户要能照着复刻下一个视频

## 支持文件
- scripts/find_subtitle_band.py — 测烧录字幕位置(y 行带)+换行时机(白色像素量骤降, 处理 typewriter 逐字效果)
- scripts/make_subtitle_overlays.py — Pillow 生成圆角遮罩条+英文白字 PNG
- references/ffmpeg-recipes.md — 完整混音/导出命令、afade bug 复现与修复、响度对齐
