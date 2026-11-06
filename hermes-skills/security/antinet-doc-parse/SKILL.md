---
name: antinet-doc-parse
description: >-
 测绘引擎·将 PDF/PPT/Excel/Word 等多格式文档解析为结构化 Markdown，并输出元数据与解析置信度，作为 RAG 与四色卡片的数据底座。
owned: true
pack: survey-skill
---

# antinet-doc-parse（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/antinet-doc-parse/`

溯源（仅标记）：`anbeime/skill-local`

---

# 多格式文档解析 Skill（密卷房）

## 使用方式
- 由密卷房 Worker 在收到已通过安全扫描的文件时调用。
- 三级 fallback 依次尝试，输出最终结构化结果与置信度。

## 输入（Input）
- `file_path`：已通过 security-scan 的本地文件路径
- `formats`：（可选）期望支持的格式白名单，默认全格式

## 输出（Output）
- `markdown`：结构化 Markdown 正文
- `metadata`：标题、页数、表格数、作者等元数据
- `confidence`：0–1 解析置信度
- `fallback_used`：最终生效的解析器名称

## 依赖（Dependencies）
- MinerU（首选，强排版还原）
- PyMuPDF（次选，PDF 快速解析）
- pdfplumber（兜底，表格/文本抽取）
- `python-magic`（类型探测）

## 失败处理（Failure Handling）
- 主解析器失败 → 自动降级到下一档，直到全部尝试。
- 三级全部失败 → 标记 `人工介入`，不输出残缺结果，回传 BLOCKED 给军机处。
- 单页超大文件 → 分块解析后拼接，避免内存溢出；块级失败仅标记该块低置信度。

## 复用价值（Reuse Value）
- 通用解析底座：RAG 索引、企业知识库、合同结构化均可直接复用。
- 置信度透明：下游（通政司四色卡片）可据此决定是否需要人工复核，降低幻觉风险。

## 复赛代码包执行（runnable package）
- 真实入口：`scripts/run_doc_parse.py`
- 执行等价于 `core.runtime.AgentSession.run_stage("doc-parse")`，调用 `archive.mijuanfang.MiJuanFangAgent`（三级解析 fallback，纯 Python 可离线）。
- 运行：`python skills/doc-parse/scripts/run_doc_parse.py`
- 产物：`examples/snse_survey/skill_outputs/doc_parse.json`（解析结果 + 置信度 + fallback 信息）。

---

## 在测绘引擎作业中的实际用法

安全作业中，本卡用于**解析渗透过程中获得的文档文件**（如 heapdump 导出、JS 配置文件、泄露的 PDF 合同、Excel 配置表等）。

### 文档解析命令

```bash
# 解析 PDF 文件（heapdump 分析报告 / 授权文件）
python3 -c "
try:
 import fitz # PyMuPDF
 doc = fitz.open('<文件路径>.pdf')
 for i, page in enumerate(doc):
 text = page.get_text()
 if any(kw in text.lower() for kw in ['password', 'token', 'secret', 'key', 'api']):
 print(f'[PAGE {i+1}] SENSITIVE CONTENT DETECTED:')
 print(text[:500])
 doc.close()
except ImportError:
 print('pip3 install PyMuPDF')
"

# 解析 Excel/CSV 配置文件（支付配置、商户列表）
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('<文件路径>.xlsx')
for sheet in wb.sheetnames:
 ws = wb[sheet]
 print(f'=== Sheet: {sheet} ({ws.max_row} rows) ===')
 for row in ws.iter_rows(max_row=5, values_only=True):
 print(row)
" 2>/dev/null || python3 -c "
import csv
with open('<文件路径>.csv') as f:
 reader = csv.DictReader(f)
 for i, row in enumerate(reader):
 if i < 5: print(dict(row))
"

# 批量提取 JS 文件中的敏感信息（从泄露的源码/minified JS）
python3 -c "
import re, sys
content = open('<文件路径>.js').read()
patterns = {
 'API Key': r'[\"\'](sk-|pk-|AIza|AKIA)[A-Za-z0-9_-]{20,50}[\"\']]',
 'JWT Secret': r'[\"\'](jwt[_-]?secret|JWT_SECRET)[\"\']\s*[:=]\s*[\"\']\w{16,}[\"\']]',
 'DB Password': r'(DB_PASSWORD|database_password)\s*[:=]\s*[\"\']\S+[\"\']]',
 'AES Key': r'(aesKey|AES_KEY|secretKey)\s*[:=]\s*[\"\']\w{16,32}[\"\']]',
}
for name, pattern in patterns.items():
 matches = re.findall(pattern, content, re.IGNORECASE)
 if matches:
 print(f'[{name}] Found: {matches[:3]}')
"
```

### 结构化提取到证据目录

```bash
# 解析结果写入案卷
python3 tools/ops/core_web_surface_probe.py \
 --parse-doc <文件路径> \
 --case <案卷> \
 --out exports/bot-recovery/<案卷>/docs/ 2>/dev/null || \
echo "手动解析: python3 -c 'import fitz; ...'"
```
