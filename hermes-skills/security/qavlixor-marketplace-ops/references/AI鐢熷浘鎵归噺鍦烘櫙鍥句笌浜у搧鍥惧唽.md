# AI 生图批量场景图 + 产品图册填充(2026-08-13)

用户工作流:47 品(拓竹 3D 打印机,整机 12 + 耗材 35)生成「厂家报价图册」= 左边 AI 场景图 + 右边规格/价格,最终形态 = A4 产品图册(catalog.html,封面+一页一品+价目总表)。

## apimart.ai gpt-image-2 接口(中转站,异步任务模式)
- 提交:`POST /v1/images/generations`,`Authorization: Bearer <key>`,`Content-Type: application/json`。
- **必须带浏览器 UA 头**(`User-Agent: Mozilla/5.0 ...`),否则 Cloudflare 403(urllib 裸调 403,curl 带 UA 通过)。
- 返回 `{"code":200,"data":[{"status":"submitted","task_id":"task_..."}]}` → 轮询 `GET /v1/tasks/{task_id}`(约 25-100s;`estimated_time` 字段)。
- 完成时 `result.images[0].url[0]` → 下载保存。
- **图生图/编辑**:字段是 `image_urls`(数组),值必须是 `data:image/...;base64,` 前缀的 data URL(裸 base64 报 "Invalid format for image_urls[0]")。
- **413 Payload Too Large**:源图 >500KB 必须先压缩(PIL `thumbnail((1024,1024))` + `convert("RGB")` + JPEG q82 → 30-100KB);阈值 500KB 不是 1.5MB(0.8-1.4MB 的图不压也 413)。
- **并发**:同 key 并行任务不排队,3 并发实测 OK(约 1min/张×3 vs 串行 4-5min/张)。未试更高并发。
- 成本约 0.0085/张;单张 1024px。
- prompt 方向:产品图 + "科技感办公桌/现代办公场景" 重绘;整机=科技感办公桌,耗材=打印机旁工位;强调"保留产品外观完全一致"。

## 批量脚本模式(断点续跑)
- 遍历 xlsx 47 品(主图路径列)→ 每品:读图(>500KB 压缩)→ 提交 → 轮询 → 下载到 `产品图册/images/{序号}_{sku}.png`。
- **断点续跑**:跳过已存在且 >50KB 的输出文件;失败(413/网络)重试 3 次后标记,第二轮自动补(压缩后)。日志写文件(threading.Lock)。
- 素材图目录名 = xlsx SKU 码去掉 `-01` 后缀(整机套装 SKU 是 ASIN 无后缀);主图 URL 列是本地路径 `C:\Users\Administrator\Desktop\素材(1)\...`。
- 用户指定模型时(如"用 image2.0 生成")必须遵守,不要擅自换便宜的。

## catalog.html 产品图册填充(A4 一页一品)
- 模板结构:封面(品牌/标题/desc/联系) + 每品一页(.detail:head 分类+页码 / figure 图 / model+名称+slogan / specs 两列 / pricebar 批发价) + 价目总表页。出片=浏览器 Ctrl+P 另存 PDF(边距无/背景图形开)。
- **SKU 明细区块**(2026-08-13 新增):多 SKU 商品在 specs 下渲染 `.skus` 列表,每行 = 圆点 + 颜色名(label 只取 `" / "` 第一段,防换行 `white-space:nowrap` + ellipsis) + SKU 码 + 单价;单 SKU 商品不显示。
- **A4 防溢出**:43 色(PLA Basic)一行一个物理放不下 → **≤16 个 SKU 一行一个,17-28 两列,>28 三列**(grid auto-fill 不行,须显式列数);主图 height 68mm + 行距紧凑(4-6px padding)保证零溢出。验证:headless 逐页量 pricebar.bottom vs page.bottom。
- 拿货价=售价÷2 取整;运费整机/套装 60、耗材/配件 8 USDT(用户 clarify 确认口径)。
- 价格条删右下角"厂家拿货价/运费"块后仅留批发价大字(用户 2026-08-13 要求)。

## 采集原链接提取
- 每素材目录有 `商品信息.txt`,含 ASIN/商品链接(Amazon UK 或 uk.store.bambulab.com);链接 = `https://www.amazon.co.uk/dp/{ASIN}` 或 `https://uk.store.bambulab.com/products/{目录名}`。47 品汇总 txt 脚本:按 SKU(-01 后缀匹配)读商品信息.txt 的「商品链接」行。

## 交付偏好
- AI 生成图**直接 MEDIA 发图给用户看**,不要先自评;用户看完才批量。
- 用户说"先做几个模板出来我看看,哪个最快先做哪个"→ 先做 2-3 个风格模板(同一款商品数据)给用户挑,再落批量。
- 本地预览用 `python -m http.server 8766` + Chrome 打开 `http://127.0.0.1:8766/...`(file:// 中文路径会打不开/图片不加载)。
