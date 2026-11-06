---
name: human-px-press-hold-captcha
description: Use when 打 HUMAN/PerimeterX「按住」press-hold 验证.
---

# HUMAN Security / PerimeterX「Press & Hold」人机验证对抗

适用：Microsoft 注册 / 任意站点出现「证明你不是机器人 + 长按该按钮」或 `#px-captcha`、`hsprotect.net`、`px-cloud.net` 元素时。
家族关系：属于 `captcha` 家族卡（极验/腾讯/网易/CaptchaFox）的 HUMAN/PX 分支；本卡独立成文。

## 0. 铁律

1. **先解剖、后按压**：不看帧内状态就按压 = 盲打。一次失败尝试可能触发风控升级。
2. **别重复已证失败的通道**（见 §4），每次尝试都要换一个变量（时序/行为/漏斗/载具）。
3. **每次尝试留三连取证**：压持中 / 释放后 1s / 释放后 4s（+ 整页），并按裁决截图归档。
4. 裁决失败时 widget 会**重载**（按钮行短暂消失=重载中）并显示「请再试一次」；成功则**父页跳转**（检测 URL/标题变化）。

## 1. 结构解剖（必做，5 分钟）

- 挑战宿主：`iframe.hsprotect.net`，典型 360×90；父页坐标用 `getBoundingClientRect()` 定位。
- `#px-captcha` div 内还有一个**嵌套 iframe**：`title="人工验证挑战"`、带 **128 字节 hex `token` 属性**（按压后常变 `display:none`）。
- 伴生：`js.px-cloud.net` 传感器帧、`fpt.live.com` 1×1 遥测壳（Microsoft 场景）。
- 常见**双实例**：一个带 `ch_ctx=1`（可见）、一个 0×0 辅助实例。

探针要点：
- `connect_over_cdp` 下 **OOPIF 帧仍可 `evaluate`**（不要因为 `pg.frames` 里 URL 为空就以为探不到）；递归 `fr.child_frames` 找嵌套挑战帧。
- 对每个 hsprotect 帧 dump：`document.readyState`、`document.body.innerText`、`document.documentElement.outerHTML`（元素数常仅 11–15 个，可全量读）。
- **读 bootstrap JS**：能拿到 postMessage 协议（`captcha` / `rendered` / `block` / `setToWindow` / `focus` / `cookie`）、`document.cookie` 转发钩子（`_pxvid/_px3/_pxde` 回传父页）、`XMLHttpRequest` 钩子（`collector-<appid>.hsprotect.net`）、错误上报 `collector-a.px-client.net/api/v1/collector/clientError`。

## 2. 坐标定位

- 视口 `dpr=1` 时**页坐标 1:1 映射**，可直接给 CDP 输入。
- 按钮 = 浅色描边胶囊（空闲态）；用**截图放大 + vision 读图**定位中心（例：视口 929×917 → 按钮中心 (490,628)）。
- 不要用 OS 级 `GetCursorPos` 反推 Δ（见 §4）。

## 3. 按压序列（人形）

1. 曲线接近（含轻微过冲）→ 悬停 150–400ms；
2. `mouse.down` → 压持；压持中加 ±1px 微颤（10–40 次）；
3. **释放时机 = widget 自身完成信号**（而非固定秒数）：压持期间每 400–700ms 读一次 widget 帧的 `innerText`/class，出现完成/校验中提示后再释放（人反应差 200–600ms）；
4. 释放后不立即移走，停留 1–2s。

> 固定长压（>10s）与过早释放都曾被判失败；**以帧内状态为准**。

## 4. 已证失败通道（勿重复投入）

| 通道 | 失败原因 |
|---|---|
| 无障碍通道（点击「可访问性挑战」链接） | 点击未被登记，组件回滚 |
| OS 级 `SetCursorPos`+SendInput | `screenX/Y` 与系统游标 Δ 不恒定（有真人/远程会话在用鼠标）→ 不可用；若必须用，先用页面 `mousemove` 监听校准 Δ 并复验两次 |
| HeadlessChrome / `navigator.webdriver=true` 的浏览器载具 | 直接识别 |
| 纯直线鼠标轨迹 | 被判机器人 |

## 5. 打法优先级（按性价比）

1. **会话养熟**：按压前 30–45s 自然行为（移动+停顿+悬停链接+轻微滚动），不做 100% 脚本化点击链路。
2. **智能释放**：见 §3.3（读 widget 状态）。
3. **换注册漏斗**：同一服务常有多个入口（Xbox / Teams / Outlook Web / 第三方 OAuth 的 `wreply` 引导），风险引擎策略可能不同 —— 找一个没有 HUMAN 面的入口往往比硬刚便宜。
4. **出口信誉**：PX 会按 IP 质量打分；换干净出口（住宅/新节点）再试。
5. **指纹面**：移动端 UA/触摸模拟（`Input.dispatchTouchEvent`）作为变体。
6. 最后才考虑 OS 级注入（需校准，见 §4）。

## 6. 载具纪律（坑）

- 真实 Chrome + `--user-data-dir` 独立档案 + 指定 socks 出口 + `--lang`；用前先 `curl http://127.0.0.1:<port>/json/version` **探活**——CDP Chrome 会自然退出（表现为 `connect ECONNREFUSED`），报告前/继续前必须重启载具。
- 探到 `navigator.webdriver=false` 只是入场券，不等于能过评分。
- 脚本族命名：`<target>_px1..pxN.py`，每步只做一件事（定位 / 几何 / 按压 / 读状态）。

## 7. 输出物

- 帧结构 dump（含 token 属性与 postMessage 协议片段）
- 按钮几何坐标
- 每次按压的三连取证图 + 裁决截图
- 裁决结论：通过（父页跳转）/ 失败（「请再试一次」+ widget 重载）/ 无响应
