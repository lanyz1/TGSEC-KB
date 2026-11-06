# -*- coding: utf-8 -*-
"""管理端批量 i18n 验证脚本(qavlixor-marketplace)。

用法:
  python admin-i18n-verify.py                 # 默认 6 页: products categories orders logistics withdrawals deposits
  python admin-i18n-verify.py sellers roles   # 自定义页面(传 app/admin/<页面名>/page.tsx 的页面名)
  python admin-i18n-verify.py components/admin/AdminTestOrdersClient.tsx   # 组件轮:传相对仓库根的 .tsx 路径也可

三步检查:
  1) 引用的全部 data-i18n*/data-i18n-aria-label/data-i18n-placeholder/data-i18n-title 键,
     在 lib/translations.ts 的 zh 段(第一个 const zh)与 en 段(const en)都必须存在 "key" 行
     —— MISSING_ZH/MISSING_EN 非空 = 英文态会显示原始键名(键名泄漏,坑 #32)。
  2) 裸中文残留探针: JSX 文本节点 `>中文<` 所在标签段必须带 data-i18n 属性,
     否则是该文本漏标(数据值/变量/DynamicText 渲染的除外,需人工判断)。
  3) 表达式位补扫(2026-08-06 组件轮新增): `([?:]) *"中文"` JS 串字面量(文本节点探针盲区),
     整行无 data-i18n 即打印 EXPR_HITS —— 仅供人工按豁免清单分类(setMessage/window.alert 串、
     labels 配置键记录、AppleSelect options 值、DynamicText 渲染数据 = 豁免),不参与 FAIL 判定。
退出码: 0 = 全过; 1 = 有缺失/漏标。
"""
import os
import re
import sys

BASE = r"D:\跨境商城\qavlixor-marketplace"
DEFAULT_PAGES = ["products", "categories", "orders", "logistics", "withdrawals", "deposits"]
CN = re.compile(r"[\u4e00-\u9fff]")
EXPR = re.compile(r'([?:]) *"([^"]*[\u4e00-\u9fff][^"]*)"')


def main() -> int:
    pages = sys.argv[1:] or DEFAULT_PAGES
    tr_path = os.path.join(BASE, "lib", "translations.ts")
    with open(tr_path, "rb") as f:
        tr = f.read().decode("utf-8-sig")
    zh_marker = tr.index("const zh: TranslationMap = {")
    en_marker = tr.index("const en: TranslationMap = {")
    zh_section = tr[zh_marker:en_marker]
    en_section = tr[en_marker:]

    all_keys: set[str] = set()
    uncovered: list[tuple] = []
    expr_hits: list[tuple] = []
    for pg in pages:
        if pg.endswith(".tsx") or pg.endswith(".ts"):
            p = os.path.join(BASE, pg)
        else:
            p = os.path.join(BASE, "app", "admin", pg, "page.tsx")
        with open(p, "rb") as f:
            lines = f.read().decode("utf-8-sig").split("\n")
        text = "\n".join(lines)
        keys = set(re.findall(r'data-i18n(?:-aria-label|-placeholder|-title)?="([^"]+)"', text))
        all_keys |= keys
        print(f"{pg}: {len(keys)} keys")
        for ln, line in enumerate(lines, 1):
            for m in re.finditer(r">([^<>{}]*[\u4e00-\u9fff][^<>{}]*)<", line):
                if not m.group(1).strip():
                    continue
                seg = line[line[: m.start()].rfind("<") : m.start()]
                if "data-i18n" not in seg:
                    uncovered.append((pg, ln, m.group(1).strip()[:40], seg[:100]))
            for m in EXPR.finditer(line):
                if "data-i18n" not in line:
                    expr_hits.append((pg, ln, m.group(2).strip()[:40]))

    missing_zh = [k for k in sorted(all_keys) if f'"{k}"' not in zh_section]
    missing_en = [k for k in sorted(all_keys) if f'"{k}"' not in en_section]
    print("MISSING_ZH:", missing_zh)
    print("MISSING_EN:", missing_en)
    print("UNCOVERED_TEXT_NODES:", uncovered)
    print("EXPR_HITS(人工按豁免清单分类):", expr_hits)
    ok = not missing_zh and not missing_en and not uncovered
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
