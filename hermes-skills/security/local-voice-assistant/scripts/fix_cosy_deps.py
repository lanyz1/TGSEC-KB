# -*- coding: utf-8 -*-
"""
CosyVoice dependency auto-loop: import AutoModel AND load the model, catching
each missing module (bare ModuleNotFoundError AND pydoc.ErrorDuringImport
wrapped exceptions), pip-install it, retry. requirements.txt pins old builds
that fail to compile on Python 3.12 (grpcio==1.57.0, conformer==0.3.2,
diffusers==0.29.0) — use this instead.

Two-stage loop is REQUIRED: deps surface at import time (openai-whisper,
inflect, omegaconf, scipy, conformer, diffusers) AND at MODEL-LOAD time via
hyperpyyaml pydoc.locate (e.g. wget), where the error arrives as
`pydoc.ErrorDuringImport: problem in cosyvoice.flow.flow_matching -
ModuleNotFoundError: No module named 'wget'` — NOT a bare ModuleNotFoundError.
So catch broad Exception and regex the module name out of the message.

Verified 2026-08 on Windows py3.12: full dep chain = openai-whisper, inflect,
omegaconf, scipy, conformer, diffusers, wget; model load ends with
`Loading weights: 100%|...| 290/290` + `模型加载成功!`.

USAGE (must clear the box's OS-level PYTHONPATH first):
  set PYTHONPATH=& set PYTHONHOME=& "C:\\...\\Python312\\python.exe" fix_cosy_deps.py
  # or in bash:  env -u PYTHONPATH -u PYTHONHOME <venv>/Scripts/python.exe fix_cosy_deps.py

Edit COSYVOICE_REPO / MODEL_DIR to match your machine.
"""
import subprocess
import sys
import re

COSYVOICE_REPO = r"D:\xibei\data\clone\CosyVoice"
MODEL_DIR = r"D:\xibei\data\clone\CosyVoice2-0.5B"
sys.path.insert(0, COSYVOICE_REPO)
sys.path.append(COSYVOICE_REPO + r"\third_party\Matcha-TTS")

# The interpreter that must end up with all the deps (system Python is safest:
# venvs derived from Hermes's venv import Hermes's site-packages).
PYTHON_EXE = sys.executable
PIP_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"

tried = set()


def extract_missing(err_text):
    m = re.search(r"No module named '([^']+)'", err_text)
    return m.group(1).split(".")[0] if m else None


for attempt in range(1, 40):
    try:
        from cosyvoice.cli.cosyvoice import AutoModel  # noqa: F401
        print(f"[OK] AutoModel imported (round {attempt}) — loading model...")
        # Stage 2: model load surfaces yaml-resolved deps (wget etc.)
        cosyvoice = AutoModel(model_dir=MODEL_DIR)
        print("[OK] Model loaded — all deps satisfied")
        break
    except Exception as e:  # ModuleNotFoundError AND pydoc.ErrorDuringImport
        mod = extract_missing(str(e))
        if not mod:
            print(f"Cannot parse error: {type(e).__name__}: {e}")
            break
        if mod in tried:
            print(f"Repeated missing module: {mod} — stopping")
            break
        tried.add(mod)
        print(f"[{attempt}] missing {mod}, installing...")
        r = subprocess.run(
            [PYTHON_EXE, "-m", "pip", "install", "-q", "-i", PIP_MIRROR, mod],
            capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print(f"  install {mod} FAILED: {r.stderr[-300:]}")
            break
        print(f"  {mod} installed")
else:
    print("More than 40 rounds — stopping")

print("Installed:", tried)
