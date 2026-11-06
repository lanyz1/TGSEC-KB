<!-- archived from /root/.hermes/skills/creative/ai-image-generation-api/SKILL.md on 2026-10-21 -->

---
name: ai-image-generation-api
description: "Use when generating AI images via multi-model API gateway."
---

> 归档卡：原目录 `/root/.hermes/skills/creative/ai-image-generation-api`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/creative/ai-image-generation-api/…')`，不要相对 `references/legacy/` 解析。

# AI 生图 API 管线(多模型网关 · 人像写真 / 证件照 / 电商素材)

触发词: AI 写真、结婚照、换发型、证件照、换装、人像一致性、APIMart、批量素材、电商主图。

## 触发场景
- AI 写真 / 结婚照 / 换发型 / 证件照 / 换装 / 人像一致性
- 用 APIMart 等 OpenAI 兼容聚合网关出图(一个 key 调多模型、统一计费)
- 批量素材生产(电商主图 / AI 模特 / 落地页素材)
- 自用集成站的引擎层(内部素材工厂 + 对外接单服务台)

## 引擎选型(APIMart 实测,2026-09)

| 场景 | 首选 | 依据 |
|---|---|---|
| **人像一致性**(写真/证件照/婚纱) | `gpt-image-2-official` | 用户亲测最像;16 参考图、mask 局部重绘、透明背景、单次 4 张 |
| 批量素材 / 极速出图 | `seedream-4-5` | 8-19s 出图、$0.026/张 |
| 多参考融合 / 图层 / 精修 | `seedream-5-0-pro` | 10 参考图、图层拆分、精确像素 |
| 备胎 | `gemini-3.1-flash-image-preview`(Nano Banana 2)、`qwen-image-3.0` | 出图快但脸部相似度弱于 gpt-image-2 |
| 极速草稿 | `z-image-turbo`、`flux-*` | 便宜量大的初筛 |

成本量级:单张 $0.006-0.06(≈¥0.05-0.42);18 张多模型对比总花费 < $0.5。任务响应自带 `credits_cost` 可直接记账。

## 必备工作流(严格按序)
1. **上传参考图** `POST /v1/uploads/images`(multipart,字段名 `file`)→ 拿公网 URL
2. **提交生成** `POST /v1/images/generations` → 返回 `task_id`(**全系异步,不是图**)
3. **统一轮询** `GET /v1/tasks/{task_id}?language=zh` → `status=completed` 后取 `result.images[].url[]`
4. **立即下载落盘**(链接 24-72h 过期,响应带 `expires_at`)
5. 缩略图内联给用户 → **用户本人判断"像不像"**(他是唯一权威,不要替他下结论)
6. 需交付时裁标准尺寸(证件照:一寸 295×413 / 二寸 413×579)

多模型对比: **并行提交全部任务 → 统一轮询**,不要串行等每个任务。

## 关键坑(全部实测踩过)

- **`image_urls` 一律字符串数组** `["https://..."]`。传 `[{"url": "..."}]` 会 400(`cannot unmarshal object into ... type string`)——全系模型统一,别按上传文档里的对象写法抄。
- **`size` 白名单**:`1:1 / 16:9 / 9:16 / 4:3 / 3:4 / 3:2 / 2:3 / 5:4 / 4:5 / 2:1 / 1:2 / 21:9 / 9:21 / 3:1 / 1:3`,或直接传像素串 —— **像素宽高必须是 16 的倍数**。证件照 5:7 比例 → `1184x1664`(1184=16×74,1664=16×104)。
- **内容审核红线**:提示词含"酒 / 微醺 / 酒吧 / 酒红色"→ 整任务失败 `task_failed 内容安全系统拒绝了你的提示词或输入`。改成"深红色""城市高层餐厅"即可通过。**模板库必须内置违禁词过滤**。
- **单张正脸参考图的硬伤**:姿势侧身时模型会把脸扳回正脸(身体侧、脸正,观感违和)。提示词必须显式写"头部必须随身体一起转向,不要把脸扭回正面"并声明目标角度(3/4 侧、90° 侧);**根治 = 多角度参考图**(正脸 + 左右侧脸 30°/60°)。
- **证件照必须显式声明**:嘴唇自然闭合(原图微张时要点名)、正面直视不倾斜、双肩水平对称、面部无阴影无过曝、不过度美颜磨皮、头部占画面上部约三分之二。少写一条就不合规。
- 网关 chat 端点:gemini 系列可能默认 SSE 流式 → 显式 `"stream": false`;若走推理模型用 `-nothinking` 变体,否则 reasoning tokens 吃光 `max_tokens` 导致正文截断(`finish_reason: length`)。

## 看图(主模型无视觉能力时的替代方案)
用网关自己的多模态 chat 模型当"眼睛":上传图拿 URL → `POST /v1/chat/completions`,content 里放 `{"type":"image_url","image_url":{"url":...}}` → 让它输出人物特征 JSON(性别/年龄/脸型/五官/发型/拍摄角度/服装/取景/光线/背景),再据此设计写真提示词。首选 `gemini-2.5-flash-nothinking`(快、便宜、中文准)。

## 提示词结构(模板引擎骨架)
题材锚定 → 主体 → 服装 → 场景 → 光线 → 道具 → 质感 → 防AI痕 → 构图+画质

例:`专业婚纱摄影照片:一对年轻中国情侣,新娘穿精致白色拖尾婚纱,新郎穿黑色西装,站在海边悬崖草坪上,日落金色逆光,白色花艺拱门,电影感色调,皮肤质感真实自然,构图大气唯美,超高清细节`

人像一致性提示词要额外叠加:**参考图身份声明 + 保持一致声明 + 角度控制声明 + 防美颜声明**。详见 `references/prompt-templates.md`。

## 用户偏好(本项目上下文)
- 后台界面简体中文;素材即商品(COD 场景)
- 交付 = 小图内联展示 + 原图落盘 + 标准尺寸裁切文件;原图路径一并给出
- 选型结论由用户亲测拍板(他判断像不像),不要替他断言
- 集成站定位:一个后台两条线 —— 内部素材工厂 + 对外接单服务台

## 复用脚本
`scripts/apimart_multimodel_run.py` —— 多模型并行提交 / 统一轮询 / 下载落盘 一条龙(含场景模板定义)

## 参考文件
- `references/apimart-api.md` —— 端点/参数/响应结构/错误码/模型清单/环境配置
- `references/prompt-templates.md` —— 场景模板库(婚纱/写真/证件照/电商素材)+ 提示词结构拆解
