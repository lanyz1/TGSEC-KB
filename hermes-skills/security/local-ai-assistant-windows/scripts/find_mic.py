# -*- coding: utf-8 -*-
"""
自动找真实麦克风: 扫描所有输入设备, 逐个录0.5s测音量, 最高的就是真麦
原因: Windows 默认输入设备可能是混音器/虚拟设备(音量<0.001), 直接录音识别为空。
用法: python find_mic.py  (或打包成双击 .bat: chcp 65001 >nul + python 全路径)
"""
import sys
import time
import numpy as np
import sounddevice as sd

for stream in (sys.stdin, sys.stdout):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

inputs = []
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0 and i > 0:  # 跳过 Sound Mapper
        inputs.append((i, d["name"]))

print(f"找到 {len(inputs)} 个输入设备, 5秒后开始逐个测音量")
print("请对着你的麦克风持续说话 (一二三四五六七八九十)")
time.sleep(4)

results = {}
for dev_id, name in inputs:
    try:
        sr = 16000
        rec = sd.rec(int(0.5 * sr), samplerate=sr, channels=1,
                     dtype="float32", device=dev_id)
        sd.wait()
        peak = float(np.max(np.abs(rec)))
        results[dev_id] = peak
        bar = "#" * int(min(peak * 300, 40))
        print(f"[{dev_id:2d}] 音量 {peak:.4f} {bar}  {name[:40]}")
    except Exception as e:
        print(f"[{dev_id:2d}] 打开失败: {str(e)[:40]}  {name[:30]}")
        results[dev_id] = 0.0

best = max(results, key=results.get) if results else None
if best is not None and results[best] > 0.005:
    print(f"\n✅ 最佳麦克风: 设备 [{best}] {sd.query_devices(best)['name']} 音量 {results[best]:.4f}")
else:
    print("\n❌ 所有设备音量极低: 检查麦克风静音 / Windows声音设置输入设备")
