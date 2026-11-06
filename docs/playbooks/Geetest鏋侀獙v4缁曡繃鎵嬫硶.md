---
title: "Geetest极验v4绕过手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# Geetest极验v4绕过手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/geetest-captcha-bypass/SKILL.md`

## 汇总内容

### geetest-captcha-bypass

来源：`/root/.hermes/skills/security/geetest-captcha-bypass/SKILL.md`

# GeeTest v3 (极验) 滑块验证码自动化

## 触发条件
- 目标页面出现 `initGeetest({...})`、`gt`/`challenge` 参数、`geetest_canvas_bg` / `geetest_canvas_slice` / `geetest_canvas_fullbg` canvas、`Slide to complete the puzzle`、"Powered by Geetest"
- 登录/注册被极验滑动拼图拦截，ddddocr 无效（它是字符验证码 OCR，不适用于滑块）

## 架构（v3 标准流程）
```
前端: initGeetest({gt, challenge, product:'bind', new_captcha})
 → 用户滑动 → captchaObj.getValidate() → {geetest_challenge, geetest_validate, geetest_seccode}
后端: POST /validate_captcha/ {gt, challenge, geetest_validate, geetest_seccode} → captcha_token
 注册/登录 携带 captcha_token 提交
```
- `get_captcha/` 端点通常**服务端直连可用**（无 CF 挑战），返回 `{success:1, gt, challenge}`
- 极验 v3 服务端 get.php：init 返回 `c`/`s`；**不要二次调用 get.php**（报 `old challenge` / `error_02`）
- 完整服务端求解需逆向 `w` 参数加密（fullpage.js/slide.js 混淆极深，工程量巨大，成功率低）→ 优先浏览器路线

## 本库入口（先跑这个）

```bash
python3 tools/ops/captcha_auto.py doctor
python3 tools/ops/captcha_auto.py solve --url https://授权站/login --case <案卷>
# 弹出滑块但脚本没找到按钮时：
python3 tools/ops/captcha_auto.py slide --url https://授权站/login --case <案卷> --click 'button[type=submit]'
# 全自动：cp config/captcha_keys.env.example config/captcha_keys.env 后填 Key
python3 tools/ops/captcha_auto.py detect --url https://授权站/login --case <案卷> --browser
python3 tools/ops/captcha_auto.py token --url https://授权站/ --case <案卷> # 自动用 detect 抽到的 id
```

`--url` 必须在 scope。默认 **有头** Chromium + 真鼠标；不要加 `--headless`。 
滑过之后 storage 同时写入 `测绘/captcha_auto/` 和 `接管/session/`，可直接 `cf_session.py consume`。 
登录 HTML 没有 ID 时：`harvest --path <案卷>` 或 `detect --probe-api`（`getSysInfo` / `getGeeCaptcha` / `vccgeetest.com`）。 
canvas 跨域污染时改用截图算缺口。字母图走 `captcha_auto.py ocr`。

## 浏览器自动化路线（实测有效）

### 0. 先过 CF 页面挑战
- **headless Playwright 会被 CF/极验识别**（fill 超时、页面不渲染）→ 用 **Xvfb + headed**：
 `xvfb-run -a python script.py` + `p.chromium.launch(headless=False, args=['--no-sandbox','--disable-dev-shm-usage','--disable-blink-features=AutomationControlled'])`
- `ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")`
- SPA 渲染慢：goto 后 **sleep 5-6s** 再操作；输入框可能无 placeholder/name → `page.locator('input').nth(i)` 按索引填
- 页面内 fetch 测极验连通：`api.geetest.com/gettype.php` / `static.geetest.com` / `api.geevisit.com` 应 200（proxy 下也通）

### 1. 关键：必须用真实输入事件（isTrusted=true）
| 方式 | 结果 |
|---|---|
| JS 合成 `MouseEvent`/`PointerEvent` dispatch | ❌ isTrusted=false → 极验忽略，滑块保持 `geetest_ready` |
| CDP `Input.dispatchMouseEvent` | ✅ 原生输入 |
| Playwright `page.mouse.move/down/up` | ✅ 原生输入 |
- 滑动后有 `geetest_fail`（而非 ready）= 事件被接收、仅位置判错 → **这是正确信号，调整距离重试**
- 人类化轨迹：mousedown 停顿 0.2-0.4s → 缓启动→加速→减速 → 末端微回弹 → mouseup；步进 2-12px 随机

### 2. 缺口定位（canvas 像素分析，页面内 evaluate）
- `geetest_canvas_bg` 列梯度找峰值：`Σ|px(x)-px(x+1)|` per column，排序取 top3（间隔>18-20px）
- `fullbg`(完整背景) vs `bg`(挖缺) 逐列差：缺口=连续高差异段；仅 bg 可用时列梯度
- slice canvas alpha 掩码模板匹配在 bg 中滑动找最小 RGB 差（缺口宽 40-50px）
- 滑动距离 = 缺口 pageX − 滑块按钮中心 pageX（按钮中心 = rect.x + width/2）
- 距离不准时循环：fail → 点 `.geetest_refresh` 拿新图 → 重新算 → 重滑

### 3. 代理（需换 IP 时）
- 历史任务脚本常有可用 SOCKS5 池，测 `ifconfig.me/ip` 确认出口
- **Chromium 不支持 SOCKS5 认证** → 换出口用仓库池里的 **HTTP** 节点（`本机IP被封换出口代理.md`），`captcha_auto.py --proxy`；禁止 SSH 用户主机搭转发
- 无认证连接通常被拒（认证必填）

### 4. 直接接管 Hermes 浏览器（备选）
- Hermes browser 的 CDP 端口在 `/tmp/agent-browser-chrome-*/DevToolsActivePort`
- 裸 websocket-client 连 CDP 会 403：需 `Origin: http://127.0.0.1:<port>` 头（`--remote-allow-origins` 未开时）
- Playwright `connect_over_cdp` 可连，但**可能重置 Hermes 会话**（页面变空）→ 优先独立 launch

## 极验错误语义（排障关键）
| 现象 | 含义 |
|---|---|
| 面板 "Timed out" + Retry | challenge 失效/加载超时（滑动前已过期）→ 点 refresh 重取 |
| "Network failure 113" | 极验 SDK 内部请求失败（仍可能与 challenge 生命周期相关） |
| `old challenge` (error_02) | 二次 get.php 或 challenge 复用 |
| slider `geetest_ready` 滑动后不变 | 事件未生效（合成事件） |
| slider `geetest_fail` | 事件生效、位置错错 → 调距离重试 |

## 硬墙判断
极验 v3 + CF 组合下，若 challenge 被服务端一次性失效（每次 get_captcha 返回即作废），纯自动化在无住宅代理/真人设备下**可能无法突破**（Cornix 实测）。穷尽后如实交付信息泄露面成果，不要无限循环滑块。

## 支撑文件
- 滑块实战：`python3 tools/ops/captcha_auto.py solve --url … --case …`（本库无 `http2socks.py`）

## 真源

- 手法：`docs/playbooks/Geetest极验v4绕过手法.md`


---

## 外部库增量（2026-10-11 分享包）

## 0-A 先判模式：离线(降级)校验 ⇒ 一行绕过（★ 最高优先级，先试这个）

拿 `act=captcha` / `get_captcha` 的返回体，先看两个字段：
- **`gt`**：若 `gt == md5("123456")`（= `e10adc3949ba59abbe56e057f20f883e`）或其它**公共测试 ID/示例值** ⇒ 服务端多半在用 Geetest **离线(宕机)校验**
- **`success`**：`success:0`（在线模式是 `success:1`）⇒ 非在线模式

离线校验 = 纯本地公式，**不需要真滑**：
```
geetest_challenge = <拿到的 challenge>
geetest_validate  = md5(challenge)        ★ 命中判据
geetest_seccode   = md5(challenge)        (或 md5(challenge)+"|jordan")
```
**通过判据**：业务

…（截断，全文见来源卡）
