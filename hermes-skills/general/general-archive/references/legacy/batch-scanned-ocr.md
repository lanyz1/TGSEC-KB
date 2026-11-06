<!-- archived from /root/.hermes/skills/productivity/batch-scanned-ocr/SKILL.md on 2026-10-21 -->

---
name: batch-scanned-ocr
description: "Use when 批量 OCR 扫描件/图片型中文 PDF 时. RapidOCR+fitz 批量纪律."
version: 1.0.0
author: Hermes Agent
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [OCR, PDF, RapidOCR, Batch, Chinese]
    related_skills: [ocr-and-documents]
---

> 归档卡：原目录 `/root/.hermes/skills/productivity/batch-scanned-ocr`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/productivity/batch-scanned-ocr/…')`，不要相对 `references/legacy/` 解析。

# 批量扫描件 OCR(RapidOCR + PyMuPDF)

场景:成批的图片型/扫描版中文 PDF(报告、档案、通知书、台账)要提文本。marker-pdf 需 ~5GB 且慢;本机已装 `rapidocr_onnxruntime`,直接用下面轻量流程。

## 核心代码

```python
import fitz  # PyMuPDF
from rapidocr_onnxruntime import RapidOCR
engine = RapidOCR()                      # 只创建一次,循环复用

doc = fitz.open(pdf_path)
for page in doc:
    pix = page.get_pixmap(dpi=140)       # 中文报告 140dpi 够用
    res, _ = engine(pix.tobytes("png"))  # res: [[box, text, score], ...]
    text = "\n".join(r[1] for r in res) if res else ""
```

## 铁律(踩坑实录)

1. 文件清单写入 .py 脚本内部循环 —— 绝不把含空格/括号的文件名经 shell/xargs 传参,会被拆碎成假「文件不存在」错误,坑一整批
2. 禁用 multiprocessing(Windows spawn → WinError 87 必炸);用顺序循环或 ThreadPoolExecutor(max_workers=2~6)
3. 单文件 OCR 60~120 秒:设计成「跳过已完成缓存、每轮 3~4 个正常退出」分多轮跑;一次硬跑整批必被调用超时杀掉(exit 15)
4. 先 `page.get_text()` 试文本层,空的才送 OCR;结果按文件名缓存到 `_ocr/` 目录,重跑不重烧算力
5. read_file 报「图片型/无文本层/coverage warning」的 PDF 直接走本流程,不要反复试 read_file
6. 工作清单 json 条目可能是 list 而非字符串,消费前 `isinstance(x, list)` 归一化

## 验证

- 每批完成后抽查输出首尾行(UTF-8);`wc -c` 对比文件数,确认无遗漏
- 失败标记(如 `<<OCR_FAIL>>`)单独 grep 出来重试
