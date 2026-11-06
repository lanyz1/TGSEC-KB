#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Markdown -> DOCX converter (no pandoc needed; requires: pip install python-docx).
Handles: #/##/### headings, pipe tables (Table Grid), '- ' bullets, numbered lines,
strips **/_/*/` markers. Usage: python md2docx.py <src.md> <dst.docx>
"""
import re, sys
from docx import Document
from docx.shared import Pt


def strip_md(t):
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    return t.replace("`", "")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    doc = Document()
    doc.styles["Normal"].font.size = Pt(10.5)
    lines = open(src, encoding="utf-8").read().split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i]); i += 1
            rows = []
            for b in block:
                cells = [c.strip() for c in b.strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    continue
                rows.append(cells)
            if rows:
                ncol = max(len(r) for r in rows)
                t = doc.add_table(rows=len(rows), cols=ncol)
                t.style = "Table Grid"
                for ri, r in enumerate(rows):
                    for ci in range(ncol):
                        cell = t.cell(ri, ci)
                        cell.text = strip_md(r[ci]) if ci < len(r) else ""
                        for p in cell.paragraphs:
                            for run in p.runs:
                                run.font.size = Pt(9)
                                if ri == 0:
                                    run.bold = True
            doc.add_paragraph("")
            continue
        s = ln.rstrip()
        if s.startswith("### "):
            doc.add_heading(strip_md(s[4:]), level=3)
        elif s.startswith("## "):
            doc.add_heading(strip_md(s[3:]), level=2)
        elif s.startswith("# "):
            doc.add_heading(strip_md(s[2:]), level=1)
        elif s.startswith("---"):
            pass
        elif s.startswith("- "):
            doc.add_paragraph(strip_md(s[2:]), style="List Bullet")
        elif re.match(r"^\d+\.\s", s):
            doc.add_paragraph(strip_md(s))
        elif s.strip():
            doc.add_paragraph(strip_md(s))
        i += 1
    doc.save(dst)
    print("saved:", dst)


if __name__ == "__main__":
    main()
