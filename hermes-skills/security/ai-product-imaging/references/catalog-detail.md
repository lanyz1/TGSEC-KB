# 图册细节:SKU 明细 / 防溢出 / 采集原链接 / 单商品重生成

(2026-08-13 拓竹 47 品实战沉淀)

## 1. SKU 明细解析(xlsx 第 5 列 → skus 数组)

xlsx "SKU明细" 列格式:`规格|码|价|库存;规格|码|价|库存;...`(分号分隔多 SKU)。

```python
def parse_skus(sku_det):
    out = []
    for seg in str(sku_det).split(";"):
        parts = seg.split("|")
        if len(parts) < 2: continue
        label_raw = parts[0].strip(); sku = parts[1].strip()
        price = parts[2].strip() if len(parts) > 2 else ""
        # label 只取第一段(颜色名), 如 "Blue (10601) / Refill / 1 kg" → "Blue (10601)"
        # 教训: 拼 kg/refill 后缀 → 2列下行宽不足换行 → 行高 64px+ → 43 色页高 1795px 爆页
        bits = [b.strip() for b in label_raw.split("/")]
        label = bits[0] if bits else label_raw
        if len(label) > 26: label = label[:26] + "…"
        out.append({"label": label, "sku": sku, "price": price})
    return out
```

模板渲染:`skus.length > 1` 才显示"SKU 明细"区块(单 SKU 商品用 specs 里的 SKU 字段即可,不重复列)。
行内容 = `红点 + label(颜色名) + sku 码 + price USDT`,`white-space:nowrap` 防换行(label 溢出省略号)。

## 2. 多 SKU 防溢出(A4 页 297mm ≈ 1123px)

实测:PLA Basic 43 个颜色 SKU,单列列表会溢出被截断。**用户拍板布局:一行一个(≤16 色)、17-28 两列、>28 三列**;防溢出最终参数(迭代三轮后定稿):

| 项 | 最终值 |
|---|---|
| `.figure` 高度 | **68mm**(margin 6mm) |
| `.specs .row` padding | **5px**(font 13px) |
| `.skus-rows` 网格 | 1fr 单列;`.cols2` = 1fr 1fr(column-gap 26px);`.cols3` = 3 列(gap 20px) |
| `.sku-row` | padding 3px、font 11.5px、nowrap;`.v` flex:1 + ellipsis |
| `.pricebar` padding | 12px 20px |

JS 按数量选列:`p.skus.length > 28 ? "cols3" : p.skus.length > 16 ? "cols2" : ""`。
溢出验证脚本(必须做):Puppeteer 遍历每页,`pricebar.getBoundingClientRect().bottom > page.getBoundingClientRect().bottom + 2` 即溢出,列出页码,修到 0 页。

## 3. 采集原链接提取

- 素材目录结构:每商品一个文件夹(`拓竹Amazon套装素材/拓竹打印机素材/拓竹耗材素材/<商品名>/`),内含 `商品信息.txt`
- `商品信息.txt` 尾部有 `【Amazon UK 原始数据】` 段:`ASIN: B0GQMN8VLS` + `商品链接: https://www.amazon.co.uk/dp/B0GQMN8VLS`(或 Bambu UK 官网 `uk.store.bambulab.com/products/<slug>`)
- **匹配坑**:xlsx SKU 码带 `-01` 后缀(`a1-01`、`pla-basic-filament-01`),素材目录名不带(`a1`、`pla-basic-filament`)→ 匹配时依次尝试 `sku`、`sku[:-3]`(去 -01)、按 ASIN 匹配
- 读取用 `encoding="utf-8-sig"`(文件带 BOM)
- 输出格式:`序号|名称|分类|ASIN|链接`,存 txt 交付

## 4. 单商品重生成

用户对某张场景图不满意或提供了正确主图(文件直接放桌面,可能带 Amazon 命名如 `715qq4z9yCL._AC_SL1500_.jpg`):
- 用新主图跑一次单张生成(同一 prompt 体系,可微调该品类描述)
- **覆盖同名** `images/NN_sku.png` → html 零改动,用户强刷 Ctrl+Shift+R 生效
- 生成完把新图 MEDIA 发给用户确认

## 5. 图册数据填充要点

- 标题精简:`re.sub(r"^Bambu Lab\s*","",title)` + 按 `[,\|]` 截断(去掉 Amazon 宣传语)
- 整机 specs:`{品牌, 类型:"桌面 FDM 3D 打印机", 系列, SKU, 发货:"48 小时内发货"}`;耗材 specs:`{品牌, 材料(从标题提取 PLA/PETG/TPU/ABS/ASA/PC/PVA/PA), 规格:"1kg / 卷", SKU, 发货}`
- price 用拿货价(售价/2 取整);**价格条右下角 moq/运费块已删(用户拍板 2026-08-13),只保留左边批发价大字——不再写 moq 渲染**
- 模板币种:价格条 `<span class="cur">¥</span>` → USDT,价目表标题 `批发价(¥)` → `厂家拿货价(USDT)`
- 填充脚本用正则 `re.sub(r"const PRODUCTS = \[.*?\];", products_js, html, flags=re.S)` 整段替换,再跑币种替换
