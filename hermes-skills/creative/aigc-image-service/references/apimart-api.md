# APIMart API 知识库(2026-09-09 实测验证)

聚合网关 https://apimart.ai/zh。一套 OpenAI 兼容 key 访问 500+ 模型,统一计费、路由、余额监控。积分 1 分 = $0.1。

## 端点速查

| 用途 | 方法/路径 | 说明 |
|---|---|---|
| 模型列表 | `GET /v1/models` | 需 auth;实测 362 模型,image-like ~78 |
| 文/图生图 | `POST /v1/images/generations` | **异步**:返回 task_id |
| 任务状态 | `GET /v1/tasks/{task_id}?language=zh` | status: submitted/processing/completed/failed;语言参数控制错误文案 |
| 上传图片 | `POST /v1/uploads/images` | multipart 传图 → `{url}` → 填 image_urls |
| 任务回调 | 提交时带 webhook 回调地址 | 完成主动 POST,可省轮询 |
| 余额 | dashboard/billing 端点 404;从任务响应 credits_cost 记账最准 | |

## 提交响应(必须兼容两种形状)

seedream 系 → data 是**数组**:
```json
{"code":200,"data":[{"status":"submitted","task_id":"task_01K8SGYNNNVBQTXNR4MM964S7K"}]}
```
其他模型 → data 可能是对象。解析:取 `d["data"][0]["task_id"] if isinstance(d["data"],list) else d["data"]["task_id"]`。

## 完成响应(轮询结果)

```json
{"code":200,"data":{
  "id":"task_01KA040M0HP1GJWBJYZMKX1XS1","status":"completed",
  "cost":0.15,"credits_cost":1.5,"progress":100,
  "result":{"images":[{"url":["https://upload.apimart.ai/f/image/...png"],"expires_at":1763174708}]},
  "estimated_time":60,"actual_time":19}}
```
- `cost` USD / `credits_cost` 积分(=cost×10)。图片 URL **24-72h 过期**,完成即下载。
- 视频任务 result 里是 `videos`,音频是 `audio`/`music`,按模型族区分。

## 图像模型清单(2026-09 实测 ID)

| 模型 ID | 家族 | 关键参数/能力 | 实测 3:4 一张 |
|---|---|---|---|
| seedream-4-5 | 字节 | 文/图生图/编辑,默认 2K | 8s / $0.026 |
| seedream-5-0-pro | 字节 | **10 参考图融合/图层拆分/坐标交互编辑**,1K/1.5K/2K 或精确像素,单图 | 53s / $0.0585 |
| seedream-5-0-lite | 字节 | 2K/3K,PNG/JPEG,URL 72h | - |
| seedream-4-0 | 字节 | 旧版 | - |
| gpt-image-2-official | OpenAI 官方 | 文/图生图/**局部重绘 mask**,15 比例,1K/2K/4K,单次 4 张,参考图 16,PNG/WebP 透明底 | 35s / $0.0063 |
| gpt-image-2.5-flare / -sunburst | OpenAI | 16 参考图,5 档质量 | - |
| gemini-3.1-flash-image-preview | Google(Nano Banana 2) | 14 参考图,极端比例(1:4~8:1),文+图 | 87s / $0.02 |
| gemini-3-pro-image-preview | Google | 异步高质量 | - |
| qwen-image-3.0 / -pro | 阿里 | 1-3 参考图编辑,1K/2K,单次 6 张;pro 版图文密集排版强 | 35s / $0.021 |
| wan2.7-image / -pro | 万相 | 1K/2K/4K(pro 文生图最高 4K),计费按成功张数不分分辨率 | - |
| flux-2-pro/max/flex / flux-kontext | 海外 | 风格强 | - |
| imagen-4.0-apimart | Google | **仅文生图**,5 种比例 | - |
| grok-imagine-image / -2.0 | xAI | 1-12 张,$0.08/张,URL 72h | - |
| midjourney | MJ | 独立风格 | - |
| z-image-turbo | 轻量快速 | 双语提示词,智能改写 | - |

人像/写真一致性主力选 seedream 系(字节电商素材事实标准)与 gpt-image-2 系(参考图最多);婚纱人像专项可加通义万相直连作为对照。

## 文档发现路径(web_extract 不稳时 curl -x 代理)

- `https://docs.apimart.ai/llms.txt` → 总索引
- `https://docs.apimart.ai/_llms/cn/api.md` → 中文 API 手册 147 页索引(全是页面链接+一句话简介,抓一次即可全局搜索)
- 具体页 `https://docs.apimart.ai/cn/api-reference/{族}/{模型}/generation.md`、`uploads/images.md`、`tasks/status.md`、`tasks/webhook.md`
- ⚠️ `https://docs.apimart.ai/api-reference/openapi.json` 是 plant-store **占位 demo**,不是真 spec
- ⚠️ 官网定价页是 Next.js 动态渲染,静态抓不到价;以实测任务 `credits_cost` 为准

## 行业参照(2026-09 调研,用于选型与定价)

- 妙鸭相机:21 张照片训分身,29.9 元(限时 9.9),日活峰值 60 万,2025-09 团队解散。
- Seedream 4.0 官方渠道:$0.02-0.04/张,单次最多 9 张一致性图、6 张参考图、最高 4K、2K 约 1.8s。
- 即梦 AI 月活 1352 万;可灵视频全球份额 ~30%(2025-05 Poe 数据)。
- 集成站毛利测算:API 成本 0.05-0.42 元/张,对外卖 99 元/9 张套(生成 8-12 张挑 4-9)毛利 ~97%。
