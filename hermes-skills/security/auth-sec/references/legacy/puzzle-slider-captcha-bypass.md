<!-- archived from /root/.hermes/skills/security/puzzle-slider-captcha-bypass/SKILL.md on 2026-10-21 -->

---
name: puzzle-slider-captcha-bypass
description: "Use when 绕过 GoCaptcha(go-captcha) 拼图滑块验证码。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/puzzle-slider-captcha-bypass`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/puzzle-slider-captcha-bypass/…')`，不要相对 `references/legacy/` 解析。

# 拼图滑块验证码绕过（GoCaptcha / go-captcha）

处理 Go 后端常见的开源拼图滑块库 `wenlng/go-captcha`（ModeBasic 模式），以及同类的拼图挖空滑块。商业验证码（极验 GT3/GT4、腾讯 TDC、易盾、数美、云片、360 天御、顶象）走 `captcha` skill，不在此列。

## 触发条件

- 目标有 `/go/api/slide/get`、`/slide/check` 端点，或响应含 `tile_x/tile_y/tile_base64/image_base64/reg_token`。
- 前端是 Go 后端 + 拼图滑块（AI 应用站、Dify 类平台常见）。

## 核心认知（最关键坑）

`slide/get` 返回的 `tile_x/tile_y` 是拼图块**初始显示位置**（`random(5, dp)`，dp=30），**不是缺口位置**。

- 缺口（半透明深色阴影）绘制在 `block.X`，经 Left 死区修正后 `block.X ∈ [88, 238]`（中右区域）。
- 校验规则 `|block.x - targetX| <= padding(5)`；`point` 提交格式是 `"X,Y"` 字符串。

## 绕过链（全自动，无需浏览器拖动）

1. `GET slide/get` → 拿 `id`、`image_base64`（背景 300×220）、`tile_base64`（拼图块 63×63）、`tile_x`、`tile_y`、`reg_token`（滑块凭证，注册时提交）。
2. 解码背景图，阴影检测（暗部 vs 高斯模糊 + 拼图掩码）或边缘轮廓匹配（FIND_EDGES）定位缺口；缺口在右侧，中心 X≈175、Y 与 `tile_y` 一致。
3. `POST slide/check` body `{"id":..., "point":"<缺口中心X>,<tile_y>"}` → 返回 `{"code":100000,"msg":"ok"}` 激活 `reg_token`。
4. 用 `reg_token` 作为注册接口的滑块凭证字段，完成注册。

## 高频坑

1. 别把 `tile_x` 当缺口 X 提交——`tile_x` 是初始位置（5-30），缺口在右侧 88-238，差一个数量级。
2. `point` 的 Y 用 `tile_y`（缺口垂直位置与拼图块初始 Y 一致）。
3. 目标常对非浏览器 UA/TLS 指纹拦截 → 脚本用 curl 子进程 + 浏览器 UA 头替代 urllib。
4. 缺口检测优先纯 numpy（阴影检测或边缘匹配）；scipy 版本冲突（`_ARRAY_API not found`）时改纯 numpy。
