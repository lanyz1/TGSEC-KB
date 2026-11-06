<!-- archived from /root/.hermes/skills/security/ecommerce-product-collection/SKILL.md on 2026-10-21 -->

---
name: ecommerce-product-collection
description: >-
  测绘引擎·Use when collecting vendor product data for listing prep.
owned: true
tier: ops
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/ecommerce-product-collection`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/ecommerce-product-collection/…')`，不要相对 `references/legacy/` 解析。

# ecommerce-product-collection（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ecommerce-product-collection/`

溯源（仅标记）：`hermes/research`

---

# 电商商品数据采集（跨境上架素材整理）

适用：从品牌官网/官方商店采集商品（整机/耗材/配件）的型号、价格、规格、图片，整理成可上架素材（如 Qavlixor 卖家端批量上传模板 16 列字段）。2026-08-11 拓竹采集首战定型。

## 通用流程

1. **判定商店架构**：先探 `{domain}/products.json?limit=5` 与 `{domain}/products/{handle}.json`
   - 返回 JSON = Shopify 标准店 → 直接翻页拉全量（`?page=N`）
   - 404 / HTML = 自研 Next.js 店（如拓竹 uk.store.bambulab.com）→ 走 JSON-LD 路线，**不要反复试 products.json**
2. **拿全量清单**：
   - `/sitemap.xml` → `sitemap_products_*.xml`（`<loc>` 即全部产品 handle，含配件，需自己筛类）
   - collection 页：browser_navigate 后用 browser_console 执行 `Array.from(document.querySelectorAll('a[href*="/products/"]')).map(a=>a.href.split('?')[0]).filter((v,i,arr)=>arr.indexOf(v)===i)` 去重提取
3. **单页数据**：curl 产品页 HTML（带浏览器 UA），正则提取 `application/ld+json` 块：
   - `ProductGroup`: name / description / hasVariant[]
   - 每 variant: sku / image(CDN) / offers.price / priceCurrency / priceSpecification(划线价) / availability(InStock=有货)
4. **图片**：CDN URL 直接下载，需带 UA；文件名 `01.jpg` `02.jpg`…，首张=主图；同一 URL 去重
5. **组织产物**：每商品一个子文件夹（用 handle 命名，安全无特殊字符），内含图片 + `商品信息.txt`（按目标平台模板字段写，见下）
6. **货币换算**：open.er-api.com 实时汇率（`https://open.er-api.com/v6/latest/USD` 或 `/latest/GBP`）；USDT≈USD；txt 里记录 原币种原价 + 汇率 + 采集时间

## Qavlixor 模板 16 列（商品信息.txt 按此写）

商品标题* / 品牌 / 分类 / 默认价格(USDT)* / 默认库存* / SKU明细(`规格名|编码|价格|库存; 多个用;分隔`) / 主图URL / 详情图URL(多张;分隔,最多12) / 卖点文字 / 产品参数(`参数名:值; 多个用;分隔`) / 运费方式 / 首件运费 / 续件运费 / 包邮门槛(USDT) / 发货时限 / 保存状态(草稿)

- SKU 规格名 = 变体名去掉商品名前缀后剩余部分（清理首尾 ` -–—`）
- SKU 编码建议 `{handle}-{序号:02d}`，库存给占位 100 并注明"按实际调整"
- 运费给建议默认并注明可调（大件打印机 vs 小件耗材不同）

## 关键坑（都踩过）

- **出口 IP 决定地区重定向**：伦敦出口 → `us.store.bambulab.com` 302 到 `uk.store.bambulab.com`，价格变 GBP。采集到的价格=所见货币，必须记录币种并换算，不能当 USD 用
- **Windows 原生 Python 不认 MSYS 路径**：传 `/c/Users/...` 会把文件夹建到 `C:\c\Users\...`；脚本输出目录参数必须用 `C:\Users\...` 格式
- 自研 Next.js 店 `products.json` / `products/{h}.json` 全 404，不要浪费轮次
- **供应商给的 xlsm/xlsx 模板先查宏再打开**——恶意宏很常见（见 references/malicious-office-macro-detection.md）
- 请求间隔 ≥0.6s + UA，避免触发反爬；批量跑用后台 terminal + notify_on_complete
- 平台分类不存在时（如 Qavlixor 无 3D 打印机类）：填自定义路径 `3D打印机/整机` 并注明"需管理端新增分类"

## 支持文件

- `references/bambulab-uk-store.md` — 拓竹 UK 店采集实录（URL、JSON-LD 形态、汇率、产出结构）
- `references/malicious-office-macro-detection.md` — 从 xlsm 提取 VBA 字符串识别木马下载器
- `templates/bulk_product_collector.py` — 通用采集器骨架（改 BASE/HEADERS/SLEEP/汇率即可复用）
