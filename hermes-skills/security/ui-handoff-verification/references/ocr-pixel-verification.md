# OCR + pixel verification of UI screenshots (no vision tool available)

Environment: Python 3.11 + `rapidocr-onnxruntime` (`pip install rapidocr-onnxruntime onnxruntime`). PIL for pixel math.

## 1. Extract baseline strings (source of truth)
```python
import re, io
html = io.open('baseline.html', encoding='utf-8').read()
i = html.find('<section class="view" id="view-login"'); j = html.find('</section>', i)
texts = [t.strip() for t in re.findall(r'>([^<>]{2,80})<', html[i:j]) if t.strip()]
```
Note: this also surfaces baseline copy bugs (glue like `AccountorPasswordError`) — fix the baseline too, but still judge the agent against it.

## 2. OCR the agent's screenshot
```python
from rapidocr_onnxruntime import RapidOCR
result, _ = RapidOCR()(screenshot_path)
for line in result: print(line[1], round(line[2],2))   # text, confidence
```
Treat confidence < 0.8 as uncertain — confirm with pixel checks or a re-crop.

## 3. Layout checks with PIL (catches what OCR can't)
```python
from PIL import Image
im = Image.open(p).convert('RGB'); w,h = im.size
def avg(box):
    px = list(im.crop(box).getdata()); n = len(px)
    return tuple(sum(p[i] for p in px)//n for i in range(3))
print(avg((0,0,w//2,h)), avg((w//2,0,w,h)))          # left vs right half
dark = sum(1 for p in im.getdata() if max(p) < 50) / (w*h)
print(f"dark%: {dark*100:.1f}")
```
Calibration from a real case: baseline login with a `#000` left brand panel ≈ 45% dark pixels; agent's panel-less form ≈ 5.5%.

## 4. Caveats
- Partial screenshots mislead: a 620px crop of a 2-column layout looks like the brand panel is missing. Demand full-page screenshots; pair OCR with region color sampling.
- OCR reads browser chrome too (tab titles, bookmarks) — filter lines that are clearly browser UI.

## 5. Verdict table
| element | baseline (verbatim) | agent (OCR) | verdict |
Invented copy absent from baseline = agent's fault, proof by exact string. Layout-frame-only fixes with invented copy left in place are the most common failure (observed twice in a row).
