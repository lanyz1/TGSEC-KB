# apimart.ai 异步生图 API(2026-08-13 实测)

中转站 https://apimart.ai,v1 接口 OpenAI 兼容但生图为**异步任务模式**。模型列表含 gpt-image-1/1.5/2、dall-e-3、gemini-3.x-image、flux-2/kontext、seedream 等(2026-08-13 时点)。

## 端点

| 用途 | 方法/路径 | 说明 |
|---|---|---|
| 提交生图 | `POST /v1/images/generations` | 返回 `{"code":200,"data":[{"status":"submitted","task_id":"task_..."}]}` |
| 轮询任务 | `GET /v1/tasks/{task_id}` | `status` ∈ submitted/processing/completed/failed;completed 时 `result.images[0].url[0]` 为图片 URL |
| 查模型 | `GET /v1/models` | Bearer key 鉴权 |

## 请求体(图生图/编辑)

```json
{
  "model": "gpt-image-2",
  "prompt": "Professional product photography: place this exact 3D printer on a modern tech desk...",
  "image_urls": ["data:image/jpeg;base64,<b64>"],
  "size": "1024x1024",
  "n": 1
}
```

- 图生图字段名是 **`image_urls`**(数组),值必须是 `data:image/xxx;base64,` 前缀格式——裸 base64 报 400 `Invalid format for image_urls[0]. Only http/https URL or data:image base64 are supported.`
- 纯文生图可不带 image_urls

## 关键坑(全部实测)

1. **必须带浏览器 User-Agent 头**:urllib 裸请求 → `HTTP 403 error code 1010`(Cloudflare)。加 `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0` 即通。curl 也一样要带。
2. **payload 上限**:请求 JSON 过大 → `HTTP 413 Payload Too Large`。实测 0.8~1.4MB 的 base64 图都会 413;压缩到 <100KB 稳过。**阈值建议:素材图 >500KB 先 PIL 压缩(thumbnail 1024 + JPEG q82)**,重试 3 次仍 413 = 压缩没生效(检查压缩分支是否触发)。
3. **异步轮询**:间隔 8s;单张(带图编辑 1024px)实测约 40~70s 完成,高峰期可能 2~5 分钟。
4. **并发**:多个任务同时提交会**并行执行不排队**(实测 2 任务同时 processing、3 并发稳定);无并发数限制提示,保守用 3~5。
5. 任务完成 25 秒级文生图样例成本 `cost:0.0085`(约 0.0085 计价单位/张),47 张 < 0.5 计价单位——很便宜,批量放心跑。

## 下载结果图

`result.images[0].url[0]` 形如 `https://getapib.org/f/image/<id>.png`,带 UA 头 GET 下载,有效期约 1 天(`expires_at`)。

## 生产可用脚本

见 `scripts/batch_gen_images.py`(3 并发 + 大图压缩 + 断点续跑 + 日志),改 `SRC`(商品 xlsx)/`OUT_DIR`/prompt 模板即用。API key 从环境变量 `APIMART_KEY` 读取,勿硬编码。
