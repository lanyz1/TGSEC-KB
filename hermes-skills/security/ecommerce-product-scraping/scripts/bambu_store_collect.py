#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用 JSON-LD 商品采集器（Bambu Lab 官方店验证过，适配任何内嵌 ProductGroup/Product JSON-LD 的商店）
用法: python bambu_store_collect.py <kind> <handles清单.txt> "C:\\输出目录"
  kind: printer / filament 等，决定分类字段与运费建议档
每个商品 -> <输出目录>/<handle>/ (01.jpg... 主图+多图 + 商品信息.txt)
txt 按 Qavlixor 批量上传模板 16 列字段写；价格 GBP->USDT 换算（汇率常量按需更新）。
注意: Windows Python 只认 C:\\ 原生路径，别传 MSYS 的 /c/... 路径！
"""
import json, os, re, sys, time, urllib.parse
import requests

BASE = "https://uk.store.bambulab.com"
GBP2USD = 1.3486  # 2026-08-11 open.er-api.com，采集前查实时汇率
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
SLEEP = 0.6  # 防反爬
SHIP = {  # (运费方式, 首件, 续件, 包邮门槛, 发货时限) 建议值
    "printer": ("自定义运费", "60.00", "30.00", "1500", "48 小时内发货"),
    "filament": ("自定义运费", "8.00", "3.00", "150", "48 小时内发货"),
}


def fetch_jsonld(handle):
    r = requests.get(f"{BASE}/products/{handle}", headers=HEADERS, timeout=25)
    r.raise_for_status()
    m = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', r.text, re.S)
    return json.loads(m[0]) if m else None


def short_variant_name(full, product_name):
    n = full
    for pre in (product_name, product_name + " -", product_name + "-"):
        if n.startswith(pre):
            n = n[len(pre):].strip()
            break
    n = n.strip(" -–—")
    return n if n else full


def process(handle, out_dir, kind):
    d = fetch_jsonld(handle)
    if not d or not d.get("hasVariant"):
        print(f"✗ {handle}: 无JSON-LD/变体"); return False
    name, desc = d.get("name") or handle, (d.get("description") or "").strip()
    variants = d.get("hasVariant", [])
    folder = os.path.join(out_dir, handle)
    os.makedirs(folder, exist_ok=True)

    # 图片去重落地
    seen, img_paths, img_urls = set(), [], []
    for v in variants:
        img = v.get("image")
        if not img or img in seen:
            continue
        seen.add(img)
        ext = os.path.splitext(urllib.parse.urlparse(img).path)[1] or ".jpg"
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        fname = f"{len(img_paths)+1:02d}{ext}"
        try:
            r = requests.get(img, headers=HEADERS, timeout=30)
            r.raise_for_status()
            open(os.path.join(folder, fname), "wb").write(r.content)
            img_paths.append(fname); img_urls.append(img)
        except Exception as e:
            print(f"  图片失败: {e}")
        time.sleep(0.3)

    # 模板 16 列
    usdt = lambda p: round(float(p) * GBP2USD, 2) if p is not None else None
    ship = SHIP.get(kind, SHIP["printer"])
    sku_lines = [
        f"{short_variant_name(v.get('name') or '', name)}|{handle}-{i:02d}|{usdt((v.get('offers') or {}).get('price')):.2f}|100"
        for i, v in enumerate(variants, 1)
    ]
    first = usdt((variants[0].get("offers") or {}).get("price"))
    cat = "3D打印机/整机" if kind == "printer" else "3D打印机/耗材"
    params = ["品牌:Bambu Lab"] + (["类型:FDM 3D打印机"] if kind == "printer"
              else [f"材料:{name.split(' ')[0]}", "直径:1.75mm", "重量:1kg(典型)"]) + ["来源:Bambu Lab官方商店(UK)"]

    lines = [
        "=" * 56, "Qavlixor 批量上传模板字段 (对应模板16列)", "=" * 56,
        f"商品标题*: {name}", "品牌: Bambu Lab",
        f"分类: {cat}  ※平台暂无3D打印机分类,需管理端新增",
        f"默认价格(USDT)*: {first:.2f}  (GBP原价 {(variants[0].get('offers') or {}).get('price')}, 汇率{GBP2USD})",
        "默认库存*: 100  (占位建议值,请按实际调整)",
        f"SKU明细: {'; '.join(sku_lines)}",
        f"主图URL: {img_urls[0] if img_urls else ''}",
        f"详情图URL: {';'.join(img_urls[:12])}",
        f"卖点文字: {desc[:120]}{'…' if len(desc) > 120 else ''}",
        f"产品参数: {'; '.join(params)}",
        f"运费方式: {ship[0]}", f"首件运费: {ship[1]}  (建议值)", f"续件运费: {ship[2]}  (建议值)",
        f"包邮门槛(USDT): {ship[3]}  (建议值)", f"发货时限: {ship[4]}", "保存状态: 草稿",
        "", "=" * 56, "【原始数据】",
        f"商品链接: {BASE}/products/{handle}", f"采集时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"图片数量: {len(img_paths)}", "", "【变体/价格明细】",
    ]
    for v in variants:
        off = v.get("offers") or {}
        av = "有货" if "InStock" in (off.get("availability") or "") else "缺货"
        lines.append(f"- {v.get('name')} | {off.get('price')} {off.get('priceCurrency','')} ≈ {usdt(off.get('price')):.2f} USDT | SKU: {v.get('sku')} | {av}")
    lines += ["", "【商品描述(原文)】", desc, "", "【图片清单】"]
    for i, (p, u) in enumerate(zip(img_paths, img_urls), 1):
        lines.append(f"- {'主图' if i == 1 else f'图{i}'}: 本地={p} | URL={u}")

    open(os.path.join(folder, "商品信息.txt"), "w", encoding="utf-8").write("\n".join(lines))
    print(f"✓ {name} | {len(variants)}变体 | {len(img_paths)}图 | 首价{first:.2f} USDT")
    return True


def main():
    kind, handles_file, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    handles = [h.strip() for h in open(handles_file, encoding="utf-8") if h.strip()]
    ok = sum(process(h, out_dir, kind) for h in handles)
    print(f"\n完成: {ok}/{len(handles)}")


if __name__ == "__main__":
    main()
