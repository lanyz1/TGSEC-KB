<!-- archived from /root/.hermes/skills/security/captcha-solving/SKILL.md on 2026-10-21 -->

---
name: captcha-solving
description: "Use when CAPTCHA blocks login/register: solve or bypass."
version: 0.1.0
tags: [captcha, geetest, slider, svg, ocr, vision, cloudflare]
---

> 归档卡：原目录 `/root/.hermes/skills/security/captcha-solving`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/captcha-solving/…')`，不要相对 `references/legacy/` 解析。

# 验证码解算 / 绕过（卡登录注册时用）

核心纪律：**先找「非交互偏门」（明文/字段名/框架旁路），再上「视觉解算」**；一切解算都在同一会话/进程链里当场消费（多数验证码一次性）；每步都记清请求形状与错误文案。

与限速配合看 `app-layer-login-ratelimit`（一次性验证码 = 每发攻击 1 次解算 + 2 请求的成本模型）。

## 0. 先做：链路形状侦察（≤5 分钟，永远先做）

- **字段名必须从前端 bundle 读**：实测某站字段真名 `captchaCode`，瞎猜 `captcha` 会永远「验证码错误」（服务端把缺字段当错误值）。grep bundle 里 captcha 附近的请求装配代码。
- **框架旁路**：FastapiAdmin 系 = `Referer: /docs` 免验证码（非生产环境判定）；其他框架找 enable/开关/白名单参数。
- **判服务端是否真校验**：对比「缺字段」「空值」「错值」三种响应文案；如「不能为空」= 校验在、但可能仅存在性检查。
- **判一次性消耗**：同 sessionId 第二次提交 → 「已失效」= 一次性；失败也消耗 → 每发攻击都要新解算。
- **判范围**：改 Device-Type（pc/android/ios/miniapp…）逐一试 —— 有的站只对 h5 强制、有的全强制；全强制则接受成本或 pivot。

## 1. SVG / 文本类（直接读源码，别 OCR）

- 服务端渲染 SVG 验证码时，答案常直接躺在 `<text>` 元素里：`''.join(re.findall(r'<text[^>]*>([^<]*)</text>', svg))`。零 OCR、毫秒级。
- 若有 decoy 元素风险：渲染成图 + 视觉读图对照，确认哪个集合 = 服务端期望（实测一组 text 内容全对但被拒 = 可能有变换/decoy，再对几个样本找规律；找不到就别死磕）。
- ddddocr 对「位图文字」尚可；对矢量渲染（字体差异/旋转）反而弱 → SVG 站永远优先读源码。

## 2. 极验 Geetest v4 点击题（word/icon）—— 视觉接力解算流水线 ⭐

已实战全破（注册成功消费）。架构 = patchright(Xvfb, 过 CF、开弹窗、真鼠标点击) + 外部解算（下载题图→定位坐标） + **文件握手**（脚本存素材→轮询 coords.json→收到坐标后点击→提交；支持跨工具调用边界的人工/视觉接力）。

**头号血坑（连败 3 次的根因）：题面素材必须实时从「弹窗已显示的 DOM」读取**：
- 背景图 = 可见元素的 CSS `background-image` url
- 目标词/图标 = 弹窗内可见 `<img>` 的 src（按 x 排序 = 点击顺序；实测 24x24）
- ❌ 用捕获的 /load 网络响应里的 imgs/ques = 与当前显示不同步（预载/刷新竞态），题面错位 → 点对也判失败。
- 自检：下载的 background url 与弹窗显示元素 url 必须一致。

其他实战点：
- 打开弹窗：填表合法 + 勾选协议 + 点提交（或触发按钮）后弹窗才出现；v-show 隐藏按钮用真鼠标坐标点。
- 定位：图中字形 = 半透明白字/彩色小图，与黑色贴图风格差异大 → 模板匹配/匹配滤波器易退化（同一点吸所有目标）；实用解 = 合成带标尺/网格的大图 + 视觉模型读坐标（±3-7px 自然像素），失败自动刷新即新题面重来（限 5-8 轮）。
- 点击：真鼠标 page.mouse 按序点击；坐标换算 natural→displayed 用 rect 比例；点击后弹窗出现编号标记 = 点击已登记；提交后成功 = 弹窗关闭/成功文案；失败自动重置刷新。
- 消费：成功后立即把 validate 字段 spread 进目标请求（注册/登录同链）——`getValidate()` 产物 {lot_number, captcha_output, pass_token, gen_time}，注册 payload 直接展开这些键。
- 网络卡：CF 挑战站点全程走 patchright，别把 requests 塞进解算链；Tor 出口下截图/字体易超时，跳过截图。

## 3. 滑块类（自研 slider；半个已知领域）

- 协议从 bundle 读：init 返回背景图+拼图块+宽高（可能含 y）；verify 载荷 = sessionId + track{bgImageWidth/Height, templateImageWidth/Height, left(图像像素), top, startTime/stopTime(ms), trackList[{x,y,t,type:down/move/up}]}；成功返 token。
- 缺口 = 图中均匀灰色拼图形状：HSV 低饱和+低局部方差+轮廓筛选（可得 bbox），或放大渲染 + 视觉读边缘。窗口内常有多个相似灰色块 → 必须视觉复核。
- ⚠️ **半成品警告（实测未通）**：自研滑块常有隐藏「基础校验」（轨迹形状/时序/会话绑定），合成轨迹（等速直线/简单缓动）实测被拒（「基础校验失败」）；真鼠标慢速多步拖拽也有时完全不触发 verify（pointer 监听对事件序列敏感）。这条线在未拿下前不要向用户承诺，也不要把错误轨迹当真→必须现场迭代、拿服务端反馈说话。
- 能绕则绕：同站其他登录口/其他环境可能用旧式或带 Referer 旁路的验证码。

## 4. 响应预言机（配限速/多因素时）

- **MFA 预言机**：密码对但缺 MFA → 差异化响应（如 `mfa_required`）≠ 错误凭据 → MFA 开着也能纯爆破出正确密码（实测 Kite k8s 面板）。
- 开喷前先打 1 发已知错凭据摸响应面，别把校验层当完成层。

## 5. 配对式图形验证码（captcha_id + code_img）——国内 App/SPA 标配

实测（资金盘平台注册+登录同链，一次通过率高）：

- 形状：`GET /img_captcha?t=<ms>` → `{"code_img":"data:image/jpeg;base64,...","captcha_id":"<hex16>"}`；提交时 **code 与 captcha_id 必须成对回传**（字段名常 `image_code` + `img_code_id`，**从前端 chunk 读确切名**，别猜）。
- 解算：`ddddocr.DdddOcr(show_ad=False).classification(base64.b64decode(img))`，4 位数字命中率高；失败直接重拉新图（新 captcha_id 天然重置，不必同图重试）。
- 字段名先于识别率：报「验证码错误」时先核对 payload 装配（`handleRegister`/`handleLogin` 附近的字段），再怀疑 OCR。
- 无会话绑定：code+captcha_id 与账号请求同一 JSON body 提交即可（无 cookie 依赖），可纯 requests 自动化。

## 6. 阿里云二代验证码（FeiLin · CHECK_BOX/滑块）——国内站标配其二

实测（2026-10 资金盘注册链：过验证→注册成功；服务端真核验、一次性）：

- 形状：页面拉 `o.alicdn.com/captcha-frontend/aliyunCaptcha/AliyunCaptcha.js`；初始化 POST `https://<prefix>.captcha-open.aliyuncs.com/`（Action=InitCaptcha）→ 回 `{CertifyId, CaptchaType:"CHECK_BOX", StaticPath}`。SDK/组件 3s 超时文案「验证超时，请重新点击人机验证」= 再点一次按钮重 init 即可。提交给业务后端的三件套缺一不可：`captchaVerifyParam`(JSON：sceneId/certifyId/failover) + `sceneId` + `certifyId`（缺字段错误序：sceneId不能为空→failover不能为空→captchaVerifyParam不能为空→验证码验证失败）。
- **过验证（实证唯一稳法；headless 连败、有头一次过）**：`xvfb-run` + 有头 chromium（playwright headless=False）。流程：点「点击人机验证」→ 0.25s 轮询 `.checkbox` 元素出现 → 行内 10+ 个随机微动目标点的拟人游走（步长 0.07–0.2s）→ 悬停 0.4–0.7s → **精点左端图标方块（行.x+25px，行中心 y）**——点行中心/文字标签无效 → ≈3s 后出「人机验证成功」；失败态「验证超时」→ 重 point 再试（≤3-4 轮）。
- 判定服务端真伪/一次性：假 certifyId 或重放旧包 → 「验证码验证失败」= 真调阿里云核验（糊弄不了）；certifyId 一次性，失败也消耗。
- 需多次探测（如时测注入）时：浏览器内 **hook XHR 捕获首个合法业务请求体**（含全套验证参数），随后页内 fetch 秒级重放变体，抢在同一 certifyId 消费前完成系列探测；做不到就每探测重过一遍验证（~30-60s/次，计成本）。
- sceneId/prefix 因站而异（本案例 irlra1zdy / q7flua6）——从站内组件 default props/代码读，别背数字。

## 7. PoW 计算题反爬（X-Verify 类）——实测全破（注册+业务端点端到端消费）

白标赌场平台（Torrero 系）在敏感端点前置「工作量证明」：直接调用返回挑战体
`{"func":"zeros","params":{"a":N,"b":"<hex 串>"}}`，且**响应头**带票据 `x-verify-data` / `x-verify-sign`。

- **解法（zeros）**：枚举 nonce = 2^31+i，算 `SHA256( utf8("b"原样字符串) + uint32BE(nonce) )`，直到 hexdigest 前 `a` 个半字节为 0；**答案 = base64(nonce 的 4 字节大端)**——标准 btoa 语义（含 `=` 填充，非 url-safe）。`sha256` 型按同协议读 params 另解（重复哈希）。
- **回填三头**：请求带上挑战响应头原值 `X-Verify-Data` / `X-Verify-Sign` + 自算答案头（`X-Verify-Result`；确切头名先抓包核对）。
- **头号血坑（Python 连败的根因）**：JS `TextEncoder.encode(b)` 是把 hex 当 **ASCII 字符串**编码，不是 hex 解码字节——Python 对应 `b_str.encode()`，绝不能 `bytes.fromhex`。
- **对标自检**：把站点自己的求解器 JS（或等价实现）原样抽出来丢 node 跑同输入，与 Python 输出**字节级一致**（含 b64 填充）再上靶场。
- **验证标准**：解完打一个会做业务校验的端点——回「缺字段/格式错」= PoW 已全过（要的就是这个信号）；回挑战 = 没过。
- 每次挑战独立消费；后续 429 = 端点限速（退避重试），不是 PoW 错。完整案例见 `references/x-verify-pow-case.md`。

## 8. 假错误掩真错误（机器人评分 / TLS 指纹层）——先查「载体」再调载荷

现象（实测）：同一注册请求用 curl/python 怎么改载荷都回通用错误（`invalid login/password`）；**同请求改从真浏览器内核的页内 `fetch(..., {credentials:'include'})` 发出，立刻拿到真实校验错误**（如 `marketing: Invalid format`）。= 前端风控按 TLS/JA3 指纹给脚本喂假响应，「谁在发请求」是第一校验层。

- 处置：注册/登录类「谜之通用报错」，先切 playwright 页内 fetch RPC（同上下文=同 TLS+同 cookie+同源头），拿真错误再调载荷；连版本/平台头（如 `production-malta-1474`、`platform: browser`）都照真浏览器抄。
- 418「服务不在你地区」也可能叠加反匿名层（Tor 国别出口照样 418）→ 换同平台的其他注册通道，别死磕端点（案例见 torrero-platform-pentest）。
- 先打 1 发真浏览器对照，再动手调载荷——辨伪成本远低于盲调。

## Pitfalls

- **Xvfb / patchright 重启坑**：杀进程后 `/tmp/.X<n>-lock` 与 `/tmp/.X11-unix/X<n>` 变陈旧 → Xvfb 拒起、浏览器报 `Missing X server or $DISPLAY`；先清陈旧文件或换新 display 号，起完 `DISPLAY=:N xdpyinfo` 验证再跑。
- 解算成功 ≠ 拿到结果：一次性 token 必须当场消费，别跨请求存着。
- 任务里你看到的题面可能是 decoy：试 2-3 个样本找规律，别对一个样本硬调参数调到底。
- 多轮失败后加 2-5s 抖动、换出口；连续失败可能已进风控池。
- 写报告时：「验证码可自动解算」与「已拿下后台」是两回事，口径保持诚实。
- **谜之通用错误先辨伪**：`invalid login/password` 类通用错误反复调载荷都不对时，改真浏览器页内 fetch 重放对比（§8）——可能是风控喂的假响应。

## 案例库

- `references/geetest-v4-uulai-case.md` — UU来国际赌博站全链：CF+geetest 全破、注册载荷、Tor 浏览器页内 fetch 通道、账户与加密包细节。
- `references/x-verify-pow-case.md` — Torrero/betmaster 白标赌场 X-Verify PoW 全协议：zeros 字节级解法、三头回填、node 对照法、端到端验证记录。
