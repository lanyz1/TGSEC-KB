#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bulk OCR with RapidOCR: parallel, resumable, dark-mode safe.

Usage:
  1) pip install rapidocr-onnxruntime
  2) edit BASE below (attachments live in BASE/attachments, output -> BASE/ocr_out)
  3) python3 -u ocr_rapid.py        # safe to re-run: skips existing outputs (top-up)

Notes:
- RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1) per worker is CRITICAL:
  without it every process spawns a full-core thread pool and loadavg explodes.
- Images with max side >2000px are downscaled (LANCZOS) before OCR for speed.
- Output: one JSON per image: {"file": ..., "lines": [...]}
"""
import glob
import json
import os
import time
from multiprocessing import Pool

BASE = os.environ.get("OCR_BASE", "/path/to/workdir")
ATT = BASE + "/attachments"
OUT = BASE + "/ocr_out"
EXTS = ("png", "jpg", "jpeg", "webp", "gif", "bmp")
WORKERS = 12


def work(f):
    try:
        from rapidocr_onnxruntime import RapidOCR
        from PIL import Image
        import tempfile

        ocr = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
        src = f
        try:
            im = Image.open(f)
            if max(im.size) > 2000:
                r = 2000 / max(im.size)
                im = im.convert("RGB").resize(
                    (int(im.size[0] * r), int(im.size[1] * r)), Image.LANCZOS
                )
                src = tempfile.mktemp(suffix=".png")
                im.save(src)
        except Exception:
            src = f
        res, _ = ocr(src)
        lines = [x[1] for x in (res or [])]
        b = os.path.basename(f).rsplit(".", 1)[0]
        json.dump(
            {"file": os.path.basename(f), "lines": lines},
            open(f"{OUT}/{b}.json", "w"),
            ensure_ascii=False,
        )
        return (b, len(lines), None)
    except Exception as e:
        return (os.path.basename(f), 0, str(e)[:80])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    files = []
    for f in sorted(glob.glob(ATT + "/*")):
        if f.lower().rsplit(".", 1)[-1] in EXTS:
            b = os.path.basename(f).rsplit(".", 1)[0]
            if not os.path.exists(f"{OUT}/{b}.json"):
                files.append(f)
    print("todo:", len(files), flush=True)
    t0 = time.time()
    ok = 0
    with Pool(WORKERS) as p:
        for i, (b, n, err) in enumerate(p.imap_unordered(work, files), 1):
            ok += 1
            if i % 100 == 0:
                print(f"  {i}/{len(files)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"DONE {ok} in {time.time()-t0:.0f}s")
