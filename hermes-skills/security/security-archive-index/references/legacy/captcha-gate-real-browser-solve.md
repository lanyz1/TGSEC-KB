<!-- archived from /root/.hermes/skills/security/captcha-gate-real-browser-solve/SKILL.md on 2026-10-21 -->

---
name: captcha-gate-real-browser-solve
description: "Use when 滑块/人机校验挡在受控端点前: 真浏览器真鼠标过闸取 token, 并让 App 自己把请求发出去。"
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
---

> 归档卡：原目录 `/root/.hermes/skills/security/captcha-gate-real-browser-solve`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/captcha-gate-real-browser-solve/…')`，不要相对 `references/legacy/` 解析。

# 人机校验闸 · 真浏览器过闸取证

只解决一件事：受控端点要一个**人机校验产物**（腾讯 `ticket`/`randstr`、极验 `validate`、易盾 `token`、自研 `captcha_token`/`x-verify`）才放行，
而你要在**几十发以内**拿到它并完成取证。需要批量/无人值守时另走协议复刻（补环境 + 逐轮生成遥测的路线已另有技能卡）。

配套（同库）：`spa-request-contract-extraction`（其《UI 驱动取证》节 + `references/browser-driven-request-capture.md`）= 路线 B 的 harness。

## 触发

- 端点回笼统码（`非法请求，请从首页重新登录` / `参数错误` / 统一 401），而 bundle 显示该端点载荷里带验证码字段。
- 弹窗由**站点自己**创建（`TencentCaptcha` / `NECaptcha` / `initGeetest`），你手上没有可直接复用的产物。
- 页面自己给了线索：`CAPTCHA has already been rendered`、`errorCode:...`、`ret!==0`。

## 决定树（先选路线再动手）

1. 一次性/少量过闸 ⇒ **路线 A：真浏览器 + 真鼠标拖拽**（首选，零协议逆向）。
2. 挑战产物一次性且与发起会话绑定，手工复刻恒被拒 ⇒ 接 **路线 B：让 App 自己发**。
3. **Cloudflare Turnstile**（无弹窗、无拖拽，只有一个 `getResponse()` token）⇒ **路线 C**。
4. 需要并发/规模化/无人值守 ⇒ **才**轮到协议复刻。

## 路线 A：真浏览器 + 真鼠标拖拽

1. **必须 headed 真桌面 Chrome**（CDP attach）＋真 UA。无头下厂商 SDK 的 `enableAutoCheck` 通常不放行。
2. `nav` 到**目标站自己的页面**（同源；跨源页内脚本发请求会被 CORS/风控挡），等弹窗出现。
3. `Page.captureScreenshot` → **只裁弹窗矩形**再做视觉读图（全屏图里滑块占比太小，读不准）。
4. 读两个 x：**拼图块左缘**（白描边块）与**缺口左缘**（深色实心凹槽）⇒ `d = 缺口x - 块x`；
   同时读出**手柄按下点**的整图坐标（拖拽起点是手柄，不是块）。
5. 发真鼠标事件 `Input.dispatchMouseEvent`：
   - `mousePressed` at `(x0,y0)`，`button:"left"`、`buttons:1`、`clickCount:1`；
   - ~30 步 `mouseMoved`：`x = x0 + d*(1-(1-t)^3)`（三次缓出），`y` 叠加 `random.uniform(-1.2,1.2)`，步间隔 12–30ms 不等；
   - `mouseReleased` 同点。
6. **成功判据看页面自己的状态**（组件 `form.ticket` 被写入 / `cap_union_new_verify` 回 `errorCode:0`），**不是**看弹窗是否消失。
   失败就重截一张重新读图重拖——同一实例可重试。
7. 产物**立刻**用（TTL 常是分钟级、且一次性）。

完整事件参数 / 读图几何 / 与协议路线的关系见 `references/slider-real-browser-drag.md`。

## 路线 B：让 App 自己发

手工拼请求恒回同一句笼统码时（即便挑战产物 + 会话令牌齐带），**不要继续猜参数**：闸做在请求上下文上。
做法 = 装 XHR+fetch 录制器（加载前注入）→ 走**真路由**（`$router.options.routes` dump 出独立路由，别用弹窗切换方法）
→ 填表 → 处理挑战 → 点**站点自己的提交按钮** → 读录音拿真 URL/真参数，响应里的会话令牌立刻落盘。
harness 代码形态见 `spa-request-contract-extraction` 的 `references/browser-driven-request-capture.md`。

## 路线 C：Cloudflare Turnstile（隐形/管理型）

turnstile 与滑块是两回事：没有弹窗、没有拖拽、没有可读的几何，只有 `window.turnstile.getResponse()` 里的一串 token。

1. **必须 headed**。`--headless=new` 下 widget **静默不渲染**：`typeof window.turnstile === 'object'`（脚本已正常载入）
   但 `getResponse()` 恒为空串、页面 `iframe` 数为 0，**且不发任何错**。headed 实例通常 5~10 秒内自动出 token（实测 len≈794~816）。
   ⇒ 见到「脚本在、token 空」先换 headed，别去改 sitekey、也别去补环境。
2. **靠 SPA 内部导航进入表单**：既不要 `goto` 受控页 URL，也不要自己 `turnstile.render(div,{sitekey})`——
   前者 SPA 初始化路径没跑，后者 widget 建得出来但永不回调。
   做法：`goto 首页 → 在页内点站点自己的入口（如导航栏「登录」）→ 轮询 getResponse()`。
3. **隐形 widget 查不出 iframe**：即便 token 正常产出，`document.querySelectorAll('iframe')` 也可能为 0。
   唯一判据是 `getResponse()` 非空 ⇒「找不到 sitekey 元素 / 没有 widget DOM」**不能**推断闸门不可过。
4. **token 与 sitekey 绑定、同一站点跨 scene 可复用**：登录 / admin 登录 / 下单 / 兑换各 scene 用同一 sitekey 的 token 都认（服务端按 scene 选 secret）。
   sitekey 常明文躺在**公开配置端点**里（如 `/api/v1/public/config` 的 captcha 段，连启用 scene 列表一起给）—— 优先从那里取，不要靠抠 DOM。
5. **一次性 + 分钟级 TTL**：取到立刻在**同页** `fetch()` 发出（同源 + `credentials:'include'`，不触发预检、可带自定义头），不要跨发复用。

脚本形态、失败现象对照表、多出口注意点：`references/turnstile-token-harvest.md`。

## 单例与凭证纪律（最容易白烧轮次的两条）

- **`TencentCaptcha` 每个 document 只允许一个实例**：自建第二个报 `CAPTCHA has already been rendered`
  ⇒ 借站点实例（`.show()` 由站点按钮触发），产物从站点组件里读：
  `setCaptcha(){ new TencentCaptcha(cap_iframe,g,this.callback,{enableAutoCheck:!0}).show() }`；
  `callback(A){ if(A.ret===0){ this.form.ticket=A.ticket; this.form.randstr=A.randstr } }`。
- **一次性产物 + 同轮会话**：产物必须与其 challenge 同轮；跨轮/跨会话复用 = 假阴性（不是「目标防住了」）。

## 缺口定位：默认视觉读图，不要先写图像算法

| 自动算法 | 失败机制 |
|---|---|
| 行最小值 / 游程法 | 背景暗纹比缺口更暗，`rowmin` 被纹理主导 |
| 局部中值背景差分 | 高频纹理 + 块与背景同色 ⇒ 分不出来 |
| 局部方差「平坦度」 | 光滑着色背景（岩石/渐变）**全图皆平坦** ⇒ 判据无区分度 |

⇒ **截图 → 视觉读图 → 给一个 dx**。每次一张，成本可接受。可复用几何：拼图块起始左缘 ≈ `warp.x + 45.5`；
同一站点内弹窗几何稳定（换页面只整体平移，先重标定一次裁剪原点），**跨站点必须重标**。

## 交付

- 过闸证据三件套：挑战弹窗回执（`errorCode:0` / `ret===0`）+ 页面表单里产物非空 + 用该产物打受控端点的业务成功响应。
- 把「裁剪原点 + dx + 手柄坐标 + 产物字段名」记成本轮常量供后续页面复用。
- 产物按凭证处理：不写进报告正文、不写进总结。

## 坑位

- 别把笼统码一律读成「缺少某字段」——先分「缺凭证」与「必须页面自发」两相，两者后续动作完全不同。
- 别用无头 Chrome 硬试：厂商对无头有专门处理，纯白烧轮次。Turnstile 的表现尤其阴 —— **脚本正常载入但 token 恒空**（`typeof window.turnstile==='object'`、不发错），最容易被误读成「sitekey 不对 / 需要补环境」。
- 别在「弹窗消没消失」上判成败：判页面状态。
- 别自建挑战实例：单例限制会让你把轮次花在 `already rendered` 上。
- 真鼠标拖拽与协议复刻不是二选一：**一次性取证走真鼠标，规模化才上协议**。
