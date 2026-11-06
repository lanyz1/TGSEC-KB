---
name: document-categorization
description: >-
  测绘引擎·Extract documents from zip archives, read their contents across formats (PDF,
  images, text), classify them by content signature, and assign meaningful names —
  especially for Chinese-language business contexts.
owned: true
tier: general
pack: survey-skill
---

# document-categorization（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/document-categorization/`

溯源（仅标记）：`hermes/productivity`

---

# Document Categorization

Extract, read, classify, and name documents from archives. Designed for scenarios where you receive a zip of English-named files and need to assign meaningful Chinese names based on actual document content.

## Workflow

### Step 1: Extract from Zip (with CJK encoding fix)

Chinese filenames in zips are stored as CP437 bytes by most archivers — decode as GBK:

```python
import zipfile, os, shutil

with zipfile.ZipFile('archive.zip', 'r') as zf:
    for info in zf.infolist():
        raw = info.filename.encode('cp437')
        try:
            decoded = raw.decode('gbk')
        except:
            decoded = raw.decode('utf-8', errors='replace')

        out_path = os.path.join('/output/dir', decoded)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        if not decoded.endswith('/'):
            with zf.open(info.filename) as src, open(out_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)
```

**⚠️ Pitfalls:**
- **先试 UTF-8，别急着 cp437→gbk**:现代打包工具(7-Zip 默认、Telegram 文件转发等)常直接把 UTF-8 中文名写进 zip。Python `zipfile` 读出的 `info.filename` 若已能正常显示中文,直接使用;强制 `encode('cp437').decode('gbk')` 会把正常 UTF-8 名打成乱码。正确顺序:先 `repr()` 看原始字节 → 能 UTF-8 解码就用 → 乱码再回退 cp437→gbk。
- `unzip -O CP936` is NOT available on Info-ZIP < 6.1 — always fall back to Python
- After extraction, verify with `os.listdir()` — some chars may render as `\u3000` (full-width space)
- Zip entries may have trailing spaces or full-width spaces in filenames — strip or handle them

### Step 2: Read Document Content

| Format | Method | Dependency |
|--------|--------|------------|
| PDF (text-based) | `pymupdf` (fitz) | `pip install pymupdf` |
| PDF (scanned) | `marker-pdf` | ~5GB install, heavy |
| JPG/PNG | PIL pixel analysis (see below) | `Pillow` (built-in) |
| Text/TXT | `open().read()` | none |

**PDF extraction example:**
```python
import fitz
doc = fitz.open('document.pdf')
for page in doc:
    text = page.get_text()
    # Search for key phrases
doc.close()
```

### Step 3: Classify by Content Signature

Scan extracted text for **content signatures** — specific phrases that identify the document type:

| Key Phrases Found | Likely Document Type |
|---|---|
| "Articles of Incorporation", "Secretary of State", "profit corporation", "Entity ID" | **公司注册证书** (Articles of Incorporation) |
| "Certificate of Fact of Good Standing", "in good standing with this office" | **公司良好存续证明** (Certificate of Good Standing) |
| "CP575A", "Employer ID Number", "EIN", "Internal Revenue Service", "42-" (EIN pattern) | **EIN税号通知书** (IRS CP575A / EIN Assignment) |
| "Certificate of Incumbency", "secretary", "president", "officer" | **在职证明** (Certificate of Incumbency) |
| "Register of Members", "shareholder", "membership register" | **成员登记册** (Register of Members) |
| "Stock Certificate", "shares", "common stock", "certificate number" | **股票证书** (Stock Certificate) |
| "Bylaws", "Article", "Section", "corporation" in legal language | **公司章程** (Corporate Bylaws / Articles) |
| "Meeting Minutes", "resolved", "board of directors", "motion" | **会议记录** (Meeting Minutes) |
| "Corporate Secretary", "secretary card" | **公司秘书卡** (Corporate Secretary Card) |

### Step 4: Analyze Image Files (No OCR Available)

When images (JPG/PNG) lack readable text, use PIL to infer whether they are document scans or photos:

```python
from PIL import Image
img = Image.open(path).convert('RGB')
w, h = img.size

# Sample corners — white corners suggest document on scanner
corners = [
    img.getpixel((10, 10)),
    img.getpixel((w - 10, 10)),
    img.getpixel((10, h - 10)),
    img.getpixel((w - 10, h - 10)),
]
# White corner → likely a document scan
# Dark corner → likely a photo taken on a surface

# Check center region brightness
center_pixels = 0
for x in range(w // 4, 3 * w // 4, 10):
    for y in range(h // 4, 3 * h // 4, 10):
        r, g, b = img.getpixel((x, y))
        center_pixels += (r + g + b) // 3
avg_brightness = center_pixels / ((w // 2) * (h // 2) / 100)
```

**Interpretation**:
- `avg_brightness > 180` + white corners → scanned document (high confidence)
- `avg_brightness 100-180` + mixed corners → photo of a document on a surface
- `avg_brightness < 80` → likely a photo, not a document

Common image types in business packages: 注册代理人同意书, 董事身份证件/护照, 地址证明/银行账单.

### Step 5: Assign Meaningful Names

Format: `[文件类型] - [entity] - [notes].ext`
- Prefix with the Chinese document type name
- Keep original extension
- Preserve any identifying numbers (EIN, Document ID)

## Reference Files

- `references/us-company-formation-documents.md` — Content signatures for common US business formation documents

## Related Skills

- `ocr-and-documents` — Lower-level PDF/text extraction (pymupdf, marker-pdf)
- This skill adds the **classification and naming** layer on top
