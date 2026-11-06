# APIMart 生图 API 速查(2026-09 实测)

聚合网关:一个 key 调 362 个模型(图像类 78 个),OpenAI 兼容,人民币/积分计费。
文档:`https://docs.apimart.ai/cn`、索引 `https://docs.apimart.ai/llms.txt`、中文手册 147 页 `https://docs.apimart.ai/_llms/cn/api.md`。
抓文档要用代理(本机直连 docs 返回 000)。

## 环境
- Base URL: `https://api.apimart.ai/v1`
- 认证: `Authorization: Bearer <key>`
- key 获取: https://apimart.ai/keys
- 本机访问必须走 v2rayN 代理 `http://127.0.0.1:10808`(直连超时 http 000)
- 项目工作区约定:`D:\ai-studio\poc\`(key 放 `.apimart_key`,参考图 URL 放 `ref_urls.txt`)

## 端点

### 1. 上传图片
```
POST /v1/uploads/images      # multipart, 字段名 file
→ {"bytes":210885,"content_type":"image/jpeg","created_at":...,"filename":"...","url":"https://getapib.org/image/..."}
```

### 2. 生成(全系异步)
```
POST /v1/images/generations
{
  "model": "gpt-image-2-official",
  "prompt": "...",
  "size": "3:4",            # 白名单比例 or 像素串(16 的倍数)
  "resolution": "2k",       # 部分模型支持 1k/2k/4k
  "n": 1,                   # gpt-image-2 最大 4
  "image_urls": ["https://..."]   # 必须是字符串数组!
}
→ {"code":200,"data":[{"status":"submitted","task_id":"task_01K8..."}]}
```
错误:400 invalid_request_error / 401 身份验证失败 / 402 余额不足 / invalid_size。

### 3. 任务状态
```
GET /v1/tasks/{task_id}?language=zh       # 支持 10 种错误文案语言
{
  "code":200,
  "data":{
    "id":"task_...","status":"completed",   # submitted/processing/completed/failed
    "cost":0.15,"credits_cost":1.5,"progress":100,
    "result":{"images":[{"url":["https://upload.apimart.ai/f/image/..."],"expires_at":1763174708}]},
    "created":...,"completed":...,"estimated_time":60,"actual_time":19
  }
}
```
失败:`status=failed`, `error.message="内容安全系统拒绝了你的提示词或输入。"`

### 4. Webhook(可选,免轮询)
提交任务时带回调地址,完成(成功/失败)主动 POST 结果。

### 5. 其他
- `GET /v1/models` → 全量模型列表(返回 362 个)
- `GET /v1/uploads/images` 上传;余额:`/v1/dashboard/billing/credit_grants` 不存在(404),用任务响应的 credits_cost 记账
- chat: `POST /v1/chat/completions`(多模态看图,见下)

## 实测模型价格/耗时(同一提示词,3:4)

| 模型 | 耗时 | 单张 cost | credits |
|---|---|---|---|
| seedream-4-5 | 8-19s | $0.026 | 0.26 |
| gpt-image-2-official | 22-36s | $0.0063-0.0176 | 0.063-0.176 |
| qwen-image-3.0 | 18-35s | $0.0206-0.0229 | 0.206-0.229 |
| seedream-5-0-pro | 29-53s | $0.0585-0.2925* | 0.29-2.93* |
| gemini-3.1-flash-image-preview | 18-87s | $0.02 | 0.15-0.20 |

*seedream-5-0-pro 人像参考图任务实测 0.2925 credits;示例文档另见 2.93。
1 credit ≈ $0.1。

## 图像模型 ID(实测可用)
- 字节 seedream: `seedream-4-0` / `seedream-4-5` / `seedream-5-0-lite` / `seedream-5-0-pro`
- OpenAI: `gpt-image-1` / `gpt-image-1-mini` / `gpt-image-1.5-official` / `gpt-image-2` / `gpt-image-2-official` / `gpt-image-2.5-flare` / `gpt-image-2.5-sunburst` / `chatgpt-image-latest`
- Google: `gemini-2.5-flash-image-preview(-official)` / `gemini-3-pro-image-preview(-official)` / `gemini-3.1-flash-image-preview(-official)` / `gemini-3.1-flash-lite-image(-ext)` / `imagen-4.0-apimart`
- 阿里: `qwen-image-2.0(-pro)` / `qwen-image-3.0(-pro)`
- 万相: `wan2.7-image` / `wan2.7-image-pro`
- 其他: `flux-2-pro/max/flex` / `flux-kontext-pro/max` / `z-image-turbo` / `grok-imagine-image-2.0` / `midjourney`

## 看图(多模态 chat 替代本地视觉)
```
POST /v1/chat/completions
{"model":"gemini-2.5-flash-nothinking","stream":false,"max_tokens":900,
 "messages":[{"role":"user","content":[
   {"type":"text","text":"...输出人物特征 JSON..."},
   {"type":"image_url","image_url":{"url":"<上传返回的 URL>"}}]}]}
```
坑:
- `gemini-2.5-flash` 默认 SSE 流式(`data: {...}`),需显式 `"stream": false` 或自己解析 SSE
- 推理型模型 reasoning tokens 计入 max_tokens,200 时正文只剩几个字(`finish_reason: length`)→ 用 `-nothinking` 变体或把 max_tokens 提到 900+
- `gpt-4o` / `claude-sonnet-4.5` 等别名可能不存在或 500 `get_channel_failed`(供应商通道),先 `GET /v1/models` 校验真实 ID
