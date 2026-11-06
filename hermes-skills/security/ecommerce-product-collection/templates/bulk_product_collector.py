#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用电商商品采集器骨架 (v2, 2026-08-11 拓竹采集定型)
解析产品详情页 JSON-LD(ProductGroup) -> 每商品一个子文件夹(主图+多图+商品信息.txt)
复用: 改 BASE / HEADERS / SLEEP / 汇率换算函数, 按目标平台模板字段改 txt 生成段
坑: 输出目录参数必须 Windows 路径 (C:\\...), MSYS 路径(/c/...)会建到 C:\\c\\...
"""
import json, os, re, sys, time, urllib.parse
import requests

BASE = "https://uk.store.bambulab.com"   # ← 目标商店
CURRENCY2USDT = 1.3486                    # ← 原币种→USDT 汇率(open.er-api.com 实时)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
SLEEP = 0.6  # 请求间隔, 防反爬

# 运费建议值(USDT) —— 按品类给默认, 注明可调
SHIP_DEFAULT = ("自定义运费", "8.00", "3.00", "150", "48 小时内发货")


def fetch_product(handle):
    url = f"{BASE}/products/{handle}"
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    m = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        return None
    return json.loads(m[0])


def download_image(img_url, path):
    try:
        r = requests.get(img_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"    图片下载失败: {e}")
        return False


def to_usdt(price):
    return round(float(price) * CURRENCY2USDT, 2) if price is not None else None


def fmt_price(p):
    return f"{p:.2f}" if p is not None else ""


def short_variant_name(full, product_name):
    """变体名去掉商品名前缀 -> 规格名"""
    n = full
    for pre in (product_name, product_name + " -", product_name + "-"):
        if n.startswith(pre):
            n = n[len(pre):].strip()
            break
    n = n.strip(" -–—")
    return n if n else full


def process(handle, out_dir, kind):
    print(f"▶ [{kind}] {handle}")
    try:
        d = fetch_product(handle)
    except Exception as e:
        print(f"  ✗ 抓取失败: {e}")
        return False
    if not d:
        print("  ✗ 无 JSON-LD")
        return False

    name = d.get("name") or handle
    desc = (d.get("description") or "").strip()
    variants = d.get("hasVariant", [])
    if not variants:
        print("  ✗ 无变体")
        return False

    folder = os.path.join(out_dir, handle)
    os.makedirs(folder, exist_ok=True)

    # 下载图片(所有变体图片, 去重; 首张=主图)
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
        if download_image(img, os.path.join(folder, fname)):
            img_paths.append(fname)
            img_urls.append(img)
        time.sleep(0.3)

    # ---- 目标平台模板字段 (按 Qavlixor 16 列) ----
    cat = "3D打印机/整机" if kind == "printer" else "3D打印机/耗材"  # ← 按需改
    ship = SHIP_DEFAULT
    sku_lines = []
    for i, v in enumerate(variants, 1):
        off = v.get("offers") or {}
        sku_lines.append(
            f"{short_variant_name(v.get('name') or '', name)}|{handle}-{i:02d}|{fmt_price(to_usdt(off.get('price')))}|100"
        )
    first_price = to_usdt((variants[0].get("offers") or {}).get("price"))
    selling = desc[:120] + ("…" if len(desc) > 120 else "") if desc else ""

    lines = [
        "=" * 56,
        "Qavlixor 批量上传模板字段 (对应模板16列)",
        "=" * 56,
        f"商品标题*: {name}",
        "品牌: " + (d.get("brand", {}).get("name") if isinstance(d.get("brand"), dict) else ""),
        f"分类: {cat}",
        f"默认价格(USDT)*: {fmt_price(first_price)}",
        "默认库存*: 100  (占位建议值,请按实际调整)",
        f"SKU明细: {'; '.join(sku_lines)}",
        f"主图URL: {img_urls[0] if img_urls else ''}",
        f"详情图URL: {';'.join(img_urls[:12])}",
        f"卖点文字: {selling}",
        f"产品参数: 品牌:{d.get('brand', {}).get('name') if isinstance(d.get('brand'), dict) else ''}",
        f"运费方式: {ship[0]}",
        f"首件运费: {ship[1]}  (建议值,请按实际调整)",
        f"续件运费: {ship[2]}  (建议值,请按实际调整)",
        f"包邮门槛(USDT): {ship[3]}  (建议值,请按实际调整)",
        f"发货时限: {ship[4]}",
        "保存状态: 草稿",
        "",
        "=" * 56,
        "【原始数据】",
        f"商品链接: {BASE}/products/{handle}",
        f"采集时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"图片数量: {len(img_paths)}",
        "",
        "【变体/价格明细】",
    ]
    for v in variants:
        off = v.get("offers") or {}
        av = "有货" if "InStock" in (off.get("availability") or "") else "缺货"
        lines.append(
            f"- {v.get('name')} | {fmt_price(off.get('price'))} {off.get('priceCurrency','')} "
            f"≈ {fmt_price(to_usdt(off.get('price')))} USDT | SKU: {v.get('sku')} | {av}"
        )
    lines += ["", "【商品描述(原文)】", desc, "", "【图片清单】"]
    for i, (p, u) in enumerate(zip(img_paths, img_urls), 1):
        lines.append(f"- {'主图' if i == 1 else f'图{i}'}: 本地={p} | URL={u}")

    with open(os.path.join(folder, "商品信息.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✓ 完成: {name} | {len(variants)}变体 | {len(img_paths)}图")
    return True


def main():
    kind = sys.argv[1]          # 品类标识(影响分类字段)
    handles_file = sys.argv[2]  # 每行一个 handle
    out_dir = sys.argv[3]       # Windows 路径!
    handles = [h.strip() for h in open(handles_file, encoding="utf-8") if h.strip()]
    ok = 0
    for h in handles:
        if process(h, out_dir, kind):
            ok += 1
        time.sleep(SLEEP)
    print(f"\n完成: {ok}/{len(handles)}")


if __name__ == "__main__":
    main()
