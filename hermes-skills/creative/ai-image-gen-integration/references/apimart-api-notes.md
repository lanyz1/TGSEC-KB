# APIMart API 对接笔记(2026-09 实测)

平台:https://apimart.ai/zh — OpenAI 兼容 AI API 聚合网关(500+ 模型,统一 key/积分/账单)。
文档走 llms.txt:`https://docs.apimart.ai/llms.txt` → 中文索引 `https://docs.apimart.ai/_llms/cn/api.md`(147 页索引),具体页 `https://docs.apimart.ai/cn/api-reference/<分类>/<slug>.md`。
**访问需代理**:docs/api 本机直连不通(HTTP:000),走 `http://127.0.0.1:10808`。

## 端点速查
| 用途 | 端点 | 说明 |
|---|---|---|
| 生图提交 | `POST /v1/images/generations` | **异步**。body: model/prompt/size("3:4")/resolution/n/image_urls |
| 任务状态 | `GET /v1/tasks/{task_id}?language=zh` | 轮询;completed 后取图 |
| 上传图片 | `POST /v1/uploads/images` | multipart `file` → `{"url": "https://getapib.org/image/..."}` |
| 模型列表 | `GET /v1/models` | 362 模型,图像类 78 |
| 聊天 | `POST /v1/chat/completions` | 部分模型默认 SSE 流式,显式 `stream:false` |
| Webhook | 提交时带回调地址 | 任务完成主动 POST(规模化用) |
| 余额 | 账户/令牌余额接口 | billing 端点不存在(404) |

## 关键格式
- 认证:`Authorization: Bearer sk-...`
- `image_urls`:**字符串数组** `["https://..."]`。传 `[{"url": ...}]` 报错:
  `cannot unmarshal object into Go struct field Alias.image_urls of type string`(seedream/gpt/gemini/qwen 全部统一为字符串数组)
- 提交响应:`{"code":200,"data":[{"status":"submitted","task_id":"task_..."}]}`(也可能是对象 data)
- 完成响应:
  ```json
  {"code":200,"data":{"id":"...","status":"completed","cost":0.15,"credits_cost":1.5,
    "result":{"images":[{"url":["https://upload.apimart.ai/f/image/..."],"expires_at":1763174708}]},
    "actual_time":19}}
  ```
  1 积分 ≈ $0.1;图片 URL 24-72h 过期(`expires_at`),**必须立即下载**
- `size` 支持比例字符串("1:1"/"3:4"/"9:16"…);gpt-image-2 系 15 种比例 + `resolution` 1k/2k/4k 档位计费
- 错误:`{"error":{"code":4xx,"message":"...","type":"invalid_request_error"}}`;`get_channel_failed` 500 = 上游通道抖动,换同族模型重试

## 图像模型 ID 清单(实测 /v1/models,2026-09)
字节:seedream-4-0 / seedream-4-5 / seedream-5-0-lite / seedream-5-0-pro
OpenAI:gpt-image-1 / gpt-image-1.5-official / gpt-image-2 / **gpt-image-2-official** / gpt-image-2.5-flare / gpt-image-2.5-sunburst
Google:**gemini-3.1-flash-image-preview**(+official/lite/ext)/ gemini-3-pro-image-preview / gemini-2.5-flash-image-preview / imagen-4.0-apimart
阿里:qwen-image-2.0 / qwen-image-3.0 / qwen-image-3.0-pro / wan2.7-image / wan2.7-image-pro
其他:flux-2-pro/max/flex / flux-kontext-pro/max / grok-imagine-image-2.0 / z-image-turbo / midjourney
视频(同 key 扩):seedance-1-0-pro~2-5 / sora2 / veo3 / kling 系 / wan2.6-3.0 / MiniMax-Hailuo 系 / Vidu Q3
聊天视觉:**gemini-2.5-flash-nothinking**(描述用,不吃 thinking token)/ gemini-2.5-flash(-thinking 会耗 max_tokens) / gemini-2.5-pro / chatgpt-4o-latest / claude-opus/sonnet 系

## seedream-5-0-pro 独有能力
多参考图融合(最多 10 张)、底图+最多 16 层图层拆分、坐标/手绘交互编辑、size 可精确像素、1K/1.5K/2K、单次 1 张、PNG/JPEG 输出、返回平台存储 URL。人像一致性/商品精修首选。

## 实测成本(2K 档,单位 credits,1 credit≈$0.1≈¥0.72)
seedream-4-5:0.26 | gpt-image-2-official:0.06-0.18 | qwen-image-3.0:0.20-0.23 |
gemini-3.1-flash-image-preview:0.15-0.20 | seedream-5-0-pro:0.29 | 耗时 8-87s 不等
→ 单张成本 ¥0.05-0.42,批量测试成本可忽略;对外 99 元/9 张套毛利 >97%
