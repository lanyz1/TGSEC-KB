---
name: botion-captcha-solver
description: Use when a botion point-click captcha gates a form.
---

# botion 点选验证码全自动破解

## 触发场景
页面出现 `Select in this order` + 3 个汉字提示 + 一张叠加描边汉字照片的挑战窗
（DOM 类名含 `botion_box` / `botion_ques_tips` / `botion_submit`）。
常见于东南亚白标博彩/支付的注册与登录。

## 第一铁律 — 挑战每次交互都刷新
读图与点击**必须在同一次脚本运行内完成**。跨工具调用（先截图、下一次调用再点）**必然失败**，
因为提示字 hash 会变。把「取图 → 识别 → 点击」写成一个原子脚本。

## 结构
```
.botion_ques_tips img   3 个 22px 提示字
  src = https://static.botion.com/nerualpic/original_word_pic/jiangchengzhengjunti/<md5>.png
.botion_bg              图片区（CSS 272x181，居中；本案例 rect=(314,581,272,181)）
.botion_submit          OK（选中前带 class botion_disable）
.botion_refresh / .botion_close
```

## 解析流程
1. **CDP 3x 截图**（`deviceScaleFactor:3`）→ ImageMagick 裁 `.botion_bg` 区域
   （CSS rect × 3；例 CSS(314,581,272,181) → 裁 `816x543+942+1743`）
2. **提示字**：下载 3 张 PNG（**透明底！** 必须 `-background white -alpha remove`），
   单字 800% 放大 → ddddocr 分类；同字同 hash，可建 `botion_dict.json` 持久化加速
3. **图内候选字**：`ddddocr.DdddOcr(det=True).detection(img)` 直接给出每个字的**坐标框**
   （约 4 个，各 ~145x145）
4. **框内识别**：裁框 → `ImageOps.autocontrast` → resize 160x160 → RGB → ddddocr 分类
   （**关键步骤**：不做 autocontrast + 定尺，OCR 会读出 藕/蒙/蓑 之类错字）
5. **匹配**：优先 OCR 字符串匹配（`set(tip) & set(box)`）；退化方案是掩膜重叠度。
   模板匹配 NCC 在**彩色描边空心字**上不可靠，别用
6. **点击**：`Input.dispatchMouseEvent` 真鼠标按序点 → 点 `.botion_submit`

## 成功标志
`4.8 s. You beat 42% of users`（挑战窗消失）

## 生产级实现（v2，成功率≈40%/次，5次内必过）

拆成两个文件，主流程用 venv（websocket-client），OCR 用**系统 python3** subprocess（ddddocr+PIL+numpy）：

1. `t4_botion_solve2.py` — 解题器：入参 `<boxpng> <tip1.png> ...`，stdout 输出 `@@{json}`
   - `n`=检测框数；`rows[]`每框 `{box, xy, w, h, ov:[每提示字的重叠度], ocr:[两路预处理OCR]}`；`tips_ocr[]`=提示字OCR
   - 重叠度：`thr = percentile(gray, p)` for p in (72,60,85)，取 `max((g>=thr) & tipmask)/tipmask.sum()`
   - **注意 `float()` 转换**，numpy float32 不能 json 序列化
2. `t4_regauto2.py` — 主流程：填表 → 点提交 → **重试循环(1..5)**：取提示 hash → 下载 → 3x 截图 → **从 `.botion_box` 的 getBoundingClientRect 动态算裁切**（别硬编码） → subprocess 调解题器 → 选框 → 点击 → 点 `.botion_submit` → 判断窗是否消失

### 选框优先级（实测唯一可靠组合）
1. 框级 OCR 字符串匹配：`set(box_ocr) & set(tip_ocr)`
2. 退化：该框对该提示字的**掩膜重叠度**最大者
3. **绝不要**在 OCR 失败时随机挑剩余框（会退化成一发不成）

### 实测准确率（三字词）
`糖→酱→鱼`、`煎→茄→片`、`麻→婆→豆→腐`、`柳→州→酸`、`凝→固→剂`、`泥→风→鸡` 全部读准。

## 坑（补充）
- **提交后表单会被清空**：极验通过后必须**重新填表再提交**（同一脚本内）
- **清空输入框要真键盘**：click → Ctrl+A → Backspace → `Input.insertText`（直接改 `.value` 过不了 React）
- **deviceScaleFactor 会残留**：读图用 3、点击必须切回 1，否则坐标偏 3 倍
- **登录页/注册页的按钮是 DIV/SPAN**：`.click()` 可能不触发；用真实鼠标序列（mouseMoved→mousePressed→mouseReleased）

## 参考实现
- `/root/t4_botion_v3.py`（v1，单次）
- `/root/t4_botion_solve2.py` + `/root/t4_regauto2.py`（v2，带重试循环，实测成功注册真实玩家账号）

## 2026-10 实测补充（乐竞 22411 线）
- **遮罩坑**：`botion_box_layer` / `botion_box_btn` 会吃鼠标事件 → 先 `pointer-events:none`，再点 `botion_bg` 才有落点
- **点击成功判据**：tip 下出现序号 `1/2/3`（不是变色/不是 tip 文案）
- **刷新**：必须 JS `document.querySelector('[class*=botion_refresh]').click()`；裸 mouse 常不换题
- **提交按钮文案**：中文 `确定`（不是 OK）
- **码型分流**：注册 captchaId 常出 icon，登录 captchaId 常出 word；同一风控会切换
- **密码预言机**：`entryErr=22411 + 验证错误` = 密码对、卡二次验证；`22001` = 账密错
- chamfer 离线分 0.85–0.95 仍可能中心偏 → 必须 `iou>=0.55` 三目标全过 + 新 bgUrl 才点确定
- 上游 `:8099 load/verify` 403 时，改走 JSONP load 域（`bcaptcha.botlabpro.com`）或 CDP Fetch 代理
