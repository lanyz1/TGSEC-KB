# Bambu Lab 官方店采集（uk.store.bambulab.com）

2026-08 实测。出口 IP 在英国（伦敦）时 `us.store.bambulab.com` 302 → `uk.store.bambulab.com`。

## 站点架构
- **自研 Next.js 商店**（非 Shopify）：`/products.json`、`/collections/{h}/products.json`、`/products/{h}.json` 全部 404。只能扒页面 HTML 里的 JSON-LD。
- **sitemap**：`/sitemap.xml` → `sitemap_products_1.xml`（全部 1021 个产品 handle，含配件）、`sitemap_collections_1.xml`、`sitemap_pages_1.xml`。
- **collection**：打印机 `collections/3d-printer`（9款：p2s/x2d/a1/p1s/a1-mini/a2l/h2s/h2d/h2c）；耗材 `collections/bambu-lab-3d-printer-filament`（36款）。注意 collection URL 不带 s（`3d-printer` 不是 `3d-printers`）。
- 反爬弱：普通 UA + 0.6s 间隔即可；图片 CDN `store.bblcdn.eu`（图片带 `/s4/default/<hash>/<Name>.jpg` 路径，可直链下载）。

## JSON-LD 结构（ProductGroup）
页面内 `<script type="application/ld+json">` 第一块即商品数据：

```json
{
  "@type": "ProductGroup",
  "name": "Bambu Lab P1S 3D Printer",
  "description": "...",
  "hasVariant": [
    {
      "@type": "Product",
      "sku": "736011934381252614",
      "image": "https://store.bblcdn.eu/s4/default/<hash>/P1SC.jpg",
      "name": "Bambu Lab P1S 3D Printer - P1S AMS Combo",
      "offers": {
        "price": 469, "priceCurrency": "GBP",
        "availability": "https://schema.org/InStock",
        "priceSpecification": { "priceType": "StrikethroughPrice", "price": 479 }
      }
    }
  ]
}
```

- 变体 = 套装/颜色/Refill-vs-带线轴等；耗材一款常 40+ 变体（颜色×包装），图片去重后约 1~30 张。
- 2026-08 价格（UK 店英镑）：A1 mini 单机 £149/Combo £259；A1 单机 £209/Combo(AMS Lite) £319；P1S 单机 £329/AMS Combo £469/AMS 2 Pro Combo £519。GBP→USDT ≈ ×1.3486（open.er-api.com 实时）。

## 变体名清洗
变体名 = "商品名 - 规格名"，写 SKU 明细时去掉商品名前缀再 strip 掉 ` -–—`，否则规格名带 `- ` 前缀。
