# 无注释干扰的 HTML 表格解析 + 对齐验收

服务端渲染后台（PHP/layui、Bootstrap 表、老式 easyui）的 `<table>` 有两个害人特性：
1. 被注释掉的 `<td>`（常见于「操作」列整段注释）会被 naive 正则当成真实单元格；
2. 单元格里可能嵌 `<table>`/嵌套 `<div>`，非贪婪正则会提前截断。

## 解析器（先删注释，再深度匹配收单元格）
```python
import re

COMMENT = re.compile(r"<!--.*?-->", re.S)
OPEN    = re.compile(r"<(td|th)\b[^>]*>", re.I)

def _cells(tr_html: str):
    """从单个 <tr> 里按深度匹配收出单元格；同名标签嵌层不会截断。"""
    out, i = [], 0
    while True:
        m = OPEN.search(tr_html, i)
        if not m:
            break
        tag = m.group(1).lower()
        j, depth = m.end(), 1
        close = re.compile(r"</?%s\b[^>]*>" % tag, re.I)
        n = None
        while depth > 0:
            n = close.search(tr_html, j)
            if not n:
                break
            depth += -1 if n.group(0).startswith("</") else 1
            j = n.end()
        seg = tr_html[m.end():(n.start() if n else len(tr_html))]
        seg = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', r"[img:\1]", seg, flags=re.I)  # 图片列别丢
        seg = re.sub(r"<[^>]+>", " ", seg)
        seg = seg.replace("&nbsp;", " ")
        out.append(re.sub(r"\s+", " ", seg).strip())
        i = j if j > m.end() else m.end()
    return out

def rows_of(html: str):
    html = COMMENT.sub("", html)                      # ① 关键：先删注释
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
    return [_cells(x) for x in trs]
```

## 对齐验收闸（交付前必跑）
```python
import csv

def check(path, key_hint="订单号"):
    rows = list(csv.reader(open(path, encoding="utf-8-sig", errors="replace", newline="")))
    hdr, body = rows[0], rows[1:]
    bad = [i for i, r in enumerate(body) if len(r) != len(hdr)]
    print("表头列数=%d 行数=%d 列数不符=%d" % (len(hdr), len(body), len(bad)))
    if key_hint in hdr:                      # 主键列语义抽查
        k = hdr.index(key_hint)
        empty = sum(1 for r in body if not r[k].strip())
        print("主键列 '%s' 空值=%d（列错位的典型症状）" % (key_hint, empty))
    return not bad
```
- 列数不符 ⇒ **整表重抓**，不要就地修补。
- 表头列数要跟页面表头人工核对一次 —— 表头行也会被注释污染。
- 「行数正确但列错位」是最隐蔽的失败形态：行数校验会全绿。

## 分页全抓 + 主键去重
```python
seen, out, dup = set(), [hdr], 0
for r in body:
    key = (r[0], r[2])            # 主键组合，按业务选
    if not r[0].strip() or key in seen:
        dup += 1
        continue
    seen.add(key); out.append(r)
```
打印「原始 / 唯一 / 重复」三个数，并写进交付说明。

## 详情页富化（PII）
layui 详情页通用「标签→值」抽取：
```python
pat = re.compile(r"([^<>]{2,16})[:：]\s*</label>(.{0,500}?)(?=<label|</form>|$)", re.S)
# 值优先 value="..."，再取 <span>，最后兜底页内第一个 1[3-9]\d{9}
```
并行：`ThreadPoolExecutor(max_workers=12)` + `urllib`（`ssl._create_unverified_context()`，带 `Host`/`Cookie` 头），逐条 append + flush 以便断点续跑。
