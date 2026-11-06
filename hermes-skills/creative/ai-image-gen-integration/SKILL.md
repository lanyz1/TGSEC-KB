---
name: ai-image-gen-integration
description: AI生图/写真站建设:APIMart网关接入与人像一致性实测选型。触发:AI写真, 结婚照, APIMart, 生图。
---

# AI 生图/写真 API 集成工作流

把"用户照片 → 多模型出图 → 交付"链路做通,并为集成站(素材工厂/接单台)选引擎。当前用户方案 = **APIMart 单网关**(一个 key 管 362+ 模型),后续 FastAPI 后台。项目工作目录 `D:\ai-studio\poc\`(key 在 `.apimart_key`,参考图 URL 在 `ref_url.txt`,已跑通脚本为 `poc_*.py`)。

## 核心链路(每步已实测通过)
1. **上传底图**:`POST /v1/uploads/images`(multipart field `file`)→ 返回 `url`(形如 `https://getapib.org/image/...`)
2. **让多模态 LLM 看图**(当主对话模型无视觉时,这就是"眼睛"):chat/completions 传 `image_url`,用 **`gemini-2.5-flash-nothinking`**(便宜快;thinking 变体会把 max_tokens 吃光只回半句话)。拿到 JSON 人物特征(性别/年龄/脸型/发型/穿着/取景)
3. **构造提示词**:`参考照片中的是一位<人脸描述>。保持她的面部特征五官脸型发型完全一致、可辨识为同一人,置于场景:<场景描述>。真人实拍质感,不要动漫化`。中文提示词对 seedream/qwen 友好
4. **逐模型提交**:`POST /v1/images/generations`(OpenAI 兼容格式,但**全部模型都是异步**——立即返回 `task_id`,不是图)
5. **统一轮询**而非串行:全部提交完再循环 `GET /v1/tasks/{task_id}?language=zh`,4s 间隔;避免逐模型等满
6. **立即下载**:URL 24-72h 过期(`expires_at`),completed 后马上落盘
7. **缩小转 JPEG**(PIL `thumbnail 700-900px + JPEG q85)供桌面内联 MEDIA: 展示 —— 原图可能 5-6MB 太大

## APIMart 事实速查(详细:references/apimart-api-notes.md)
- base `https://api.apimart.ai/v1`,header `Authorization: Bearer <key>`;**本机需走 v2rayN 代理 `http://127.0.0.1:10808`**(直连 HTTP:000 不通;curl/requests 都过代理)
- 提交响应 `{"code":200,"data":[{"status":"submitted","task_id":...}]}`(数组或对象都兼容解析)
- 完成响应 `data.result.images[].url[]` + `expires_at`;计费 `cost`(USD)/`credits_cost`(积分,**1 积分 ≈ $0.1**)
- **`image_urls` 必须是字符串数组 `["url"]`**,不是 `[{"url":...}]` → 否则报 `cannot unmarshal object into Go struct field Alias.image_urls of type string`(seedream/gpt/gemini/qwen 全统一)
- 模型真实 ID 以 `GET /v1/models` 为准:是 `seedream-4-5` 不是 seedream-4.5;图像类有 `seedream-4-5 / seedream-5-0-pro / seedream-5-0-lite / gpt-image-2-official / gpt-image-2.5-flare / gemini-3.1-flash-image-preview / qwen-image-3.0 / wan2.7-image / flux-2-pro / imagen-4.0-apimart / grok-imagine-image-2.0 / midjourney`
- `size` 传比例字符串 `"3:4"` 通用;测试档 `resolution` 用 2K 足够判质
- 图像类模型 **没有同步接口**,提交→轮询是唯一路径;Webhook 存在(任务提交带回调地址),将来规模化再上

## 实测模型画像(2K 档,2026-09)
| 模型 | 耗时 | credits/张 | 定位 |
|---|---|---|---|
| seedream-4-5 | 8-35s | 0.26 | 快/便宜,主力批量 |
| gpt-image-2-official | 22-36s | 0.06-0.18 | 最便宜,参考图保真强 |
| qwen-image-3.0 | 18-35s | 0.20-0.23 | 快 |
| gemini-3.1-flash-image-preview (Nano Banana 2) | 18-87s | 0.15-0.20 | 慢但强 |
| seedream-5-0-pro | 29-53s | 0.29 | 旗舰:多参考融合10张/图层拆分,人像一致性首选 |

## 选型方法论(用户实测偏好 — 勿跳步)
- 用户明确 **"先实测出图看效果再定站"**:新引擎/新方案先拿 key 实测,不要直接开搭架构
- 选人像一致性模型:**同场景 × N 模型矩阵对比,把图发给照片本人判断"哪张最像我"** —— 本人判断比任何自动评估准
- 先用 2 个代表性场景(大场景换装 + 贴近本人气质场景)筛模型,胜出后再铺开剩余场景,控制成本
- 一次跑多图并行提交→统一轮询,不要串行等待

## Pitfalls
- **MSYS/bash 的 `/d/` 路径给 Windows 原生 python 会写错**:`open("/d/ai-studio/...")` 落到 `C:\d\...`。python 写文件必须用 `D:\ai-studio\...` 原生路径
- 主对话模型无视觉时,本地 `vision_analyze` 对文件返回 `[Unsupported Image]` 属预期 —— 不要反复重试,直接用 APIMart 多模态 LLM 看图(见链路 2)
- gemini 系 chat 默认 SSE 流式:要么显式 `"stream": false`,要么解析 `data: ` 行
- 部分模型偶发 `get_channel_failed` 500 —— 换同族模型(gpt-4o 失败换 chatgpt-4o-latest / gemini)重试
- 图片 URL 过期即失效(24-72h),任务完成立刻下载,别攒着

## 项目状态(续做起点)
- 已完成:链路打通、5 模型画质对比、2 场景×5 模型人像一致性对比(海边白纱裙/韩系咖啡店)
- 待做:用户选定像的模型 → 铺开 汉服/晚礼服/职业/海岛 场景 → Phase1 FastAPI 后台(任务队列:提交→轮询→落盘 + 素材工厂页,简体中文后台)
- 商业背景与成本测算见 references/aigc-market-notes.md
- 可复用脚本:scripts/apimart_gen.py(上传→多模态描述→多模型生成→轮询→下载)
