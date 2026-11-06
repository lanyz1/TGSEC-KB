# 拓竹 Bambu Lab UK 商店采集实录（2026-08-11）

## 商店属性
- 域名：`uk.store.bambulab.com`（自研 Next.js 商店 + Cloudflare，**非 Shopify**）
- `products.json`、`products/{handle}.json` 全部 404（不要反复试）
- 地区重定向：本机出口伦敦 → `us.store.bambulab.com` 302 → `uk.store.bambulab.com`，价格 GBP

## 关键 URL
| 用途 | URL |
|---|---|
| 全量清单 | `https://uk.store.bambulab.com/sitemap.xml` → `sitemap_products_1.xml`（1021 个产品，含配件，需筛类） |
| 打印机 collection | `https://uk.store.bambulab.com/collections/3d-printer`（9 款） |
| 耗材 collection | `https://uk.store.bambulab.com/collections/bambu-lab-3d-printer-filament`（36 款） |
| 单产品页 | `https://uk.store.bambulab.com/products/{handle}` |

打印机 9 款：p2s, x2d, a1, p1s, a1-mini, a2l, h2s, h2d, h2c
耗材 36 款：pla-basic-filament, pla-matte, pla-pure, petg-basic, petg-hf, petg-translucent, pla-translucent, pla-silk-upgrade, abs-filament, pla-matte-refill-bundle-2-rolls, pla-cmyk-lithophane, pla-basic-beginner-s-filament-pack, pla-basic-gradient, pla-silk-multi-color, pla-metal, pla-marble, pla-galaxy, pla-sparkle, pla-wood, pla-tough-upgrade, pla-glow, tpu-85a-tpu-90a, tpu-for-ams, tpu-95a-hf, paht-cf, petg-cf, pla-cf, pet-cf, pc-filament, pc-fr, asa-filament, support-for-pla-new, support-for-pla-petg, pva, abs-gf, pa6-gf

## JSON-LD 形态（产品页内）
```json
{"@type": "ProductGroup", "name": "...", "description": "...", "hasVariant": [
  {"@type": "Product", "sku": "7360...", "image": "https://store.bblcdn.eu/s4/default/{hash}/{NAME}.jpg",
   "name": "完整变体名(含商品名前缀)",
   "offers": {"price": 469, "priceCurrency": "GBP",
              "availability": ".../InStock",
              "priceSpecification": {"price": 479, "priceType": ".../StrikethroughPrice"}}}
]}
```
正则提取：`<script[^>]*application/ld\+json[^>]*>(.*?)</script>`（re.S），取第一个块。

## 汇率（2026-08-11 open.er-api.com）
- GBP/USD = 1.3486（GBP→USDT = ×1.3486）
- USD/CNY = 6.765

## 产出结构（用户确认的方案A）
```
桌面/拓竹打印机素材/{handle}/  01.jpg 02.jpg ... 商品信息.txt
桌面/拓竹耗材素材/{handle}/    01.jpg 02.jpg ... 商品信息.txt
```
- 每商品一个子文件夹，handle 命名；图片首张=主图
- 商品信息.txt = 模板16列字段 + 原始数据（变体价格明细含 GBP 原价与 USDT 换算、描述原文、图片清单 本地文件名+URL）
- 测试结果参考：P1S 3变体3图（£469≈632.49 USDT），PLA Basic 43变体30图（£17.99≈24.26 USDT）

## 复用注意
- 采集器工作副本：`D:\跨境商城\会话产物\bambu_collector.py`（v2，含 16 列 txt 生成）
- 清单文件：同目录 `bambu_printers.txt` / `bambu_filaments.txt`
- 输出目录参数必须 Windows 路径（`C:\Users\...`），MSYS 路径会把文件夹建到 `C:\c\...`
