---
name: gocaptcha-automation
description: "Use for go-captcha click/slide captcha automation."
version: 0.1.0
author: 骚母狗
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [captcha, gocaptcha, automation, playwright, vision]
---

# go-captcha Automation (click / slide)

破解 go-captcha（wenlng/go-captcha）的 click 点选与 slide 滑块验证码。识别特征：页面有 `img.gc-picture`、`.gc-drag-block`、`go-captcha` 类名；接口形态 `captcha/check`、`captcha/generate`、`captcha/verify`。

## 侦察

- 类型: `captcha/check?scene=<x>` → `default_type`（slide/click/...）
- 生成: `POST captcha/generate {id, type, scene}` → `{captcha_key, type, image(dataURL), thumb(dataURL)}`
- 验证: `POST captcha/verify {captcha_key, id, value}` → `{captcha_token}`

## 提交格式铁律（实测）

- **value 必须是字符串**。传对象/数组 → 服务端 500。
- **click**: 逗号坐标串 `"x1,y1,x2,y2,..."`（按点击顺序）
- **slide**: `"x,y"`（x=缺口左边缘在原图坐标；y=thumb_y 或 0）

## 时限

- **captcha_token TTL = 300 秒**（从 generate 起算）。提交必须 <300s。
- 前端 verify 失败 → 自动 refresh（换新题）。同一 key 服务端可多次尝试（实测 20+ 次无锁），但最好一次做对。

## click 解题流程

1. 用 crypto hook / DOM 取 image+thumb（base64）。
2. thumb（白字提示条）读取目标字符（vision 一次）。
3. 主图字符定位：**视觉读数**（vision 直接问坐标，多轮时取平均）或用**色相 blob 检测**辅助（cv2 HSV 高饱和区域，形状 30-60px）。
4. **小心形近干扰字**：议/认、辽/边、治/海、支/走——裁剪放大 5x 复核。
5. value = "x1,y1,x2,y2"（逗号分隔）。

## slide 解题流程（推荐全自动）

1. 取 image（300x220 背景+缺口）与 thumb（拼图块）。
2. **缺口定位**：vision 读「缺口左边缘 x」（直接问原图最准；或用 cv2 黑帽异常块）。
3. **Playwright 拖动闭环**：
   - 起点 = `.gc-drag-block` 中心（**不要点在 drag-slide-bar 空白处！事件绑在 block 上**）
   - `mouse.move→down`，先试移 +100px 测比例 k（实测 k≈0.98）
   - 目标屏幕坐标 = `img.gc-picture.x + 缺口x`；读取图上滑块小 img 的 boundingRect.x，逐步收敛到 ±5px
   - `mouse.up` → 点确认（`.gc-btn-block` 或 text=确认）
4. 全程实测 ~2 分钟/轮（含一次 vision）。

## 页面防护 patch（Playwright route 拦截，字符串替换后 fulfill）

- **disable-devtool**: `detectors:[1,3,4,5,6,7]` → `detectors:[]`
- **FingerprintJS BotD**: `.detect().bot&&(` → `.detect().bot&&!1&&(`
- **stealth init script**: navigator.webdriver=false、WebGL getParameter vendor/renderer 伪装 Intel、languages、window.chrome
- **明文抓取**: hook `SubtleCrypto.prototype.encrypt/decrypt`（ubcv4/自定义加密站的请求响应明文全部可见）

## 工具链坑

- **vision_analyze 不稳定**：大图（>900px）易超时；700-800px jpg 较稳；超时就缩小/重试。
- 子图裁剪复核时给视觉明确「显示尺寸/放大倍数 + offset」，否则读数系统性偏差。
- RapidOCR/ddddocr 对「半透明彩色+描边」渲染几乎无效；go-captcha 字表字体在 github.com/wenlng/go-captcha-assets（fzshengsksjw_cu / yrdzst_bold）可用于自建字形模板匹配。

## 案例锚点

- 哈希8（ha8e.cc）: csAgent login 用 click（value 逗号串，TTL300），注册页用 slide（拖动闭环）；反调试=disable-devtool+BotD。脚本: /root/cases/ha8e/pw_reg_drag.py。
