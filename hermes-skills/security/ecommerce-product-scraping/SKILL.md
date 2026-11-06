---
name: ecommerce-product-scraping
description: >-
  测绘引擎·采集电商商品成上架素材，JSON-LD/sitemap/图片落地/按模板出商品信息txt。
owned: true
tier: ops
pack: survey-skill
---

# ecommerce-product-scraping（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ecommerce-product-scraping/`

溯源（仅标记）：`hermes/research`

---

# 电商商品采集 → 可上架素材

把电商商品页（官方品牌店、Amazon、Shopify 店等）采集成本地素材包：每商品一个子文件夹（主图+多图 + `商品信息.txt`），txt 前半按 Qavlixor 批量上传模板 16 列字段写，后半留原始数据（评分/评价/卖家/卖点原文/图片URL）。

## 通用流程（5 步）

1. **找商品清单**：
   - 先试 `sitemap.xml` → `sitemap_products_1.xml`（Next.js 商店都有，一次拿全所有 handle）
   - 或从 collection 页导航链接拿清单（如 `collections/3d-printer`）
   - Shopify 架构可试 `{store}/products.json?limit=250`（自定义 Next.js 商店会 404，别浪费时间）
2. **详情页数据**：解析 `<script type="application/ld+json">` 里的 `ProductGroup` / `Product`。关键字段：`hasVariant[]`（每项含 `sku`、`image`(CDN直链)、`offers.price`、`offers.priceCurrency`、`offers.priceSpecification.price`(划线价)、`availability`）。绝大多数电商站都有 JSON-LD，比扒 DOM 快且全。
3. **图片落地**：取 `variant.image` 去重后按 `01.jpg`、`02.jpg`… 编号下载；Amazon 图片 URL 要去缩略图标记（见 references/amazon-uk.md）。下载间隔 0.3s 防反爬。
4. **价格换算 USDT**：Qavlixor 模板价格是 USDT（=USD）。非美元币种用 `https://open.er-api.com/v6/latest/XXX` 拿实时汇率换算（本机 TUN 直连可用）。汇率写进 txt 注明来源日期。
5. **输出**：`商品信息.txt` 按模板 16 列：商品标题*/品牌/分类/默认价格(USDT)*/默认库存*/SKU明细(`规格名|编码|价格|库存;`分隔)/主图URL/详情图URL(;分隔≤12)/卖点文字/产品参数(`名:值;`)/运费方式/首件运费/续件运费/包邮门槛/发货时限/保存状态。库存/运费给建议值并注明"请按实际调整"，状态=草稿。

## 站点速查
- Bambu Lab 官方店：references/bambu-lab-store.md（JSON-LD 结构、CDN、collections）
- Amazon UK：references/amazon-uk.md（选择器、cookie、图片清理）
- 可复用采集器：scripts/bambu_store_collect.py（通用 JSON-LD 采集，传 kind/清单/输出目录）

## 陷阱（血的教训）
- **Windows git-bash 跑 Windows Python（python3）**：脚本参数必须传原生路径 `C:\...`。传 MSYS 风格 `/c/Users/...` 会被当成 `C:\c\Users\...`，文件夹建到错误位置且难以发现。脚本内输出目录写死 Windows 路径最稳。
- **browser_console 只认单行表达式**：多行箭头函数/对象字面量报 `Unexpected end of input`。拆成多个单行简单表达式逐个取。
- **出口 IP 决定商店区域**：本机住宅节点出口在英国伦敦 → `us.store.bambulab.com` 302 到 `uk.store.bambulab.com`，采到的是英镑价。要美区价需美国 IP。
- **官方店价 ≠ Amazon 套装价**：Amazon 常含渠道溢价 + 捆绑件（如 LED Kit），上架定价以官方店为基准，Amazon 五点卖点文案当素材参考。
- **商品信息.txt 编码**：必须 UTF-8 写（Windows 记事本/Excel 打开正常），不要 GBK。
- **先确认模板真实来源**：用户给的模板文件先验货——xlsm 可能是恶意宏（见 desktop-software-reversing 的 Office 宏排查），别直接双击/信任；干净模板在 `D:\跨境商城\会话产物\Qavlixor卖家端批量上传商品模板.xlsx`。
