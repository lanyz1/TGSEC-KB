---
name: ai-product-imaging
description: >-
  测绘引擎·用在线生图 API 批量给商品生成 AI 场景图并填充图册/报价图(异步任务中转站模式)。
owned: true
tier: general
pack: survey-skill
---

# ai-product-imaging（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ai-product-imaging/`

溯源（仅标记）：`hermes/creative`

---

# AI 商品视觉物料(场景图/图册/报价图)

用在线生图 API(如 apimart 中转站的 gpt-image-2)把真实产品图重绘成科技感/场景图,再填进产品图册(catalog.html)或报价图。适用于:厂家报价图、产品图册、商品宣传图批量制作。

## 触发条件
- 用户要"AI 生成产品图/场景图"、"厂家报价图"、"产品图册",且有商品素材图(本地路径)+ 价格/规格数据(xlsx/表格)
- 用户说"用 image2.0 / image2 生成" = gpt-image-2 模型

## 用户偏好(本用户,违反会返工)
1. **先出一张样板给用户确认,再批量**(用户明确要"先做一张出来发给我看看效果")
2. **生成的图片直接 MEDIA 发出去,不要先 vision_analyze 分析占用回合**——用户会说"你别分析了,直接发给我,我来看就行了"
3. 用户指定 gpt-image-2(apimart 中转有该模型)
4. 交付时给文件路径 + 关键验证数字(生成张数/图册行数),让用户自己看效果

## 厂家报价/图册计价规则(本用户口径,2026-08-13 确认)
- 厂家拿货价 = 卖家售卖价 ÷ 2,取整数(去小数点,如 525.27÷2=262.635→262)
- 运费与价格分开算:整机/套装类 60 USDT、耗材/配件类 8 USDT(按品类,不是按件数)
- 产品图册/报价图里价格用**拿货价**(不是售价)

## 工作流
1. **检查素材图**:从 xlsx 读主图路径,验证 47/全部存在(缺图先补)
2. **出样板**:选第一个商品,生成 1 张场景图 + 1 张完整效果图(左图右信息)给用户确认风格
3. **批量生成**:见 `scripts/batch_gen_images.py`(3 并发 + 断点续跑 + 大图压缩);用户确认风格后才批量
4. **填充模板**:`templates/catalog.html`(A4 产品图册:封面+一页一品+价目总表);替换 PRODUCTS 数组(标题精简去"Bambu Lab"前缀、model=SKU 码、img=images/NN_sku.png、price=拿货价、specs=品牌/类型/材料/SKU/发货、skus=完整 SKU 明细数组)。**价格条只保留左边"批发价"大字——右下角 moq/运费块用户已拍板删除(2026-08-13),不要再渲染**
5. **多 SKU 明细**:解析 xlsx SKU 明细列(`规格|码|价|库存;规格|码|价|库存`,分号分隔)→ 每商品 skus 数组;模板里 `skus.length > 1` 才渲染"SKU 明细"区块。**用户拍板:一行一个(≤16 色)、17-28 两列、>28 三列**;label 只取第一段颜色名(拼 kg/refill 后缀会换行撑爆行高)。详见 `references/catalog-detail.md`
6. **验证**:Puppeteer 打开本地 HTTP 服务(127.0.0.1:8766 起 python http.server,根=素材所在目录,防 file:// 中文路径打不开),检查 `.figure img` broken=0、价目表行数=商品数、**逐页检查 pricebar 不溢出页面**,截图封面+产品页给用户
7. **交付**:给浏览器地址 + MEDIA 截图 + 打印说明(浏览器 Ctrl+P → 另存 PDF → 边距无、背景图形开)
8. **采集原链接提取**:素材目录每商品文件夹内 `商品信息.txt` 有 ASIN + 商品链接(Amazon UK `amazon.co.uk/dp/ASIN` 或 Bambu UK 官网);匹配时注意 xlsx SKU 码带 `-01` 后缀而目录名不带。详见 `references/catalog-detail.md`

## 关键坑(apimart 中转站异步生图)
- **必须带浏览器 User-Agent 头**,否则 urllib 裸请求 403(Cloudflare error 1010)
- 异步任务模式:POST `/v1/images/generations` 返回 `task_id` → 轮询 GET `/v1/tasks/{id}`(8s 间隔)直到 `status=completed` → 图片在 `result.images[0].url[0]`
- 图生图字段是 **`image_urls`**(数组,值必须 `data:image/jpeg;base64,...` 前缀格式),不是 `image`
- **素材图 >500KB 必须先压缩**(PIL thumbnail 1024 + JPEG q82),否则 HTTP 413 Payload Too Large;重试 3 次仍 413 说明没压缩成功
- **并发可行**:3 个任务并行提交不排队(实测 ~3x 提速);2 任务同时 processing 确认
- 断点续跑:已存在且 >50KB 的输出文件跳过,批量中断可安全重启
- 单张成本约 0.0085 USDT(gpt-image-2 1024px),47 张 < 0.5 USDT
- API key 从环境变量读(APIMART_KEY),不硬编码进脚本/技能
- **单商品重生成**:用户给新主图(任意路径)→ 用新图重生成 → 覆盖同名 `images/NN_sku.png`(文件名不变则 html 零改动,用户强刷 Ctrl+Shift+R 即可看到新图)

## 支持文件
- `references/apimart-api.md` — apimart 异步生图 API 完整细节(端点/请求响应/限制)
- `references/catalog-detail.md` — SKU 明细解析/防溢出参数、采集原链接提取(商品信息.txt)、单商品重生成
- `scripts/batch_gen_images.py` — 批量生图脚本模板(并发/压缩/断点/日志,改 SRC/OUT_DIR/prompt 即用)
- `templates/catalog.html` — A4 产品图册模板(封面+一页一品+价目总表+SKU 明细区,改 BRAND/PRODUCTS 即用)
