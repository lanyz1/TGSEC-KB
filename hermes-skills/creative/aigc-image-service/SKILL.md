---
name: aigc-image-service
description: "AI写真/结婚照/发型/素材等AI生图服务集成站搭建: APIMart网关异步接入+模型实测选型。"
---

# AI 生图商业服务 / 集成站搭建

为"自用 AI 生图集成站 / AI 写真 / AI 结婚照 / AI 发型试戴 / 电商素材工厂"类项目做市场判断、网关接入与模型选型。2026-09 实证。中文交付,技术术语保留英文。

## 一、市场结论(先判断定位,再动手)

1. **纯 2C 卖图小程序已死**:妙鸭相机(2023 上线,21 张照片训数字分身,9.9-29.9 元,日活峰值 60 万,排队 4000+)2025-09 团队解散 —— 死于大厂把同能力免费内置(即梦/可灵/豆包/通义)。不要做"下一个妙鸭"。
2. **钱在三处**:① 细分场景**服务代做**(AI 结婚照/全家福/百天/宠物,一套 99-399 元,小红书/闲鱼案例引流私信成交);② **B 端素材生产**(电商主图/AI 模特上身/落地页,单张外包 50-200 元 vs API 成本 0.2 元);③ 本地生活**获客钩子**(理发店 AI 试发型 → 到店转化,卖的是到店不是软件)。
3. 技术壁垒≈0:壁垒在流量/交付流程/审美/模板积累。底层模型**不自己训、不本地部署**(用户主服无 GPU),全走云 API 网关。

## 二、产品架构模式(用户已选定:一个后台两条线)

- **内部素材工厂**(商品图/模特上身/批量变体/尺寸管理,直连 COD 后台素材目录)+ **对外接单服务台**(客户照片→数字分身→套餐→生成→**人工审核挑片**→无水印交付,先手动确认收款)。
- 硬约束:引擎抽象层**第一天就做**(provider 路由,随时换模型/网关);任务**全异步**(提交→轮询/回调→落盘,生成 10-90s 同步会卡死);生成 URL 有时效必须立即下载;人脸敏感数据最小留存、生成完删原图(妙鸭被点名教训)。
- 分期: P1 MVP=FastAPI+SQLite+任务表状态机+单网关多模型+素材工厂页;P2 模板库/批量/尺寸;P3 接单台/审核/交付;P4 多引擎+Redis+OSS+海外 VPS。

## 三、APIMart 网关接入(已验证可跑)

- Base `https://api.apimart.ai/v1`,OpenAI 兼容,统一 key 统一计费。`GET /v1/models`(需 auth)现返回 362 模型、约 78 图像类。
- 生图 `POST /v1/images/generations` **异步**:提交即返回 task_id。参数:`model/prompt/size("3:4" 比例或像素)/resolution(1K/2K/4K)/n/image_urls(参考图)/watermark/optimize_prompt_options`。
- 轮询 `GET /v1/tasks/{task_id}?language=zh` → `status=completed` 后 `result.images[].url[]`,带 `expires_at`(24-72h,必落盘)、`cost`、`credits_cost`。
- 参考图:先 `POST /v1/uploads/images` 拿 URL,再填 `image_urls`(也支持 base64 混填)。
- 完整端点/任务 JSON/模型角色/文档路径 → `references/apimart-api.md`;多模型跑分脚本 → `scripts/poc_gen.py`(读同目录 `.apimart_key`)。

## 四、实测/选型工作流(已跑通)

1. `GET /v1/models` 过滤 image 关键词拿**真实模型 ID**(是 `seedream-4-5` 不是 seedream-4.5;`gemini-3.1-flash-image-preview` 即 Nano Banana 2)。
2. 同提示词多模型**并行提交→统一轮询**,记录耗时/cost/credits(脚本已封装)。
3. 下载后**出图给用户内联看**(MEDIA: 路径),文本模型无视觉时别硬评,效果判定交给用户。
4. 按业务线定主备(2026-09 实测价):
   - 低价快速素材:`seedream-4-5`(8s / $0.026≈0.19元)
   - 旗舰精修/多参考融合:`seedream-5-0-pro`(10 参考图/图层/精确像素,$0.0585)
   - OpenAI 系 16 参考图/局部重绘 mask:`gpt-image-2-official`(实测最便宜 $0.0063≈0.05元)
   - 备胎:`qwen-image-3.0`、`gemini-3.1-flash-image-preview`、`wan2.7-image`、`flux-2`、`imagen-4.0-apimart`、`grok-imagine-image`
5. **关键第二关 = 人像一致性**(用户照片→换婚纱场景仍像本人),决定能否商用;需用户提供授权正脸照,一次只改一个变量做差分。

## 五、网关/中转站可信性校验(2026-09 实测报道:428 家中转站,26 家"动手脚")

- 结论:第三方 AI 中转/聚合网关普遍存在**降级模型(挂 A 模型之名跑 B 模型)、留存/回传提示词与产物、篡改输出**的问题;"1 块钱 285 万 Token"的便宜额度,代价可能是数据
- 选网关/换网关前跑一次校验(四项,10 分钟):
  1. **同 prompt 双跑对比**:官方直连 vs 网关,比对输出指纹(风格、能力边界、拒绝行为、上下文窗口长度)→ 明显降级 = 有中间层
  2. **唯一 token 探针**:提示词里塞一段一次性随机串,看是否出现在别处(回传/共享池复用)
  3. **计费核对**:申请额度与实际 token 消耗比例对不上 = 中间层改写(截断/缓存/换模型)
  4. **稳定性/超时形态**:同一模型不同时段响应差异大 = 动态路由到廉价后端
- 架构要求(建站交付时写进方案):**网关必须可替换**,核心链路保留"切官方直连"的开关,不要硬绑单一中转站;有 SLA/发票/可直连的官方 API 优先用于生产链路,中转站只用于压测与低成本批量
- 来源: https://www.freebuf.com/articles/ai-security/500215.html

## Pitfalls(实测踩坑)

- 提交响应 `data` 可能是**数组**(seedream 系 `data[0].task_id`)也可能是**对象** → 解析必须兼容两种,别写死。
- 任务结果 URL 过期快(24-72h)、文件大(0.5-6.5MB PNG):完成即下载落盘,别存 URL。
- `docs.apimart.ai/api-reference/openapi.json` 是 plant-store **占位 demo**,不是真 spec。
- 文档索引:`/llms.txt` → `/_llms/cn/api.md`(147 页索引),具体页在 `/cn/api-reference/.../xxx.md`。
- 定价页是 Next.js 动态数据抓不出 → **实测扣费最准**(任务响应的 `credits_cost` 即真实成本;1 积分 = $0.1)。
- 本机直连 api/docs.apimart.ai 不通(HTTP:000),requests 需显式 `proxies={"http":"http://127.0.0.1:10808","https":...}`(v2rayN 代理)。
- web_extract 多后端不稳(403/Unrecognized MCP shape)时:curl -x 代理抓 markdown 文档最快最稳。
- 视觉通道收不到本地大 PNG 时:Pillow 缩到 900px JPEG 供显示;最终效果判定始终交用户。
