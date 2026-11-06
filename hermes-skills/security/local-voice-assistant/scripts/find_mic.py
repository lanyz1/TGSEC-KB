# -*- coding: utf-8 -*-
"""
find_mic.py — scan all audio input devices and rank by captured peak volume.
Use when a voice assistant hears nothing: the default input device is often a
bus mixer (Recording Mixer) with near-zero signal, and device NAMES lie
(e.g. "耳机式麦克风 (LP90 Pro)" was actually a Bluetooth SPEAKER).

Procedure: record ~0.5s from every input device, print peak volume bars,
declare the loudest as the real mic. Bake the winning index into config
(e.g. `mic_device: 12`) and pass `device=` to sounddevice.InputStream.

Usage:
    python find_mic.py
    (then talk into the mic continuously while it scans ~10-15s)
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

# Collect all input devices (skip index 0 = Sound Mapper alias)
inputs = []
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0 and i > 0:
        inputs.append((i, d["name"]))

print("=" * 55)
print("Find microphone: %d input devices found" % len(inputs))
print("Scan starts in 4s — talk into your mic continuously")
print("(e.g. count 1..10 out loud)")
print("=" * 55)
time.sleep(4)
print("Scanning... keep talking!")

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
        print("[%2d] peak %.4f %s  %s" % (dev_id, peak, bar, name[:40]))
    except Exception as e:
        print("[%2d] open failed: %s  %s" % (dev_id, str(e)[:40], name[:30]))
        results[dev_id] = 0.0

print()
print("=" * 55)
best = max(results, key=results.get) if results else None
if best is not None and results[best] > 0.005:
    print("BEST mic: device [%d] %s" % (best, sd.query_devices(best)["name"]))
    print("peak: %.4f" % results[best])
else:
    print("ALL devices near-silent — check mute / Windows input device")
print("=" * 55)
