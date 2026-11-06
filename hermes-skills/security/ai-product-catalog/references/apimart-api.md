# apimart.ai 生图 API(中转站,gpt-image-2 等)

2026-08-13 实测验证的完整用法。Key 由用户提供(敏感,不写入任何库/技能)。

## 端点与认证

- 提交:`POST https://apimart.ai/v1/images/generations`
- 查询:`GET https://apimart.ai/v1/tasks/{task_id}`
- 认证:`Authorization: Bearer {KEY}`
- **必须带浏览器 User-Agent**,如 `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0`——urllib 默认 UA 直接 403 Cloudflare(error code 1010);curl/requests 带 UA 正常

## 异步任务模式(不是同步返回!)

1. 提交返回:`{"code":200,"data":[{"status":"submitted","task_id":"task_xxx"}]}`
2. 轮询 task_id,`data.status` ∈ processing/completed/failed
3. 完成:`{"data":{"status":"completed","result":{"images":[{"url":["https://getapib.org/f/image/...png"]}]}}}`——下载 url[0](同样带 UA)
- 单张实测:50-100 秒(文生图小图 ~25s,图生图 1024 更久),成本 ~0.0085/张
- 任务查询免费,提交后立即轮询即可

## 图生图/编辑(产品图换背景)

```json
{
  "model": "gpt-image-2",
  "prompt": "Professional product photography: ... keep the product design exactly the same ...",
  "image_urls": ["data:image/jpeg;base64,<b64>"],
  "size": "1024x1024",
  "n": 1
}
```

**坑**:
- 字段名是 `image_urls`(数组),**不是 `image`**;裸 base64 报 `invalid_request_error: Invalid format for image_urls[0]. Only http/https URL or data:image base64 are supported`
- data URL 必须带 `data:image/jpeg;base64,` 前缀
- **413 Payload Too Large**:图片 base64 提交过大。实测 797KB-1.4MB 的图片直接提交 413,压缩后(<100KB)成功。阈值约为图片 ~800KB(未精确探明),**提交前统一压缩到 <500KB**:
  ```python
  from PIL import Image; import io
  im = Image.open(io.BytesIO(raw)); im.thumbnail((1024, 1024))
  buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=82); raw = buf.getvalue()
  ```

## 并发

- 同 key 多任务**并行执行不排队**(实测 2 个任务同时 processing)
- ThreadPoolExecutor max_workers=3 稳定提速(47 张:串行 ~4-5 分钟/张 → 3 并发 ~1 分钟/张)
- 可测 4-5 并发,但 3 已足够

## 可用生图模型(2026-08 实测列表)

gpt-image-1 / gpt-image-1.5 / **gpt-image-2**(用户指定)、dall-e-3、gemini-2.5/3.x-flash-image-preview、gemini-3-pro-image-preview、doubao-seedream-5、flux-2-flex/max/pro、flux-kontext-max/pro

## 批量生产要点

- 断点续跑:输出文件已存在且 >50KB 跳过
- 进度日志:`open(LOG,"a")` + print,线程安全要加 threading.Lock
- 失败重试 3 次(413 是参数问题,压缩后再试)
- 素材图命名:输出 `{序号:02d}_{SKU}.png`,SKU 取自 xlsx SKU 明细第一个 `|xxx|` 段
